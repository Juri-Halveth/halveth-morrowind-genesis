"""Patch one existing 1.0.1 installation with the 1.0.2 native preview.

Only named owned app files are touched. The installer manifest is checked first,
previous bytes and state are backed up, and failure rolls back each touched file.
User profiles, original game assets and saves are never opened or copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
CHANGED=(
    'app/mod/halveth.omwscripts',
    'app/mod/scripts/halveth/global.lua',
    'app/mod/scripts/halveth/menu_portal.lua',
    'app/mod/scripts/halveth/player.lua',
    'app/server.py',
)
ADDED=(
    'app/mod/scripts/halveth/origin.lua',
    'app/mod/Textures/tx_bc_muck.dds',
    'app/mod/Textures/tx_bc_rock_01.dds',
    'app/mod/Textures/tx_bc_grass.dds',
)

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def within(root:Path,relative:str)->Path:
    target=root.joinpath(*relative.split('/'))
    if not target.resolve(strict=False).is_relative_to(root):
        raise ValueError('Patch path escapes installation: '+relative)
    return target

def preflight(installed:Path)->tuple[dict,dict,dict]:
    installed=installed.resolve(strict=True)
    if installed.is_symlink() or (hasattr(installed,'is_junction') and installed.is_junction()):
        raise ValueError('Installation root must not be a link')
    state_path=installed/'install-state.json'
    state=json.loads(state_path.read_text(encoding='utf-8-sig'))
    if state.get('version')!='1.0.1' or state.get('mode') not in ('local-engine','owned-mod'):
        raise ValueError('Expected a verified Genesis 1.0.1 installation')
    records={record['path']:record for record in state['files']}
    sources={}
    for relative in CHANGED+ADDED:
        source=within(ROOT,relative.removeprefix('app/'))
        if not source.is_file(): raise FileNotFoundError(source)
        target=within(installed,relative)
        if relative in CHANGED:
            if relative not in records or not target.is_file():
                raise ValueError('Expected installed file missing: '+relative)
            if target.stat().st_size!=records[relative]['bytes'] or digest(target)!=records[relative]['sha256']:
                raise ValueError('Installed file changed independently: '+relative)
        elif target.exists() or relative in records:
            raise FileExistsError('New preview file already exists: '+relative)
        sources[relative]=source
    return state,records,sources

def apply(installed:Path,dry_run:bool=False)->dict:
    installed=installed.resolve(strict=True)
    state,records,sources=preflight(installed)
    backup=installed/'app'/'.local'/'patches'/'1.0.2-before-reborn'
    if backup.exists(): raise FileExistsError('Patch backup already exists: '+str(backup))
    receipt={'status':'READY' if dry_run else 'PATCHED_PREVIEW',
        'version':'1.0.2-preview','installed':str(installed),
        'changed':list(CHANGED),'added':list(ADDED),'backup':str(backup),
        'personalSavesTouched':False}
    if dry_run: return receipt
    backup.mkdir(parents=True)
    state_path=installed/'install-state.json'
    written=[]
    try:
        for relative in CHANGED:
            source=within(installed,relative)
            copy=backup/relative
            copy.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,copy)
            if digest(copy)!=digest(source): raise OSError('Backup differs: '+relative)
        shutil.copy2(state_path,backup/'install-state.json')
        if digest(backup/'install-state.json')!=digest(state_path):
            raise OSError('State backup differs')
        for relative in CHANGED+ADDED:
            target=within(installed,relative)
            target.parent.mkdir(parents=True,exist_ok=True)
            staged=target.with_name(target.name+'.patching')
            shutil.copy2(sources[relative],staged)
            if digest(staged)!=digest(sources[relative]): raise OSError('Staged copy differs: '+relative)
            os.replace(staged,target)
            written.append(relative)
            entry={'path':relative,'sha256':digest(target),'bytes':target.stat().st_size}
            if relative in records: records[relative].update(entry)
            else: state['files'].append(entry)
        state['version']='1.0.2-preview'
        staged_state=state_path.with_name(state_path.name+'.patching')
        staged_state.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.replace(staged_state,state_path)
    except Exception:
        for relative in reversed(written):
            target=within(installed,relative)
            if relative in CHANGED: shutil.copy2(backup/relative,target)
            else: target.unlink(missing_ok=True)
        shutil.copy2(backup/'install-state.json',state_path)
        raise
    (backup/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return receipt

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed',type=Path,required=True)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    print(json.dumps(apply(args.installed,args.dry_run),ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
