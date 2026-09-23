"""Reversibly add Heart Letter to the existing 1.0.2-preview Genesis install.

Only named owned mod files are touched after a hash preflight. Existing saves,
user profiles, Bethesda content and third-party graphic packages stay in place.
Run only while the installed game process is closed; restart to load scripts.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil

from apply_reborn_preview import digest, within

ROOT = Path(__file__).resolve().parents[1]
CHANGED = (
    'app/mod/halveth.omwscripts',
    'app/mod/scripts/halveth/content.lua',
    'app/mod/scripts/halveth/player.lua',
    'app/mod/scripts/halveth/universe.lua',
)
ADDED = ('app/mod/scripts/halveth/heart.lua',)


def apply(installed: Path, dry_run: bool = False) -> dict:
    installed = installed.resolve(strict=True)
    if installed.is_symlink() or (hasattr(installed, 'is_junction') and installed.is_junction()):
        raise ValueError('Installation root must not be a link')
    state_path = installed / 'install-state.json'
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    if state.get('version') != '1.0.2-preview' or state.get('mode') not in ('local-engine', 'owned-mod'):
        raise ValueError('Expected the verified 1.0.2-preview Genesis installation')
    records = {item['path']: item for item in state['files']}
    sources = {}
    for relative in CHANGED + ADDED:
        source = within(ROOT, relative.removeprefix('app/'))
        target = within(installed, relative)
        if not source.is_file():
            raise FileNotFoundError(source)
        if relative in CHANGED:
            if relative not in records or not target.is_file():
                raise ValueError('Expected installed file missing: ' + relative)
            if target.stat().st_size != records[relative]['bytes'] or digest(target) != records[relative]['sha256']:
                raise ValueError('Installed file changed independently: ' + relative)
        elif target.exists() or relative in records:
            raise FileExistsError('New script already exists: ' + relative)
        sources[relative] = source
    backup = within(installed, 'app/.local/patches/1.0.3-before-heart')
    if backup.exists():
        raise FileExistsError('Patch backup already exists: ' + str(backup))
    receipt = {'status': 'READY' if dry_run else 'PATCHED_PREVIEW',
               'version': '1.0.3-preview', 'installed': str(installed),
               'changed': list(CHANGED), 'added': list(ADDED),
               'backup': str(backup), 'personalSavesTouched': False}
    if dry_run:
        return receipt
    backup.mkdir(parents=True)
    written = []
    try:
        for relative in CHANGED:
            source = within(installed, relative)
            copy = within(backup, relative)
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, copy)
            if digest(copy) != digest(source):
                raise OSError('Backup differs: ' + relative)
        shutil.copy2(state_path, backup / 'install-state.json')
        if digest(backup / 'install-state.json') != digest(state_path):
            raise OSError('State backup differs')
        for relative in CHANGED + ADDED:
            target = within(installed, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = target.with_name(target.name + '.patching')
            shutil.copy2(sources[relative], stage)
            if digest(stage) != digest(sources[relative]):
                raise OSError('Staged bytes differ: ' + relative)
            os.replace(stage, target)
            written.append(relative)
            entry = {'path': relative, 'sha256': digest(target), 'bytes': target.stat().st_size}
            if relative in records:
                records[relative].update(entry)
            else:
                state['files'].append(entry)
        state['version'] = '1.0.3-preview'
        stage_state = state_path.with_name(state_path.name + '.patching')
        stage_state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(stage_state, state_path)
    except Exception:
        for relative in reversed(written):
            target = within(installed, relative)
            if relative in CHANGED:
                shutil.copy2(within(backup, relative), target)
            else:
                target.unlink(missing_ok=True)
        shutil.copy2(backup / 'install-state.json', state_path)
        raise
    (backup / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(apply(args.installed, args.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
