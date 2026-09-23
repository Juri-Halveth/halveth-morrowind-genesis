"""Run the original HALVETH postprocess in an isolated OpenMW 0.51 session."""
import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import configparser
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare


PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local I=require('openmw.interfaces')
local postprocessing=require('openmw.postprocessing')
local started,phase,done=nil,0,false
local function fail(reason)
    done=true;print('HALVETH_VISUALS_FAIL '..reason);core.quit()
end
local function step(t)
    local v=I.HALVETHVisuals
    assert(v,'Visuals interface absent')
    if phase==0 and t>2 then
        phase=1
        assert(v.getState().mode=='scarlet','New-game visual mode missing')
        assert(v.setMode('scarlet'),'Scarlet visual failed to enable')
    elseif phase==1 and t>3 then
        phase=2
        assert(v.getState().enabled,'OpenMW did not compile/enable own shader')
        local found=false
        for _,item in ipairs(postprocessing.getChain()) do
            if item.name=='halveth_atmosphere' then found=true end
        end
        assert(found,'Own shader absent from real render chain')
        assert(v.setMode('dawn'),'Morgenrot mode failed')
    elseif phase==2 and t>4 then
        phase=3
        assert(v.getState().enabled and v.getState().mode=='dawn','Morgenrot mode not active')
        assert(v.setMode('nocturne'),'Nocturne mode failed')
    elseif phase==3 and t>5 then
        phase=4
        assert(v.getState().enabled and v.getState().mode=='nocturne','Nocturne mode not active')
        assert(not v.setMode('invalid-mode'),'Unknown mode accepted')
        assert(v.getState().mode=='nocturne','Unknown mode changed current mode')
        assert(v.setMode('original'),'Original mode failed')
    elseif phase==4 and t>6 then
        phase=5
        assert(not v.getState().enabled,'Original mode left HALVETH shader active')
        local found=false
        for _,item in ipairs(postprocessing.getChain()) do
            if item.name=='halveth_atmosphere' then found=true end
        end
        assert(not found,'HALVETH shader remained in real render chain')
        assert(v.setMode('scarlet'),'Restoring Scarlet mode failed')
    elseif phase==5 and t>7 then
        phase=6
        assert(v.getState().enabled,'Scarlet did not restore after original mode')
        done=true;print('HALVETH_VISUALS_PASS modes=4 shader=halveth_atmosphere')
        core.quit()
    end
    if t>20 then fail('Timeout at phase '..phase) end
end
return {engineHandlers={onFrame=function()
    if done or not self.cell then return end
    if not started then started=core.getRealTime() end
    local ok,err=pcall(step,core.getRealTime()-started)
    if not ok then fail(tostring(err)) end
end}}
'''


def run():
    state = ROOT / '.local' / 'visuals-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    )
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='beauty', smoke=True, copy_saves=False, reset_settings=True,
    ))
    profile, data = Path(prepared['profile_dir']), Path(prepared['profile_dir']) / 'data'
    settings = configparser.ConfigParser(interpolation=None)
    settings.read(profile / 'settings.cfg', encoding='utf-8-sig')
    settings['Video']['window mode'] = '0'
    settings['Video']['minimize on focus loss'] = 'false'
    out = io.StringIO()
    settings.write(out)
    atomic_text(profile / 'settings.cfg', out.getvalue())
    atomic_text(data / 'scripts' / 'halveth_visuals_test.lua', PLAYER)
    live_manifest = (ROOT / 'mod' / 'halveth.omwscripts').read_text(encoding='utf-8')
    visual_registration = '' if 'PLAYER: scripts/halveth/visuals.lua' in live_manifest else (
        'PLAYER: scripts/halveth/visuals.lua\n'
    )
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
        visual_registration + 'PLAYER: scripts/halveth_visuals_test.lua\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(prepared['stdout_log'])
    source_files = ('mod/scripts/halveth/visuals.lua', 'mod/shaders/halveth_atmosphere.omwfx')
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Fresh isolated OpenMW 0.51 game, native shader compile and active render chain. No personal saves.',
        'testedFiles': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files},
        'personalSavesUsed': False,
    }
    with log.open('w', encoding='utf-8') as output:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'], stdout=output, stderr=subprocess.STDOUT)
        print(json.dumps({'pid': process.pid, 'state': str(state)}), flush=True)
        try:
            result['exitCode'] = process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            result['exitCode'] = 'TIMEOUT'
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers'] = [line for line in lines if 'HALVETH_VISUALS_' in line]
    result['passed'] = result['exitCode'] == 0 and not result['errors'] and any(
        'HALVETH_VISUALS_PASS' in line for line in lines
    )
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
