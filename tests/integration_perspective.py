"""Verify player-centred camera controls inside an isolated real OpenMW session."""
import argparse
import configparser
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import prepare, default_install, atomic_text

PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local camera=require('openmw.camera')
local I=require('openmw.interfaces')
local started,done,phase,initial=nil,false,0,nil
local function finish(ok,text)
    done=true
    print('HALVETH_PERSPECTIVE_'..(ok and 'PASS' or 'FAIL')..' '..text)
    core.quit()
end
local function run()
    local view=I.HALVETHPerspective
    assert(view,'Native perspective interface missing')
    initial=camera.getMode()
    local state=view.getState()
    assert(state.cell~='' and state.scope=='LOADED_ACTORS_IN_VIEWPORT_PROJECTION','Bound current scene missing')
    assert(state.lineOfSightChecked==false,'Viewport projection falsely claims line of sight')
    assert(type(state.inFrame)=='table','Nearby viewport list absent')
    assert(not view.setView('invalid'),'Unknown view accepted')
    assert(view.setView('first') and camera.getMode()==camera.MODE.FirstPerson,'First person mode failed')
    assert(view.setView('third') and camera.getMode()==camera.MODE.ThirdPerson,'Third person mode failed')
    assert(view.setView('look') and camera.getMode()==camera.MODE.Preview,'Free look mode failed')
    local yaw=camera.getYaw()
    assert(view.turn(15),'Turn refused')
    assert(math.abs(camera.getYaw()-yaw-math.rad(15))<0.01,'Actual camera yaw unchanged')
    assert(not view.turn(360),'Unbounded turn accepted')
    assert(view.zoom(-60),'Third person zoom failed')
    view.open()
    assert(view.isOpen(),'Native in-game camera panel absent')
    assert(view.reset(),'Original view reset failed')
    assert(camera.getMode()==camera.MODE.Preview,'Panel baseline not restored')
    view.close()
    assert(not view.isOpen(),'Camera panel did not close')
    local context=I.HALVETH.getContext()
    assert(context.viewpoint and context.viewpoint.scope==state.scope,'JARVIS lacks bounded player viewpoint')
    assert(view.setView('third'),'Third-person hold failed')
end
return {engineHandlers={onFrame=function()
    if done or not self.cell then return end
    if not started then started=core.getRealTime() end
    local elapsed=core.getRealTime()-started
    if phase==0 and elapsed>2 then
        phase=1
        local ok,error=pcall(run)
        if not ok then finish(false,tostring(error)) end
    elseif phase==1 and elapsed>3.5 then
        phase=2
        local ok,error=pcall(function()
            assert(camera.getMode()==camera.MODE.ThirdPerson,'Third person did not persist after a frame')
            assert(I.HALVETHPerspective.setView('first'),'First-person hold failed')
        end)
        if not ok then finish(false,tostring(error)) end
    elseif phase==2 and elapsed>5 then
        local ok,error=pcall(function()
            assert(camera.getMode()==camera.MODE.FirstPerson,'First person did not persist after a frame')
            camera.setMode(initial,true)
        end)
        if not ok then finish(false,tostring(error))
        else finish(true,'first=PASS third=PASS freeLook=PASS persistentModes=PASS turn=PASS zoom=PASS nativePanel=PASS context=PASS') end
    end
    if elapsed>20 then finish(false,'Timeout') end
end}}
'''


def run():
    state = ROOT / '.local' / 'perspective-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    )
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='beauty', smoke=True, copy_saves=False, reset_settings=True,
    ))
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    settings = configparser.ConfigParser(interpolation=None)
    settings.read(profile / 'settings.cfg', encoding='utf-8-sig')
    settings['Video']['window mode'] = '0'
    settings['Video']['minimize on focus loss'] = 'false'
    output = io.StringIO()
    settings.write(output)
    atomic_text(profile / 'settings.cfg', output.getvalue())
    atomic_text(data / 'scripts/halveth_perspective_test.lua', PLAYER)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'PLAYER: scripts/halveth_perspective_test.lua\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(prepared['stdout_log'])
    tested = ('mod/scripts/halveth/perspective.lua', 'mod/scripts/halveth/universe.lua',
              'mod/scripts/halveth/player.lua', 'mod/halveth.omwscripts')
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Fresh isolated OpenMW 0.51 game with native camera and actual nearby actors. No personal save.',
        'testedFiles': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in tested},
        'personalSavesUsed': False,
    }
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                   stdout=stream, stderr=subprocess.STDOUT)
        print(json.dumps({'pid': process.pid, 'state': str(state)}), flush=True)
        try:
            result['exitCode'] = process.wait(timeout=50)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            result['exitCode'] = 'TIMEOUT'
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers'] = [line for line in lines if 'HALVETH_PERSPECTIVE_' in line]
    result['passed'] = result['exitCode'] == 0 and not result['errors'] and any(
        'HALVETH_PERSPECTIVE_PASS' in line for line in lines
    )
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
