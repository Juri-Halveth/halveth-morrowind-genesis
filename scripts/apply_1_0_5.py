"""Forward-port verified Genesis 1.0.5 source into the existing owned install.

Only manifest-bound app files are replaced. Private profiles, saves, licensed
game files, downloaded mods, runtime mailboxes and the visible game EXE stay at
their current paths. Backups are hash-checked before a reversible local patch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from apply_reborn_preview import digest, within
from build_release import collect_files, validate_files

VERSION = '1.0.5-preview'
BASE_VERSION = '1.0.4-preview'
RUNTIME_FILES = {'data/entities.json', 'mod/bridge/inbox.json'}


def ensure_game_closed(installed: Path) -> None:
    """Refuse to patch a recorded personal OpenMW process still in use."""
    if os.name != 'nt':
        return
    pid_path = within(installed, 'app/.local/game.pid')
    if not pid_path.is_file():
        return
    pid = pid_path.read_text(encoding='ascii').strip()
    if not pid.isdigit():
        raise ValueError('Spiel-PID ist unlesbar; Installation nicht geaendert.')
    result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                            capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError('Spielprozess konnte nicht sicher geprueft werden.')
    expected = [b'"openmw.exe"', f'"{pid}"'.encode('ascii')]
    for line in result.stdout.splitlines():
        if line.strip().lower().split(b',', 2)[:2] == expected:
            raise RuntimeError('Das persoenliche Morrowind laeuft noch; bitte erst normal beenden.')


def preflight(installed: Path, source: dict[str, bytes] | None = None):
    if installed.is_symlink() or (hasattr(installed, 'is_junction') and installed.is_junction()):
        raise ValueError('Installationsordner darf kein Link sein.')
    installed = installed.resolve(strict=True)
    ensure_game_closed(installed)
    state_path = within(installed, 'install-state.json')
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    if state.get('version') != BASE_VERSION or state.get('mode') not in ('local-engine', 'owned-mod'):
        raise ValueError('Erwartet wird die verifizierte Genesis 1.0.4-Vorschau.')
    records = {item['path']: item for item in state['files']}
    if len(records) != len(state['files']):
        raise ValueError('Installationsmanifest enthaelt doppelte Pfade.')
    source = source if source is not None else collect_files()
    validate_files(source)
    changed, added = {}, {}
    for relative, raw in sorted(source.items()):
        if relative in RUNTIME_FILES:
            continue
        name = 'app/' + relative
        target = within(installed, name)
        if target.is_symlink() or (hasattr(target, 'is_junction') and target.is_junction()):
            raise ValueError('Verknuepfte Installationsdatei: ' + name)
        record = records.get(name)
        if record:
            if not target.is_file() or target.stat().st_size != record['bytes'] or digest(target) != record['sha256']:
                raise ValueError('Verwaltete Datei wurde unabhaengig geaendert: ' + name)
            if target.read_bytes() != raw:
                changed[name] = raw
        elif target.exists():
            raise FileExistsError('Neuer Paketpfad ist bereits belegt: ' + name)
        else:
            added[name] = raw
    backup = within(installed, 'app/.local/patches/1.0.5-before-native-console')
    if backup.exists():
        raise FileExistsError('Patch-Sicherung existiert bereits: ' + str(backup))
    return state_path, state, records, changed, added, backup


def apply(installed: Path, dry_run: bool = False, source: dict[str, bytes] | None = None) -> dict:
    state_path, state, records, changed, added, backup = preflight(installed, source)
    installed = installed.resolve(strict=True)
    receipt = {'status': 'READY' if dry_run else 'PATCHED_PREVIEW',
               'version': VERSION, 'changed': sorted(changed), 'added': sorted(added),
               'backup': str(backup), 'gameRestartRequired': True,
               'companionRestartRequired': True, 'personalSavesTouched': False,
               'licensedGameDataTouched': False}
    if dry_run:
        return receipt
    backup.mkdir(parents=True)
    shutil.copy2(state_path, backup / 'install-state.json')
    if digest(backup / 'install-state.json') != digest(state_path):
        raise OSError('Installationsmanifest-Sicherung stimmt nicht ueberein.')
    for name in changed:
        source_file = within(installed, name)
        saved = within(backup, name)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, saved)
        if digest(saved) != records[name]['sha256']:
            raise OSError('Sicherung stimmt nicht ueberein: ' + name)
    written = []
    try:
        for name, raw in [*changed.items(), *added.items()]:
            target = within(installed, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            staging = target.with_name(target.name + '.patching')
            if staging.exists():
                raise FileExistsError('Stagingpfad ist bereits belegt: ' + str(staging))
            try:
                staging.write_bytes(raw)
                if digest(staging) != hashlib.sha256(raw).hexdigest():
                    raise OSError('Staging-Hash stimmt nicht ueberein: ' + name)
                # Record the target before replacement so an exception in the
                # replacement path still includes it in local rollback.
                written.append(name)
                os.replace(staging, target)
            finally:
                staging.unlink(missing_ok=True)
            record = records.get(name)
            if record is None:
                record = {'path': name}
                state['files'].append(record)
            record['sha256'] = digest(target)
            record['bytes'] = target.stat().st_size
        state['version'] = VERSION
        state['nativeConsolePatch'] = True
        staging = state_path.with_name(state_path.name + '.patching')
        staging.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(staging, state_path)
        receipt_staging = backup / 'receipt.json.patching'
        receipt_staging.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(receipt_staging, backup / 'receipt.json')
    except Exception:
        (backup / 'receipt.json.patching').unlink(missing_ok=True)
        for name in reversed(written):
            target = within(installed, name)
            if name in changed:
                shutil.copy2(within(backup, name), target)
            else:
                target.unlink(missing_ok=True)
        shutil.copy2(backup / 'install-state.json', state_path)
        raise
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(apply(args.installed, args.dry_run), ensure_ascii=False, indent=2))
