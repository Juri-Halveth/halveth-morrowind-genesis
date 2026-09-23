"""Add the seven Reborn World materials to a verified 1.0.3-preview install.

Only new owned image files and install-state.json are written. Existing saves,
Bethesda data, profile settings, and installed third-party mods are untouched.
An already running game continues; the new textures become visible after its
next normal restart, when OpenMW rebuilds its virtual file system.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil

from apply_reborn_preview import digest, within
from build_reborn_world import MATERIALS

ROOT = Path(__file__).resolve().parents[1]
ADDED = tuple(item for name in MATERIALS for item in (
    f'app/assets/RebornWorld/{name}-source.png',
    f'app/mod/Textures/{name}.dds',
))


def apply(installed: Path, dry_run: bool = False) -> dict:
    installed = installed.resolve(strict=True)
    if installed.is_symlink() or (hasattr(installed, 'is_junction') and installed.is_junction()):
        raise ValueError('Installation root must not be a link')
    state_path = installed / 'install-state.json'
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    if state.get('version') != '1.0.3-preview' or state.get('mode') not in ('local-engine', 'owned-mod'):
        raise ValueError('Expected a verified 1.0.3-preview Genesis installation')
    records = {item['path']: item for item in state['files']}
    sources = {}
    for relative in ADDED:
        source = within(ROOT, relative.removeprefix('app/'))
        target = within(installed, relative)
        if not source.is_file():
            raise FileNotFoundError(source)
        if relative in records or target.exists():
            raise FileExistsError('New material already exists: ' + relative)
        sources[relative] = source
    backup = within(installed, 'app/.local/patches/1.0.4-before-world')
    if backup.exists():
        raise FileExistsError('Patch backup already exists: ' + str(backup))
    receipt = {'status': 'READY' if dry_run else 'PATCHED_PREVIEW',
               'version': '1.0.4-preview', 'installed': str(installed),
               'added': list(ADDED), 'backup': str(backup),
               'personalSavesTouched': False, 'restartRequired': True}
    if dry_run:
        return receipt
    backup.mkdir(parents=True)
    shutil.copy2(state_path, backup / 'install-state.json')
    if digest(backup / 'install-state.json') != digest(state_path):
        raise OSError('State backup differs')
    written = []
    try:
        for relative in ADDED:
            target = within(installed, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = target.with_name(target.name + '.patching')
            shutil.copy2(sources[relative], stage)
            if digest(stage) != digest(sources[relative]):
                raise OSError('Staged bytes differ: ' + relative)
            os.replace(stage, target)
            written.append(relative)
            state['files'].append({'path': relative, 'sha256': digest(target),
                                   'bytes': target.stat().st_size})
        state['version'] = '1.0.4-preview'
        staged_state = state_path.with_name(state_path.name + '.patching')
        staged_state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(staged_state, state_path)
    except Exception:
        for relative in reversed(written):
            within(installed, relative).unlink(missing_ok=True)
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
