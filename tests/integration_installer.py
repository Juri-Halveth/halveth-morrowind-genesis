"""Isolated Windows EXE install/check/uninstall smoke; never loads a personal save.

Run after building both setup variants with --engine-root, --source-profile and
--game-data pointing at the user's licensed local installations. All writes are
confined to a fresh tests/.local sibling under the project root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.local' / 'installer-smoke'
SETUPS = ROOT / 'dist' / 'installer-candidates'


def invoke(exe: Path, *args: str) -> tuple[int, dict]:
    result = subprocess.run([str(exe), *args], capture_output=True, text=True,
                            timeout=180, check=False)
    output = result.stdout.strip()
    try:
        receipt = json.loads(output)
    except json.JSONDecodeError as exc:
        raise AssertionError(f'{exe.name} returned no JSON (code {result.returncode}): {result.stderr}') from exc
    return result.returncode, receipt


def insist(code: int, receipt: dict, expected: str) -> None:
    if code != 0 or receipt.get('status') != expected:
        raise AssertionError(f'Expected {expected}, got code={code} receipt={receipt}')


def run_variant(mode: str, exe: Path, target: Path, engine: Path, profile: Path,
                game_data: Path) -> dict:
    arguments = ['--install', '--target', str(target), '--no-shortcuts']
    if mode == 'owned-mod':
        arguments += ['--engine-root', str(engine), '--source-profile', str(profile)]
    else:
        arguments += ['--game-data', str(game_data)]
    code, installed = invoke(exe, *arguments)
    insist(code, installed, 'INSTALLED')
    code, checked = invoke(exe, '--check', '--target', str(target))
    insist(code, checked, 'PASS')
    if checked.get('broken'):
        raise AssertionError('Installed hash check found broken files')

    sentinel = target / 'app' / '.local' / 'kept-user-state.txt'
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text('Keep local personal state across uninstall.\n', encoding='utf-8')
    sentinel_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()

    # Running a self-uninstall should leave the state for a retry when Windows
    # locks the installed EXE. Some Windows modes permit deletion; accept both.
    self_code, self_result = invoke(target / 'HALVETH Morrowind.exe', '--uninstall',
                                    '--target', str(target))
    if self_result.get('status') == 'PARTIAL_UNINSTALL_RETRY_WITH_SETUP_EXE':
        if self_code == 0 or not (target / 'install-state.json').is_file():
            raise AssertionError('Partial self-uninstall lost its retry manifest')
        code, uninstalled = invoke(exe, '--uninstall', '--target', str(target))
        insist(code, uninstalled, 'UNINSTALLED')
    else:
        insist(self_code, self_result, 'UNINSTALLED')
        uninstalled = self_result
    if hashlib.sha256(sentinel.read_bytes()).hexdigest() != sentinel_hash:
        raise AssertionError('User-state sentinel changed during uninstall')
    if (target / 'install-state.json').exists():
        raise AssertionError('Install-state remains after complete uninstall')
    return {'mode': mode, 'setupSha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
            'installedFiles': installed['files'], 'check': checked['status'],
            'selfUninstallStatus': self_result['status'],
            'finalUninstallStatus': uninstalled['status'],
            'userStatePreserved': True, 'shortcutsCreated': installed['shortcutCount']}


def run_empty_target_cleanup(exe: Path, target: Path, engine: Path, profile: Path) -> dict:
    code, installed = invoke(exe, '--install', '--target', str(target),
                             '--engine-root', str(engine), '--source-profile', str(profile),
                             '--no-shortcuts')
    insist(code, installed, 'INSTALLED')
    code, removed = invoke(exe, '--uninstall', '--target', str(target))
    insist(code, removed, 'UNINSTALLED')
    if target.exists() or removed.get('userDataPreserved'):
        raise AssertionError('Empty install target survived complete uninstall')
    return {'status': 'PASS', 'emptyTargetRemoved': True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-root', type=Path, required=True)
    parser.add_argument('--source-profile', type=Path, required=True)
    parser.add_argument('--game-data', type=Path, required=True)
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='final-0.8-', dir=BASE)).resolve()
    if temporary.parent != BASE.resolve() or temporary.is_symlink():
        raise RuntimeError('Isolated smoke target escaped its workspace boundary.')
    try:
        public = SETUPS / 'HALVETH-Morrowind-Genesis-0.8.1-Setup.exe'
        private = SETUPS / 'HALVETH-Morrowind-Genesis-0.8.1-Local-Engine-Setup.exe'
        results = [run_variant('owned-mod', public, temporary / 'public',
                               args.engine_root, args.source_profile, args.game_data),
                   run_variant('local-engine', private, temporary / 'private',
                               args.engine_root, args.source_profile, args.game_data)]
        empty_cleanup = run_empty_target_cleanup(public, temporary / 'empty',
                                                 args.engine_root, args.source_profile)
        receipt = {'schema': 'halveth.genesis.installer-smoke/1', 'version': '0.8.1',
                   'status': 'PASS', 'scope': 'fresh isolated install/check/self-uninstall/retry',
                   'licensedGameDataCopied': False, 'personalSavesLoaded': False,
                   'results': results, 'emptyTargetCleanup': empty_cleanup}
        (BASE / 'final-0.8-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n',
                                                   encoding='utf-8')
        print(json.dumps(receipt, indent=2))
    finally:
        if temporary.exists() and temporary.parent == BASE.resolve() and not temporary.is_symlink():
            shutil.rmtree(temporary)


if __name__ == '__main__':
    main()
