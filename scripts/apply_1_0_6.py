"""Patch a verified Genesis 1.0.5-preview installation to 1.0.6-preview.

Only the owned, build_release-allowlisted app snapshot is eligible. The game
EXE, engine, profiles, licensed data, saves and third-party .local graphics are
outside this transaction. Run --dry-run first; it emits a JSON plan and writes
nothing. A live patch needs the game and its installed companion to be closed.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import uuid

import build_release


BASE_VERSION = '1.0.5-preview'
TARGET_VERSION = '1.0.6-preview'
SOURCE_VERSION = '1.0.6'
BACKUP_RELATIVE = 'app/.local/patches/1.0.6-before-mystery-start'
# These two package seed files can acquire legitimate runtime state. They are
# never copied from the source release and keep their prior manifest entries.
RUNTIME_FILES = {'data/entities.json', 'mod/bridge/inbox.json'}
# One previous local microphone preview was installed outside the manifest.
# This exception is bound to both its old manifest entry and exact observed
# bytes. It never accepts arbitrary drift or grants a generic force option.
PINNED_DRIFT = {
    'app/mod/scripts/halveth/microphone.lua': {
        'manifestSha256': '8d1e978c231df07bec95ad50f9a1dc9cdc1b9ed8b755f7982a9b62bfeb62a2bd',
        'manifestBytes': 6777,
        'observedSha256': '11c7e77e0ee2fb1a85390435c75d0aabb83fb936b63164287d2f2fdcfd1bd486',
        'observedBytes': 6958,
    },
}
SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def is_reparse(path: Path) -> bool:
    """Reject symlinks and Windows junction/other reparse points."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    # FILE_ATTRIBUTE_REPARSE_POINT is 0x400 on every supported Windows build.
    # Keep the literal as a fallback for Python versions without the stat name.
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, 'st_file_attributes', 0) & 0x400)
            or (hasattr(path, 'is_junction') and path.is_junction()))


def check_components(path: Path) -> None:
    for component in (path, *path.parents):
        if is_reparse(component):
            raise ValueError('Verknuepfter/reparse Pfad ist nicht erlaubt: ' + str(component))


def relative_parts(relative: str) -> tuple[str, ...]:
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative or relative.startswith('/'):
        raise ValueError('Ungueltiger Paketpfad: ' + str(relative))
    parts = tuple(relative.split('/'))
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('Ungueltiger Paketpfad: ' + relative)
    return parts


def within(root: Path, relative: str) -> Path:
    path = root.joinpath(*relative_parts(relative))
    # Keep root anchored and reject links in every existing component. Do not
    # resolve the target before checking: resolution hides a linked ancestor.
    check_components(path)
    if not path.resolve(strict=False).is_relative_to(root.resolve(strict=True)):
        raise ValueError('Paketpfad verlaesst die Installation: ' + relative)
    return path


def _windows_processes() -> list[dict]:
    # A PID file alone can be stale or absent. Enumerate real processes and
    # command lines; fail closed if WMI cannot provide a trustworthy snapshot.
    script = (
        '[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false); '
        "$ErrorActionPreference = 'Stop'; "
        "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in "
        "@('openmw.exe','python.exe','pythonw.exe','HALVETH Morrowind.exe') } | "
        'Select-Object ProcessId,Name,ExecutablePath,CommandLine) | ConvertTo-Json -Compress'
    )
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=20, check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Windows-Prozesse konnten nicht sicher geprueft werden.') from exc
    if result.returncode != 0:
        raise RuntimeError('Windows-Prozesse konnten nicht sicher geprueft werden: '
                           + result.stderr.strip()[:300])
    try:
        values = json.loads(result.stdout.strip())
    except (ValueError, TypeError) as exc:
        raise RuntimeError('Windows-Prozessliste ist unlesbar.') from exc
    if not isinstance(values, list) or any(not isinstance(item, dict) for item in values):
        raise RuntimeError('Windows-Prozessliste hat ein unerwartetes Format.')
    return values


def _windows_command_args(command: str) -> list[str]:
    """Parse the process's Windows command line without losing quoted paths."""
    argc = ctypes.c_int()
    parser = ctypes.windll.shell32.CommandLineToArgvW
    parser.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    parser.restype = ctypes.POINTER(ctypes.c_wchar_p)
    argv = parser(command, ctypes.byref(argc))
    if not argv:
        raise RuntimeError('Windows-Prozessargumente sind nicht lesbar.')
    try:
        return [argv[index] for index in range(argc.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(ctypes.cast(argv, ctypes.c_void_p))


def _canonical_absolute(path: str | Path) -> Path | None:
    """Expand existing Windows 8.3 path segments before process comparison."""
    candidate = Path(path)
    if not candidate.is_absolute():
        return None
    try:
        return candidate.resolve(strict=False)
    except (OSError, RuntimeError):
        return None


def _same_process_file(path: str, expected: Path) -> bool:
    candidate = _canonical_absolute(path)
    if candidate is None:
        return False
    try:
        return os.path.samefile(candidate, expected)
    except OSError:
        return candidate == expected.resolve(strict=False)


def ensure_game_closed(installed: Path) -> None:
    if os.name != 'nt':
        return
    server = installed / 'app' / 'server.py'
    runtime = (installed / 'runtime').resolve(strict=False)
    launcher = installed / 'HALVETH Morrowind.exe'
    for item in _windows_processes():
        name = str(item.get('Name') or '').casefold()
        exe = str(item.get('ExecutablePath') or '')
        command = str(item.get('CommandLine') or '')
        exe_path = _canonical_absolute(exe) if exe else None
        pid = item.get('ProcessId')
        if name == 'openmw.exe':
            # An unrelated OpenMW is conservatively stopped at this point too:
            # changing native mod bytes while any world is running is unsafe.
            raise RuntimeError(f'OpenMW laeuft noch (PID {pid}); bitte normal beenden.')
        if name == 'halveth morrowind.exe' and (not exe or _same_process_file(exe, launcher)):
            raise RuntimeError(f'Genesis-Launcher laeuft noch (PID {pid}).')
        if name in ('python.exe', 'pythonw.exe'):
            if exe_path is not None and exe_path.is_relative_to(runtime):
                raise RuntimeError(f'Genesis-Begleiter laeuft noch (PID {pid}); bitte normal beenden.')
            arguments = _windows_command_args(command) if command else []
            for argument in arguments[1:]:
                if Path(argument).name.casefold() != 'server.py':
                    continue
                if _same_process_file(argument, server):
                    raise RuntimeError(f'Genesis-Begleiter laeuft noch (PID {pid}); bitte normal beenden.')
                if not Path(argument).is_absolute():
                    # WMI does not expose this process's working directory;
                    # a relative server.py might be our companion.
                    raise RuntimeError(f'Ein Python-Serverprozess ist nicht eindeutig lesbar (PID {pid}).')
            if not exe and not command:
                raise RuntimeError(f'Ein Genesis-Prozess ist nicht eindeutig lesbar (PID {pid}).')


def source_snapshot(source: dict[str, bytes] | None) -> dict[str, bytes]:
    if source is None:
        if build_release.VERSION != SOURCE_VERSION:
            raise ValueError('Quellpaket muss Version ' + SOURCE_VERSION + ' deklarieren.')
        source = build_release.collect_files()
    build_release.validate_files(source)
    if not isinstance(source, dict) or any(not isinstance(raw, bytes) for raw in source.values()):
        raise TypeError('Quellpaket braucht Pfade und unveraenderliche Bytes.')
    folded_paths: set[str] = set()
    for relative in source:
        relative_parts(relative)
        folded = relative.casefold()
        if folded in folded_paths:
            raise ValueError('Quellpaket enthaelt doppelte Windows-Pfade: ' + relative)
        folded_paths.add(folded)
    return {name: raw for name, raw in source.items() if name not in RUNTIME_FILES}


def source_fingerprint(source: dict[str, bytes]) -> str:
    index = '\n'.join(f'{name}\0{len(raw)}\0{digest_bytes(raw)}'
                      for name, raw in sorted(source.items()))
    return digest_bytes(index.encode('utf-8'))


def read_state(installed: Path) -> tuple[Path, dict, dict[str, dict], str]:
    state_path = within(installed, 'install-state.json')
    if not state_path.is_file():
        raise FileNotFoundError('Installationsmanifest fehlt: ' + str(state_path))
    state_raw = state_path.read_bytes()
    state = json.loads(state_raw.decode('utf-8-sig'))
    if not isinstance(state, dict) or state.get('version') != BASE_VERSION or state.get('mode') not in ('local-engine', 'owned-mod'):
        raise ValueError('Erwartet wird eine Genesis 1.0.5-preview Installation.')
    entries = state.get('files')
    if not isinstance(entries, list):
        raise ValueError('Installationsmanifest hat keine Dateiliste.')
    records: dict[str, dict] = {}
    seen_folded: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Installationsmanifest enthaelt einen ungueltigen Eintrag.')
        name = entry.get('path')
        relative_parts(name)
        if name.casefold().startswith('app/.local/'):
            raise ValueError('Lokaler Nutzerzustand darf nicht im verwalteten App-Manifest stehen: ' + name)
        sha = entry.get('sha256')
        size = entry.get('bytes')
        if (not isinstance(sha, str) or not SHA256.fullmatch(sha)
                or not isinstance(size, int) or isinstance(size, bool) or size < 0):
            raise ValueError('Installationsmanifest enthaelt ungueltige Hash-/Groessenwerte: ' + name)
        folded = name.casefold()
        if folded in seen_folded:
            raise ValueError('Installationsmanifest enthaelt doppelte Pfade: ' + name)
        seen_folded.add(folded)
        records[name] = entry
    return state_path, state, records, digest_bytes(state_raw)


def preflight(installed: Path, source: dict[str, bytes] | None = None) -> dict:
    installed = Path(installed).absolute()
    check_components(installed)
    if not installed.is_dir():
        raise FileNotFoundError('Installationsordner fehlt: ' + str(installed))
    installed = installed.resolve(strict=True)
    ensure_game_closed(installed)
    state_path, state, records, state_sha = read_state(installed)
    package = source_snapshot(source)
    changed: dict[str, bytes] = {}
    added: dict[str, bytes] = {}
    already: list[dict] = []
    pinned: list[dict] = []
    observed: dict[str, tuple[int, str]] = {}
    checked = 0
    for name, record in records.items():
        if not name.startswith('app/') or name[4:] in RUNTIME_FILES:
            continue
        target = within(installed, name)
        if not target.is_file():
            raise ValueError('Verwaltete App-Datei fehlt: ' + name)
        actual_size = target.stat().st_size
        actual_sha = digest_file(target)
        observed[name] = (actual_size, actual_sha)
        desired = package.get(name[4:])
        if actual_size != record['bytes'] or actual_sha != record['sha256']:
            desired_sha = digest_bytes(desired) if desired is not None else None
            if desired is not None and actual_sha == desired_sha and actual_size == len(desired):
                already.append({'path': name, 'manifestSha256': record['sha256'],
                                'observedSha256': actual_sha, 'desiredSha256': desired_sha,
                                'bytes': actual_size})
            elif (name in PINNED_DRIFT and desired is not None
                  and record['sha256'] == PINNED_DRIFT[name]['manifestSha256']
                  and record['bytes'] == PINNED_DRIFT[name]['manifestBytes']
                  and actual_sha == PINNED_DRIFT[name]['observedSha256']
                  and actual_size == PINNED_DRIFT[name]['observedBytes']):
                pinned.append({'path': name, 'manifestSha256': record['sha256'],
                               'observedSha256': actual_sha, 'desiredSha256': desired_sha,
                               'observedBytes': actual_size, 'desiredBytes': len(desired)})
            else:
                raise ValueError('Verwaltete App-Datei wurde unabhaengig geaendert: ' + name)
        checked += 1
    already_names = {item['path'] for item in already}
    for relative, raw in sorted(package.items()):
        name = 'app/' + relative
        target = within(installed, name)
        desired_sha = digest_bytes(raw)
        if name in records:
            if name in already_names:
                continue
            if digest_file(target) != desired_sha:
                changed[name] = raw
        elif target.exists():
            raise FileExistsError('Neuer Paketpfad ist schon belegt: ' + name)
        else:
            added[name] = raw
    backup = within(installed, BACKUP_RELATIVE)
    if backup.exists():
        raise FileExistsError('Patch-Sicherung existiert bereits: ' + str(backup))
    plan = {
        'status': 'READY', 'fromVersion': BASE_VERSION, 'version': TARGET_VERSION,
        'installed': str(installed), 'sourceFingerprintSha256': source_fingerprint(package),
        'installStateBeforeSha256': state_sha, 'managedAppFilesVerified': checked,
        'changed': sorted(changed), 'added': sorted(added), 'alreadyApplied': already,
        'pinnedPriorDrift': pinned,
        'changedDetails': [
            {'path': name, 'manifestSha256': records[name]['sha256'],
             'observedSha256': observed[name][1],
             'desiredSha256': digest_bytes(raw), 'bytes': len(raw)}
            for name, raw in sorted(changed.items())],
        'addedDetails': [
            {'path': name, 'desiredSha256': digest_bytes(raw), 'bytes': len(raw)}
            for name, raw in sorted(added.items())],
        'backup': str(backup), 'gameRestartRequired': True,
        'companionRestartRequired': True, 'personalSavesTouched': False,
        'licensedGameDataTouched': False, 'thirdPartyGraphicsTouched': False,
    }
    return {'plan': plan, 'installed': installed, 'statePath': state_path,
            'state': state, 'records': records, 'changed': changed, 'added': added,
            'backup': backup, 'package': package, 'observed': observed}


def _write_staged(target: Path, raw: bytes) -> Path:
    check_components(target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    check_components(target.parent)
    staged = target.with_name(target.name + '.patching-1.0.6-' + uuid.uuid4().hex)
    try:
        with staged.open('xb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        if staged.stat().st_size != len(raw) or digest_file(staged) != digest_bytes(raw):
            raise OSError('Staging-Hash stimmt nicht ueberein: ' + str(target))
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    return staged


def _replace_bytes(target: Path, raw: bytes) -> None:
    staged = _write_staged(target, raw)
    try:
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)
    if target.stat().st_size != len(raw) or digest_file(target) != digest_bytes(raw):
        raise OSError('Geschriebene Datei weicht ab: ' + str(target))


def apply(installed: Path, dry_run: bool = False,
          source: dict[str, bytes] | None = None) -> dict:
    context = preflight(installed, source)
    plan = context['plan']
    if dry_run:
        return plan
    root = context['installed']
    backup = context['backup']
    state_path = context['statePath']
    changed = context['changed']
    added = context['added']
    records = context['records']
    state = context['state']
    observed = context['observed']
    backup.mkdir(parents=True, exist_ok=False)
    check_components(backup)
    backup_state = backup / 'install-state.json'
    shutil.copy2(state_path, backup_state)
    if digest_file(backup_state) != plan['installStateBeforeSha256']:
        raise OSError('Installationsmanifest-Sicherung stimmt nicht ueberein.')
    # Back up every file whose installed bytes change and every drifted file
    # whose manifest hash is reconciled. Backups are checked before mutation.
    for name in sorted(set(changed) | {item['path'] for item in plan['alreadyApplied']}):
        original = within(root, name)
        saved = within(backup, name)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, saved)
        if saved.stat().st_size != observed[name][0] or digest_file(saved) != observed[name][1]:
            raise OSError('Datei-Sicherung stimmt nicht ueberein: ' + name)
    writes = [*sorted(changed.items()), *sorted(added.items())]
    stages: dict[str, Path] = {}
    written: list[str] = []
    state_written = False
    try:
        for name, raw in writes:
            target = within(root, name)
            stages[name] = _write_staged(target, raw)
        if digest_file(state_path) != plan['installStateBeforeSha256']:
            raise RuntimeError('Installationsmanifest hat sich seit der Vorpruefung geaendert.')
        for name, (size, sha) in observed.items():
            target = within(root, name)
            if not target.is_file() or target.stat().st_size != size or digest_file(target) != sha:
                raise RuntimeError('App-Datei hat sich seit der Vorpruefung geaendert: ' + name)
        for name in added:
            if within(root, name).exists():
                raise FileExistsError('Neuer Paketpfad wurde zwischenzeitlich belegt: ' + name)
        # Narrow the race between planning and replacement. This is a local
        # maintenance transaction, not a process-suspension mechanism.
        ensure_game_closed(root)
        for name, raw in writes:
            target = within(root, name)
            written.append(name)
            os.replace(stages[name], target)
            stages.pop(name)
            if target.stat().st_size != len(raw) or digest_file(target) != digest_bytes(raw):
                raise OSError('Geschriebene Datei weicht ab: ' + name)
        for name, raw in writes:
            record = records.get(name)
            if record is None:
                record = {'path': name}
                state['files'].append(record)
                records[name] = record
            record['sha256'] = digest_bytes(raw)
            record['bytes'] = len(raw)
        for item in plan['alreadyApplied']:
            records[item['path']]['sha256'] = item['observedSha256']
            records[item['path']]['bytes'] = item['bytes']
        state['version'] = TARGET_VERSION
        state['mysteryStartPatch'] = True
        encoded = (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        state_written = True
        _replace_bytes(state_path, encoded)
        receipt = dict(plan, status='PATCHED_PREVIEW',
                       installStateAfterSha256=digest_file(state_path))
        _replace_bytes(backup / 'receipt.json',
                       (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        return receipt
    except Exception as exc:
        rollback_errors = []
        for name in reversed(written):
            target = within(root, name)
            try:
                if name in changed:
                    _replace_bytes(target, within(backup, name).read_bytes())
                elif target.exists():
                    raw = added[name]
                    if target.stat().st_size != len(raw) or digest_file(target) != digest_bytes(raw):
                        raise RuntimeError('Neu angelegter Pfad hat unerwartete fremde Bytes; bleibt erhalten.')
                    target.unlink()
            except Exception as rollback_exc:
                rollback_errors.append(f'{name}: {rollback_exc}')
        if state_written:
            try:
                _replace_bytes(state_path, backup_state.read_bytes())
            except Exception as rollback_exc:
                rollback_errors.append('install-state.json: ' + str(rollback_exc))
        if rollback_errors:
            raise RuntimeError('Patch fehlgeschlagen; Rollback unvollstaendig. Sicherung: '
                               + str(backup) + '; Fehler: ' + '; '.join(rollback_errors)) from exc
        raise
    finally:
        for staged in stages.values():
            staged.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(apply(args.installed, args.dry_run), ensure_ascii=False, indent=2))
