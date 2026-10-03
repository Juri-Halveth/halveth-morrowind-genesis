-- SPDX-License-Identifier: MIT
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local util=require('openmw.util')
local I=require('openmw.interfaces')
local C=require('scripts.veyra_wildlife.config')
local meta,active,enabled=false,false,false
local phase,goal,destination,last,previous,distance='WAIT_INIT',nil,nil,-100,nil,0
local function own()return type(meta)=='table'and meta.actorId==self.id and meta.recordId==self.recordId and self.contentFile==nil end
local function report()
    if own()then core.sendGlobalEvent('VEYRA_WildReport',{actor=self.object,phase=phase,distance=distance})end
end
local function ready()
    if active and own()then phase='READY';report()end
end
local function stop()if active and own()then I.AI.removePackages('Travel')end end
local function update()
    if not active or not own()or not enabled or not goal or core.isWorldPaused()then return end
    if types.Actor.isDead(self)then phase='DEAD_HOLD';report();return end
    local package=I.AI.getActivePackage()
    if I.AI.isFleeing()or package and(package.type=='Combat'or package.type=='Pursue')then phase='COMBAT_DEFERRED';report();return end
    local now=core.getSimulationTime()
    if not destination then
        if now-last<1 then return end;last=now
        local bounds=types.Actor.getPathfindingAgentBounds(self)
        local flags=nearby.NAVIGATOR_FLAGS.Walk+nearby.NAVIGATOR_FLAGS.OpenDoor
        local projected=nearby.findNearestNavMeshPosition(util.vector3(goal.x,goal.y,goal.z),{
            agentBounds=bounds,includeFlags=flags,searchAreaHalfExtents=util.vector3(140,140,240)})
        if not projected then phase='WAIT_NAV';report();return end
        local status=nearby.findPath(self.position,projected,{agentBounds=bounds,includeFlags=flags,destinationTolerance=30})
        if status~=nearby.FIND_PATH_STATUS.Success then phase='WAIT_NAV';report();return end
        destination=projected;previous=self.position
        I.AI.startPackage({type='Travel',destPosition=destination,isRepeat=false,cancelOther=true})
        phase='TRAVEL_STARTED';report();return
    end
    if now-last<.25 then return end;last=now
    local position=self.position
    local step=util.vector2(position.x-previous.x,position.y-previous.y):length()
    if step>250 then stop();enabled=false;phase='POSITION_JUMP_HOLD';report();return end
    distance=distance+step;previous=position
    if(position-destination):length()<70 then stop();goal=nil;phase=distance>64 and 'ARRIVED_OBSERVED'or 'POSITION_ONLY';report()
    else phase='TRAVEL_PROGRESS';report()end
end
local function init(data)
    if type(data)=='table'and data.schema==C.schema and data.frontierSha256==C.frontierSha256 then meta=data end
end
return {interfaceName='VeyraWildCreature',interface={version=1,getState=function()return{phase=phase,distance=distance}end},
 engineHandlers={onInit=init,onActive=function()
    active=true
    if own()then types.Actor.stats.ai.fight(self).base=0;types.Actor.stats.ai.fight(self).modifier=0 end
    destination=nil;goal=nil;previous=nil;distance=0;ready()
 end,onInactive=function()active=false;destination=nil;goal=nil;previous=nil end,onUpdate=update,
 onSave=function()return{schema=C.schema,meta=meta}end,onLoad=function(data)
    active=false;enabled=false;destination=nil;goal=nil;previous=nil
    if type(data)=='table'and data.schema==C.schema then init(data.meta)end
 end},eventHandlers={
 VEYRA_WildPing=ready,
 VEYRA_WildEnabled=function(data)if type(data)=='table'and type(data.enabled)=='boolean'then enabled=data.enabled;if not enabled then stop()end end end,
 VEYRA_WildGoal=function(data)
    if not own()or not enabled or type(data)~='table'or data.x~=C.target.x or data.y~=C.target.y or data.z~=C.target.z then return end
    goal=C.target;destination=nil;previous=nil;distance=0;last=-100
 end}}
