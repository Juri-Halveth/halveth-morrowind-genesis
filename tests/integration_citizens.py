"""Exercise opt-in HALVETH citizens against an isolated installed OpenMW game."""
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
local nearby=require('openmw.nearby')
local types=require('openmw.types')
local phase,started,entered,origin,ids,first,furthest,wandered,inspection,done=
    'start',nil,nil,nil,nil,nil,{0,0},{},nil,false
local function finish(ok,detail)
    if done then return end
    done=true
    print('HALVETH_CITIZENS_'..(ok and 'PASS' or 'FAIL')..' '..detail)
    core.quit()
end
local function nextPhase(value)
    phase=value;entered=core.getRealTime()
    print('HALVETH_CITIZENS_PHASE '..value)
end
local function distance(a,b)
    if not a or not b then return 0 end
    local dx=a.x-b.x;local dy=a.y-b.y;local dz=a.z-b.z
    return math.sqrt(dx*dx+dy*dy+dz*dz)
end
local function tick()
    if done or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>100 then error('Timeout '..phase) end
    local api=assert(I.HALVETHCitizens,'Citizens interface not loaded')
    local state=api.getState()
    if phase=='start' and now-entered>1 then
        -- The production microphone consent panel intentionally pauses the world.
        -- This isolated AI-motion test declines it; no audio is opened.
        if I.HALVETHMicrophone then I.HALVETHMicrophone.decline() end
        -- Character-origin choice is another intentional new-game modal.
        if I.HALVETHOrigin and I.HALVETHOrigin.getState().armed then
            I.HALVETHOrigin.select('journey')
        end
        assert(self.cell.isExterior,'Test did not start outdoors')
        assert(#state.people==0,'Unexpected previous citizens')
        assert(api.spawn(),'Spawn request failed')
        nextPhase('spawn')
    elseif phase=='spawn' and #state.people==2 and state.people[1].loaded
        and state.people[2].loaded then
        assert(state.people[1].actorId~=state.people[2].actorId,'Duplicate generated actor ID')
        ids={state.people[1].actorId,state.people[2].actorId}
        first={state.people[1].position,state.people[2].position}
        print('HALVETH_CITIZENS_SPAWNED '..ids[1]..' '..ids[2])
        for _,actor in ipairs(nearby.actors) do
            if actor.id==ids[1] or actor.id==ids[2] then
                local health=types.Actor.stats.dynamic.health(actor)
                local record=actor.type.record(actor)
                assert(health.current>0 and not types.Actor.isDead(actor),'Generated actor has no health')
                assert(record.mwscript=='' or record.mwscript==nil,'Inherited Bethesda script')
                for service,offered in pairs(record.servicesOffered) do
                    assert(not offered,'Inherited service: '..service)
                end
                print('HALVETH_CITIZENS_HEALTH '..actor.id..' current='..tostring(health.current)
                    ..' base='..tostring(health.base)..' dead='..tostring(types.Actor.isDead(actor)))
            end
        end
        nextPhase('moving')
    elseif phase=='moving' then
        for i,person in ipairs(state.people) do
            furthest[i]=math.max(furthest[i],distance(first[i],person.position))
        end
        if furthest[1]>15 and furthest[2]>15 then
            print('HALVETH_CITIZENS_MOVED '..ids[1]..'='..string.format('%.1f',furthest[1])
                ..' '..ids[2]..'='..string.format('%.1f',furthest[2]))
            wandered={}
            nextPhase('handoff')
        elseif now-entered>60 then error('Both citizens must move: '..ids[1]..'='..string.format('%.1f',furthest[1])
            ..' '..ids[2]..'='..string.format('%.1f',furthest[2])) end
    elseif phase=='handoff' then
        if wandered[ids[1]] and wandered[ids[2]] then
            print('HALVETH_CITIZENS_WANDER_HANDOFF '..ids[1]..' '..ids[2])
            origin={x=self.position.x,y=self.position.y,z=self.position.z}
            core.sendGlobalEvent('HALVETH_CitizensTestTravel',{player=self.object,phase='away'})
            nextPhase('leaving')
        elseif now-entered>30 then error('Both citizens must transition to Wander') end
    elseif phase=='leaving' and not self.cell.isExterior then
        assert(api.refresh(),'Status request after cell change failed')
        nextPhase('away')
    elseif phase=='away' and #state.people==2 and not state.people[1].loaded
        and not state.people[2].loaded then
        assert(api.dismiss(),'Offscreen removal request failed')
        nextPhase('dismissed')
    elseif phase=='dismissed' and #state.people==0 and state.retiredCount==2 then
        assert(state.success,'Offscreen dismissal did not succeed')
        require('openmw.types').Player.sendMenuEvent(self,'HALVETH_CitizensSave',{slot='citizens-isolated'})
        nextPhase('saved')
    elseif phase=='reloaded' and now-entered>2 then
        assert(#state.people==0 and state.retiredCount==2,'Removal intent lost across save/reload')
        core.sendGlobalEvent('HALVETH_CitizensTestTravel',
            {player=self.object,phase='home',origin=origin})
        nextPhase('returning')
    elseif phase=='returning' and self.cell.isExterior
        and distance(origin,{x=self.position.x,y=self.position.y,z=self.position.z})<128 then
        nextPhase('revisited')
    elseif phase=='revisited' and now-entered>4 then
        core.sendGlobalEvent('HALVETH_CitizensTestInspect',{player=self.object,ids=ids})
        nextPhase('inspecting')
    elseif phase=='inspecting' and inspection then
        assert(inspection.originals>0,'Original Morrowind NPCs absent in test cell')
        assert(inspection.retiredFound==0,'Retired HALVETH citizens remain in loaded cell')
        assert(state.retiredCount==0,'Retirement entries did not clear after revisit')
        finish(true,'ownedSpawn=PASS bothNativeAIMovement=PASS bothWanderHandoff=PASS noInheritedServices=PASS offscreenDismiss=PASS actualSaveReload=PASS originalNPCsPreserved=PASS')
    end
end
return {eventHandlers={HALVETH_CitizensTestInspectResult=function(data)inspection=data end,
    HALVETH_CitizensTestPackage=function(data)
        if phase=='handoff' and data.package=='Wander' then wandered[data.actorId]=true end
    end},
engineHandlers={onFrame=function()
    local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end
end,onSave=function()return {phase=phase,ids=ids,origin=origin}end,
onLoad=function(data)
    assert(data and data.phase=='saved','Unexpected isolated save')
    if I.HALVETHMicrophone then I.HALVETHMicrophone.decline() end
    ids,origin=data.ids,data.origin;inspection=nil;done=false
    started=core.getRealTime();nextPhase('reloaded')
end}}
'''

GLOBAL=r'''local util=require('openmw.util')
local world=require('openmw.world')
local core=require('openmw.core')
local last=0
local function travel(data)
    if data.phase=='away' then
        data.player:teleport('Seyda Neen, Census and Excise Office',util.vector3(100,180,193))
    elseif data.phase=='home' then
        local p=data.origin
        data.player:teleport('',util.vector3(p.x,p.y,p.z))
    end
end
local function inspect(data)
    local retiredFound,originals=0,0
    for _,actor in ipairs(world.activeActors) do
        if actor.contentFile~=nil then originals=originals+1 end
        for _,id in ipairs(data.ids) do
            if actor.id==id then retiredFound=retiredFound+1 end
        end
    end
    data.player:sendEvent('HALVETH_CitizensTestInspectResult',
        {retiredFound=retiredFound,originals=originals})
end
return {eventHandlers={HALVETH_CitizensTestTravel=travel,HALVETH_CitizensTestInspect=inspect,
    HALVETH_CitizensTestPackage=function(data)
        local player=world.players[1]
        if player then player:sendEvent('HALVETH_CitizensTestPackage',data) end
    end},
    engineHandlers={onUpdate=function()
        local now=core.getRealTime()
        if now-last>4 then last=now;print('HALVETH_CITIZENS_WORLD paused='..tostring(world.isWorldPaused())) end
    end}}
'''

MENU=r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_CitizensSave=function(data)
    assert(not pending and not loaded and data.slot=='citizens-isolated','Unexpected save request')
    pending=data.slot
    menu.saveGame('HALVETH isolated citizens integration',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated citizens integration' then
            print('HALVETH_CITIZENS_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true;menu.loadGame(dir,slot);return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_CITIZENS_FAIL isolated save absent');menu.quit()
    end
end}}
'''

NPC=r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local nextAt,count=0,0
return {engineHandlers={onUpdate=function()
    if not tostring(self.recordId):lower():match('^generated:') or count>=15
        or core.getRealTime()<nextAt then return end
    count=count+1;nextAt=core.getRealTime()+2
    local ai=I.AI and I.AI.getActivePackage()
    core.sendGlobalEvent('HALVETH_CitizensTestPackage',
        {actorId=self.id,package=ai and ai.type or 'nil'})
    print('HALVETH_CITIZENS_NPC '..self.id..' dead='..tostring(types.Actor.isDead(self))
        ..' canMove='..tostring(types.Actor.canMove(self))
        ..' inRange='..tostring(types.Actor.isInActorsProcessingRange(self))
        ..' onGround='..tostring(types.Actor.isOnGround(self))
        ..' swimming='..tostring(types.Actor.isSwimming(self))
        ..' x='..tostring(self.position.x)..' y='..tostring(self.position.y)
        ..' package='..tostring(ai and ai.type or 'nil'))
end}}
'''

def run()->int:
    state=ROOT/'.local'/'citizens-integration'/(
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    prepared=prepare(argparse.Namespace(install_root=default_install(),state_dir=state,
        source_profile='max',profile='original',smoke=True,copy_saves=False,reset_settings=True))
    data=Path(prepared['profile_dir'])/'data'
    atomic_text(data/'scripts/halveth_citizens_smoke.lua',PLAYER)
    atomic_text(data/'scripts/halveth_citizens_global_smoke.lua',GLOBAL)
    atomic_text(data/'scripts/halveth_citizens_menu.lua',MENU)
    atomic_text(data/'scripts/halveth_citizens_npc.lua',NPC)
    atomic_text(data/'halveth-genesis-smoke.omwscripts',
        'MENU: scripts/halveth_citizens_menu.lua\n'
        'GLOBAL: scripts/halveth_citizens_global_smoke.lua\n'
        'PLAYER: scripts/halveth_citizens_smoke.lua\n'
        'NPC: scripts/halveth_citizens_npc.lua\n')
    atomic_text(data/'bridge/inbox.json','{}\n')
    atomic_text(data/'bridge/companion-status.json','{"status":"offline"}\n')
    prepared['command'][-1]='Seyda Neen'
    log=Path(prepared['stdout_log'])
    result={'recordedAt':datetime.now(timezone.utc).isoformat(),
        'scope':'Disposable installed OpenMW; exact generated citizens, real movement and save/reload; no personal saves.',
        'sourceSha256':hashlib.sha256((ROOT/'mod/scripts/halveth/citizens_global.lua').read_bytes()).hexdigest(),
        'personalSavesUsed':False}
    with log.open('w',encoding='utf-8') as output:
        process=subprocess.Popen(prepared['command'],cwd=prepared['cwd'],stdout=output,stderr=subprocess.STDOUT)
        print(json.dumps({'pid':process.pid,'state':str(state)}),flush=True)
        try: result['exitCode']=process.wait(timeout=115)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=10);result['exitCode']='TIMEOUT'
    lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
    result['errors']=[line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers']=[line for line in lines if 'HALVETH_CITIZENS_' in line]
    result['passed']=result['exitCode']==0 and not result['errors'] and any(
        'HALVETH_CITIZENS_PASS' in line for line in lines)
    atomic_text(state/'result.json',json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result['passed'] else 1

if __name__=='__main__': raise SystemExit(run())
