"""Prove opt-in generated NPC movement in a disposable native OpenMW game."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_profile import atomic_text,default_install,prepare

PLAYER=r'''local core=require('openmw.core')
local self=require('openmw.self')
local I=require('openmw.interfaces')
local phase,started,entered,initial,actorId,done='start',nil,nil,nil,nil,false
local function finish(ok,why)
    if done then return end
    done=true
    print('HALVETH_ACTOR_LIFE_'..(ok and 'PASS' or 'FAIL')..' '..why)
    core.quit()
end
local function nextPhase(next) phase=next;entered=core.getRealTime() end
local function distance(a,b)
    if not a or not b then return 0 end
    local dx=a.x-b.x;local dy=a.y-b.y;local dz=a.z-b.z
    return math.sqrt(dx*dx+dy*dy+dz*dz)
end
local function tick()
    if done or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>75 then error('Timeout '..phase) end
    local ambient=assert(I.HALVETHAmbient,'Native ambient interface missing')
    local a=ambient.getState()
    if phase=='start' and now-entered>1 then
        assert(self.cell.isExterior,'Smoke start is not outdoors: '..tostring(self.cell.name))
        assert(not a.actorId,'Unexpected pre-existing ambient actor')
        assert(ambient.spawn(),'Spawn request was not sent')
        nextPhase('spawn')
    elseif phase=='spawn' and a.actorId and a.loaded and a.position then
        actorId=a.actorId;initial=a.position
        print('HALVETH_ACTOR_LIFE_SPAWNED '..actorId..' '..tostring(initial.x)..','..tostring(initial.y))
        nextPhase('moving')
    elseif phase=='moving' then
        local moved=distance(initial,a.position)
        if moved>40 then
            print('HALVETH_ACTOR_LIFE_MOVED '..string.format('%.1f',moved))
            assert(ambient.pause(),'Pause request failed')
            nextPhase('paused')
        elseif now-entered>35 then error('Wander package did not move generated NPC; distance='..string.format('%.1f',moved)) end
    elseif phase=='paused' and now-entered>2 then
        assert(ambient.resume(),'Resume request failed')
        nextPhase('resumed')
    elseif phase=='resumed' and now-entered>2 then
        assert(a.actorId==actorId and a.loaded,'Generated actor disappeared before save')
        nextPhase('saved')
        require('openmw.types').Player.sendMenuEvent(self,'HALVETH_ActorSave',{slot='actor-life-isolated'})
    elseif phase=='reloaded' and now-entered>3 then
        assert(a.actorId==actorId and a.loaded,'Generated actor missing after real save reload')
        assert(ambient.dismiss(),'Dismiss request failed')
        nextPhase('dismissed')
    elseif phase=='dismissed' and now-entered>2 then
        assert(not a.actorId and not a.loaded,'Dismiss did not clear only generated actor')
        finish(true,'ownActor=PASS realWanderMovement=PASS pauseResume=PASS actualSaveReload=PASS ownActorDismiss=PASS')
    end
end
return {engineHandlers={onFrame=function()
    local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end
end,onSave=function()return {phase=phase,actorId=actorId}end,onLoad=function(data)
    assert(data and data.phase=='saved','Unexpected isolated save')
    actorId=data.actorId;done=false;started=core.getRealTime();nextPhase('reloaded')
    print('HALVETH_ACTOR_LIFE_RELOADED '..tostring(actorId))
end}}
'''

MENU=r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_ActorSave=function(data)
    assert(not pending and not loaded and data.slot=='actor-life-isolated','Unexpected save request')
    pending=data.slot
    menu.saveGame('HALVETH isolated actor life',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated actor life' then
            print('HALVETH_ACTOR_LIFE_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true;menu.loadGame(dir,slot);return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_ACTOR_LIFE_FAIL isolated save absent');menu.quit()
    end
end}}
'''

def run()->int:
    state=ROOT/'.local'/'actor-life-integration'/(
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    prepared=prepare(argparse.Namespace(install_root=default_install(),state_dir=state,
        source_profile='max',profile='original',smoke=True,copy_saves=False,reset_settings=True))
    data=Path(prepared['profile_dir'])/'data'
    atomic_text(data/'scripts/halveth_actor_life_smoke.lua',PLAYER)
    atomic_text(data/'scripts/halveth_actor_life_menu.lua',MENU)
    atomic_text(data/'halveth-genesis-smoke.omwscripts',
        'MENU: scripts/halveth_actor_life_menu.lua\n'
        'PLAYER: scripts/halveth_actor_life_smoke.lua\n')
    atomic_text(data/'bridge/inbox.json','{}\n')
    atomic_text(data/'bridge/companion-status.json','{"status":"offline"}\n')
    prepared['command'][-1]='Seyda Neen'
    log=Path(prepared['stdout_log'])
    result={'recordedAt':datetime.now(timezone.utc).isoformat(),
        'scope':'Disposable exterior OpenMW game; generated actor only; measured movement and actual save reload.',
        'globalSourceSha256':hashlib.sha256((ROOT/'mod/scripts/halveth/actor_life_global.lua').read_bytes()).hexdigest(),
        'personalSavesUsed':False}
    with log.open('w',encoding='utf-8') as output:
        process=subprocess.Popen(prepared['command'],cwd=prepared['cwd'],stdout=output,stderr=subprocess.STDOUT)
        print(json.dumps({'pid':process.pid,'state':str(state)}),flush=True)
        try: result['exitCode']=process.wait(timeout=85)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=10);result['exitCode']='TIMEOUT'
    lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
    result['errors']=[line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers']=[line for line in lines if 'HALVETH_ACTOR_LIFE_' in line]
    result['passed']=(result['exitCode']==0 and not result['errors']
        and any('HALVETH_ACTOR_LIFE_PASS' in line for line in lines))
    atomic_text(state/'result.json',json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result['passed'] else 1

if __name__=='__main__': raise SystemExit(run())
