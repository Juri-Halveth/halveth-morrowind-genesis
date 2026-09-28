"""Forward-port the verified 1.0.4 gameplay additions into the owned install.

Only exact managed app paths are touched. Existing files and install state get
hash-checked backups; Bethesda data, third-party mods, settings and saves do
not enter this patch. Restart the game normally to load the new resources.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil

from apply_reborn_preview import digest, within

ROOT = Path(__file__).resolve().parents[1]
REPLACE = (
    'app/data/native-content.json',
    'app/mod/scripts/halveth/content_catalog.lua',
    'app/mod/halveth.omwscripts',
    'app/mod/scripts/halveth/worldlife.lua',
    'app/server.py',
    'app/voice_output.py',
    'app/README.md',
)
ADD = (
    'app/mod/scripts/halveth/world_moments.lua',
    'app/mod/Video/new_game.webm',
)


def apply(installed: Path, dry_run: bool = False) -> dict:
    installed = installed.resolve(strict=True)
    if installed.is_symlink() or (hasattr(installed, 'is_junction') and installed.is_junction()):
        raise ValueError('Installation root must not be a link')
    state_path = within(installed, 'install-state.json')
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    if state.get('version') != '1.0.4-preview' or state.get('germanVoicePatch') is not True \
            or state.get('playablePatch'):
        raise ValueError('Expected verified German 1.0.4-preview before this patch')
    records = {entry['path']: entry for entry in state['files']}
    if len(records) != len(state['files']):
        raise ValueError('Duplicate install-state paths')
    for relative in REPLACE:
        target = within(installed, relative)
        record = records.get(relative)
        if not record or not target.is_file() or digest(target) != record['sha256']:
            raise ValueError('Managed file differs from install-state: ' + relative)
    for relative in ADD:
        if relative in records or within(installed, relative).exists():
            raise FileExistsError('Expected new managed file: ' + relative)
    for relative in REPLACE + ADD:
        if not within(ROOT, relative.removeprefix('app/')).is_file():
            raise FileNotFoundError('Missing source: ' + relative)
    backup = within(installed, 'app/.local/patches/1.0.4-before-playable')
    if backup.exists():
        raise FileExistsError('Backup already exists: ' + str(backup))
    receipt = {'status': 'READY' if dry_run else 'PATCHED_PREVIEW',
               'paths': list(REPLACE + ADD), 'backup': str(backup),
               'restartRequired': True, 'personalSavesTouched': False}
    if dry_run:
        return receipt
    backup.mkdir(parents=True)
    shutil.copy2(state_path, backup / 'install-state.json')
    if digest(backup / 'install-state.json') != digest(state_path):
        raise OSError('Install-state backup hash mismatch')
    for relative in REPLACE:
        saved = within(backup, relative)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(within(installed, relative), saved)
        if digest(saved) != records[relative]['sha256']:
            raise OSError('Backup hash mismatch: ' + relative)
    written = []
    try:
        for relative in REPLACE + ADD:
            source = within(ROOT, relative.removeprefix('app/'))
            target = within(installed, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = target.with_name(target.name + '.patching')
            shutil.copy2(source, stage)
            if digest(stage) != digest(source):
                raise OSError('Stage hash mismatch: ' + relative)
            os.replace(stage, target)
            written.append(relative)
            record = records.get(relative)
            if record is None:
                record = {'path': relative}
                state['files'].append(record)
            record['sha256'] = digest(target)
            record['bytes'] = target.stat().st_size
        state['playablePatch'] = True
        staged_state = state_path.with_name(state_path.name + '.patching')
        staged_state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(staged_state, state_path)
    except Exception:
        for relative in reversed(written):
            target = within(installed, relative)
            if relative in ADD:
                target.unlink(missing_ok=True)
            else:
                shutil.copy2(within(backup, relative), target)
        shutil.copy2(backup / 'install-state.json', state_path)
        raise
    (backup / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(apply(args.installed, args.dry_run), ensure_ascii=False, indent=2))
