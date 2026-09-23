"""Check owned Bitter Coast terrain assets in a disposable native game session."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_profile import atomic_text,default_install,prepare

PLAYER_TEST=r'''local core=require('openmw.core')
local self=require('openmw.self')
local vfs=require('openmw.vfs')
local names={'tx_bc_muck.dds','tx_bc_rock_01.dds','tx_bc_grass.dds',
    'tx_ai_dirtroad_01.dds','tx_land_darkgravel.dds','tx_rm_redrock_01.dds',
    'tx_rm_rock_02.dds','tx_ac_dirt_01.dds','tx_rm_grayrock_01.dds',
    'tx_ma_crackedearth.dds'}
local done=false
return {engineHandlers={onFrame=function()
    if done or not self.cell then return end
    done=true
    local ok,err=pcall(function()
        assert(self.cell.isExterior,'Expected exterior terrain')
        for _,name in ipairs(names) do
            local path='textures/'..name
            assert(vfs.fileExists(path),'Missing terrain asset '..path)
            local file=assert(vfs.open(path))
            assert(file:read(4)=='DDS ','Invalid DDS header '..path)
            assert(file:seek('end')==4717676,'VFS did not select owned RGB DDS '..path)
            file:close()
        end
    end)
    print('HALVETH_TERRAIN_'..(ok and 'PASS' or 'FAIL')..' '..(ok and 'tenOwnedDDS=PASS exterior=PASS' or tostring(err)))
    core.quit()
end}}
'''

def run(install_root:Path,state_dir:Path)->dict:
    args=argparse.Namespace(install_root=install_root,state_dir=state_dir,
        source_profile='max',profile='original',smoke=True,
        copy_saves=False,reset_settings=True)
    prepared=prepare(args)
    profile=Path(prepared['profile_dir'])
    data=profile/'data'
    atomic_text(data/'scripts/halveth_genesis_smoke.lua',PLAYER_TEST)
    prepared['command'][-1]='Seyda Neen'
    result={'recordedAt':datetime.now(timezone.utc).isoformat(),
        'scope':'Fresh isolated native OpenMW exterior; VFS resolves ten owned terrain DDS files. No personal saves or visual screenshot.',
        'passed':False,'profileDir':str(profile),'personalSavesUsed':False}
    process=None
    try:
        log=Path(prepared['stdout_log'])
        with log.open('w',encoding='utf-8') as output:
            process=subprocess.Popen(prepared['command'],cwd=prepared['cwd'],
                stdout=output,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result['pid']=process.pid
            result['exitCode']=process.wait(timeout=45)
        lines=Path(prepared['engine_log']).read_text(encoding='utf-8',errors='replace').splitlines()
        result['markers']=[line for line in lines if 'HALVETH_TERRAIN_' in line]
        result['errors']=[line for line in lines if ' E]' in line or 'Lua error' in line]
        result['passed']=(result['exitCode']==0 and not result['errors']
            and any('HALVETH_TERRAIN_PASS' in line for line in result['markers']))
    except Exception as exc:
        result['error']=f'{type(exc).__name__}: {exc}'
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
        atomic_text(state_dir/'result.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root',type=Path,default=default_install())
    parser.add_argument('--state-dir',type=Path)
    args=parser.parse_args()
    state=args.state_dir or ROOT/'.local/terrain-integration'/(
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    result=run(args.install_root.resolve(),state.resolve())
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
