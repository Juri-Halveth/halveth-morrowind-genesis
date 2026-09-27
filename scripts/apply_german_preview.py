"""Patch only owned German books and companion speech into a verified preview.

The running game and its save files are not opened. Changes load after the
normal game/companion restart. Every replaced owned file is backed up.
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
    'app/server.py',
    'app/launcher.py',
    'app/README.md',
)
ADD = ('app/voice_output.py',)


def apply(installed: Path, dry_run: bool = False) -> dict:
    installed = installed.resolve(strict=True)
    if installed.is_symlink() or (hasattr(installed, 'is_junction') and installed.is_junction()):
        raise ValueError('Installation root must not be a link')
    state_path = within(installed, 'install-state.json')
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    if state.get('version') != '1.0.4-preview' or state.get('germanVoicePatch'):
        raise ValueError('Expected unpatched 1.0.4-preview installation')
    records = {item['path']: item for item in state['files']}
    for relative in REPLACE:
        target = within(installed, relative)
        if relative not in records or digest(target) != records[relative]['sha256']:
            raise ValueError('Installed owned file differs from manifest: ' + relative)
    for relative in ADD:
        if relative in records or within(installed, relative).exists():
            raise FileExistsError('Expected new file: ' + relative)
    for relative in REPLACE + ADD:
        if not within(ROOT, relative.removeprefix('app/')).is_file():
            raise FileNotFoundError(relative)
    backup = within(installed, 'app/.local/patches/1.0.4-before-language')
    if backup.exists():
        raise FileExistsError(backup)
    receipt = {'status': 'READY' if dry_run else 'PATCHED_PREVIEW',
               'files': list(REPLACE + ADD), 'backup': str(backup),
               'restartRequired': True, 'personalSavesTouched': False}
    if dry_run:
        return receipt
    backup.mkdir(parents=True)
    shutil.copy2(state_path, backup / 'install-state.json')
    for relative in REPLACE:
        target_backup = within(backup, relative)
        target_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(within(installed, relative), target_backup)
        if digest(target_backup) != records[relative]['sha256']:
            raise OSError('Backup hash mismatch: ' + relative)
    changed = []
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
            changed.append(relative)
            record = records.get(relative)
            if record is None:
                record = {'path': relative}
                state['files'].append(record)
            record['sha256'] = digest(target)
            record['bytes'] = target.stat().st_size
        state['germanVoicePatch'] = True
        stage = state_path.with_name(state_path.name + '.patching')
        stage.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(stage, state_path)
    except Exception:
        for relative in reversed(changed):
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
