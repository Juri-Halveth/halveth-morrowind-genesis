"""Verify real OpenMW exterior sampling and sparse in-game cues in a disposable game."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare

PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local I=require('openmw.interfaces')
local started,phase,firstCount,done=nil,0,nil,false
local function finish(ok,message)
    if done then return end
    done=true
    print('HALVETH_WORLD_MOMENTS_'..(ok and 'PASS' or 'FAIL')..' '..message)
    core.quit()
end
local function tick()
    if done or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now end
    local moments=assert(I.HALVETHWorldMoments,'World moments interface is missing')
    local s=moments.getState()
    if phase==0 and now-started>12 then
        local okSun,sun=pcall(core.weather.getCurrentSunPercentage,self.cell)
        print('HALVETH_WORLD_MOMENTS_DIAG exterior='..tostring(self.cell.isExterior)..
            ' sunOk='..tostring(okSun)..' sun='..tostring(sun)..
            ' state='..tostring(s.observed and s.observed.source))
        assert(s.enabled and s.observed,'Exterior weather was not observed')
        assert(s.observed.source=='loaded_exterior_weather','Wrong observation source')
        assert(type(s.observed.sun)=='number' and s.observed.sun>=0 and s.observed.sun<=1,
            'Sun sample is out of range')
        assert(s.cueCount==1,'Expected exactly one sparse native cue: '..tostring(s.cueCount))
        firstCount=s.cueCount
        assert(not moments.setEnabled('false'),'Invalid toggle was accepted')
        assert(moments.setEnabled(false),'Could not disable moments')
        phase=1
    elseif phase==1 and now-started>19 then
        assert(not s.enabled and s.cueCount==firstCount,'Disabled moments changed cue count')
        assert(moments.setEnabled(true),'Could not re-enable moments')
        phase=2
    elseif phase==2 and now-started>21 then
        assert(s.enabled and s.cueCount==firstCount,'Re-enable bypassed cooldown')
        finish(true,'exteriorWeather=PASS oneCue=PASS toggle=PASS cooldown=PASS')
    end
    if now-started>30 then finish(false,'Timeout') end
end
return {engineHandlers={onFrame=function()
    local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end
end}}
'''


def run() -> int:
    state = ROOT / '.local' / 'world-moments-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    )
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='original', smoke=True, copy_saves=False, reset_settings=True,
    ))
    data = Path(prepared['profile_dir']) / 'data'
    atomic_text(data / 'scripts' / 'halveth_world_moments_smoke.lua', PLAYER)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'PLAYER: scripts/halveth_world_moments_smoke.lua\n')
    prepared['command'][-1] = 'Seyda Neen'
    log = Path(prepared['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Fresh disposable OpenMW exterior; native sampled light/storm, one cue, toggle and cooldown. No personal saves.',
        'testedFiles': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in ('mod/scripts/halveth/world_moments.lua', 'mod/halveth.omwscripts')},
        'personalSavesUsed': False,
    }
    with log.open('w', encoding='utf-8') as output:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                   stdout=output, stderr=subprocess.STDOUT)
        try:
            result['exitCode'] = process.wait(timeout=50)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            result['exitCode'] = 'TIMEOUT'
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers'] = [line for line in lines if 'HALVETH_WORLD_MOMENTS_' in line]
    result['passed'] = result['exitCode'] == 0 and not result['errors'] and any(
        'HALVETH_WORLD_MOMENTS_PASS' in line for line in lines)
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
