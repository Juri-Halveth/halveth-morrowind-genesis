"""Native new-game origin, UTF-8 stress, and save/load in an isolated profile."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare

PLAYER_TEST = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')
local phase,entered,finished='start',nil,false
local function finish(ok,detail)
    if finished then return end
    finished=true
    print('HALVETH_ORIGIN_INTEGRATION_'..(ok and 'PASS' or 'FAIL')..' '..detail)
    core.quit()
end
local function tick()
    if finished or not self.cell or not self.cell.isExterior then return end
    local now=core.getRealTime()
    if not entered then entered=now end
    if now-entered>25 then error('Timeout '..phase) end
    if phase=='start' and now-entered>0.8 then
        local origin=I.HALVETHOrigin
        assert(origin,'Origin interface missing')
        local s=origin.getState()
        assert(s.armed and not s.completed,'New-game event did not arm origin')
        assert(I.UI.getMode()=='Interface','Native origin modal did not open')
        assert(not origin.select('invalid'),'Unknown choice accepted')
        assert(not origin.select(''),'Empty choice accepted')
        local parts={'A','ä','❤️','界','𐍈'}
        math.randomseed(127)
        for i=1,1000 do
            local source={}
            for j=1,math.random(1,90) do source[#source+1]=parts[math.random(#parts)] end
            local value=table.concat(source)
            local limit=math.random(1,160)
            local head=C.head(value,limit)
            assert(#head<=limit,'Head exceeded byte limit at '..i)
            assert(utf8.len(head),'Head split a UTF-8 codepoint at '..i)
            assert(value:sub(1,#head)==head,'Head changed source content at '..i)
        end
        assert(origin.select('love'),'Valid origin choice failed')
        s=origin.getState()
        assert(s.completed and not s.armed and s.choice=='love','Choice was not committed')
        assert(s.counterpart=='woman' or s.counterpart=='man','Counterpart missing')
        assert(not origin.select('journey'),'Completed origin accepted a second choice')
        assert(I.UI.getMode()~='Interface','Origin left its native mode open')
        phase='saved';entered=now
        types.Player.sendMenuEvent(self,'HALVETH_OriginSave',{slot='halveth-origin-isolated'})
    elseif phase=='reloaded' and now-entered>0.5 then
        local s=I.HALVETHOrigin.getState()
        assert(s.completed and not s.armed and s.choice=='love','Origin lost across save/load')
        assert(not I.HALVETHOrigin.select('witness'),'Reloaded origin accepted second choice')
        assert(I.UI.getMode()~='Interface','Reloaded origin reopened modal')
        finish(true,'newGame=PASS nativeModal=PASS invalidChoices=PASS randomUtf8=1000 modeCleanup=PASS actualSaveReload=PASS')
    end
end
return {engineHandlers={
    onFrame=function() local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end end,
    onSave=function() return {phase=phase} end,
    onLoad=function(data)
        assert(data and data.phase=='saved','Unexpected test save')
        phase='reloaded';entered=core.getRealTime();finished=false
        print('HALVETH_ORIGIN_INTEGRATION_RELOADED')
    end}}
'''

MENU_TEST = r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_OriginSave=function(data)
    assert(not pending and not loaded and data.slot=='halveth-origin-isolated','Unexpected save request')
    pending=data.slot
    menu.saveGame('HALVETH isolated origin integration',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated origin integration' then
            print('HALVETH_ORIGIN_INTEGRATION_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true;menu.loadGame(dir,slot)
            return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_ORIGIN_INTEGRATION_FAIL Save did not materialize');menu.quit()
    end
end}}
'''

def run(install_root: Path, state_dir: Path) -> dict:
    args = argparse.Namespace(install_root=install_root, state_dir=state_dir,
        source_profile='max', profile='original', smoke=True,
        copy_saves=False, reset_settings=True)
    prepared = prepare(args)
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    atomic_text(data / 'scripts/halveth_genesis_smoke.lua', PLAYER_TEST)
    atomic_text(data / 'scripts/halveth_origin_test_menu.lua', MENU_TEST)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
        'MENU: scripts/halveth_origin_test_menu.lua\nPLAYER: scripts/halveth_genesis_smoke.lua\n')
    script_run = state_dir / 'origin-console.txt'
    atomic_text(script_run, 'coc "Seyda Neen"\n')
    command = prepared['command'][:-2] + ['--new-game=1', '--script-run', str(script_run)]
    log = Path(prepared['stdout_log'])
    result = {'recordedAt':datetime.now(timezone.utc).isoformat(),
        'scope':'Fresh native Morrowind game; origin event/modal, 1000 deterministic UTF-8 truncation cases, choice and actual isolated save/load.',
        'passed':False, 'profileDir':str(profile), 'log':str(log),
        'personalSavesUsed':False}
    process = None
    try:
        with log.open('w',encoding='utf-8') as output:
            process=subprocess.Popen(command,cwd=prepared['cwd'],stdout=output,
                stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result['pid']=process.pid
            result['exitCode']=process.wait(timeout=90)
        lines=Path(prepared['engine_log']).read_text(encoding='utf-8',errors='replace').splitlines()
        result['markers']=[line for line in lines if 'HALVETH_ORIGIN_' in line]
        result['warnings']=[line for line in lines if "Failed to open video: Resource 'video/new_game.webm' not found" in line]
        result['errors']=[line for line in lines if (' E]' in line or 'Lua error' in line)
            and "Failed to open video: Resource 'video/new_game.webm' not found" not in line]
        result['testSaveFiles']=[str(p.relative_to(profile)) for p in profile.rglob('*.omwsave')]
        result['passed']=(result['exitCode']==0 and not result['errors']
            and any('HALVETH_ORIGIN_INTEGRATION_PASS' in line for line in result['markers'])
            and any('HALVETH_ORIGIN_INTEGRATION_RELOADED' in line for line in result['markers'])
            and len(result['testSaveFiles'])==1)
    except Exception as exc:
        result['error']=f'{type(exc).__name__}: {exc}'
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
        atomic_text(state_dir/'result.json',json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root',type=Path,default=default_install())
    parser.add_argument('--state-dir',type=Path)
    args=parser.parse_args()
    state=args.state_dir or ROOT/'.local/origin-integration'/(
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    result=run(args.install_root.resolve(),state.resolve())
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result['passed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
