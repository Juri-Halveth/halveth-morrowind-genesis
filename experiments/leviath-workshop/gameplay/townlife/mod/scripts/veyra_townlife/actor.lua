-- SPDX-License-Identifier: MIT
-- CUSTOM on this module's generated NPCs only. Native integration NOT_RUN.
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local util=require('openmw.util')
local I=require('openmw.interfaces')
local C=require('scripts.veyra_townlife.config')
local roleConfig={};for _,r in ipairs(C.roles)do roleConfig[r.id]=r end
local state={schema=C.saveSchema,enabled=false,phase='WAIT_INIT',awaitAuthority=true,
    replans=0,totalMeasuredDistance=0,windowDistance=0,observationContinuity='INITIAL_WINDOW'}
local active=false
local lastSample,lastProgress,lastNavTry=-100,-100,-100
local previous,windowOrigin,destination=nil,nil,nil
local needsNavigation=false
local function finite(v)return type(v)=='number'and v==v and math.abs(v)<10000000 end
local function integer(v)return finite(v)and v>=0 and v==math.floor(v)end
local function plain(p)return{x=p.x,y=p.y,z=p.z}end
local function vector(p)return util.vector3(p.x,p.y,p.z)end
local function horizontal(a,b)return util.vector2(a.x-b.x,a.y-b.y):length()end
local function metaValid(m)
    return type(m)=='table'and m.schema==C.saveSchema and m.boundEntrySha256==C.boundEntrySha256
        and roleConfig[m.role]~=nil and type(m.actorId)=='string'and type(m.recordId)=='string'
end
local function owned()
    return metaValid(state.meta)and self:isValid()and types.NPC.objectIsInstance(self)
        and self.contentFile==nil and self.id==state.meta.actorId and self.recordId==state.meta.recordId
end
local function report(kind)
    if not owned()then return end
    core.sendGlobalEvent('VEYRA_TownReport',{actor=self.object,role=state.meta.role,
        seq=(kind~='READY'and state.goal)and state.goal.seq or nil,kind=kind,
        measuredDistance=state.totalMeasuredDistance,windowDistance=state.windowDistance,
        remainingDistance=destination and (self.position-destination):length()or nil,
        observationContinuity=state.observationContinuity})
end
local function phase(kind)
    if kind=='STALLED'or kind=='POSITION_JUMP_HOLD'then state.terminalHold=kind end
    if state.phase~=kind then state.phase=kind;report(kind)end
end
local function snapshot()
    return {version=C.version,phase=state.phase,enabled=state.enabled,awaitAuthority=state.awaitAuthority,
        actorId=state.meta and state.meta.actorId,role=state.meta and state.meta.role,
        seq=state.goal and state.goal.seq,place=state.goal and state.goal.place,
        replans=state.replans,totalMeasuredDistance=state.totalMeasuredDistance,
        windowDistance=state.windowDistance,observationContinuity=state.observationContinuity,
        destination=destination and plain(destination)or nil}
end
local function resetWindow(gap)
    previous,windowOrigin,destination=nil,nil,nil
    state.windowDistance=0;lastSample,lastProgress,lastNavTry=-100,-100,-100
    if gap then state.observationContinuity=gap end
end
local function stopOwnTravel()
    if active and owned()then I.AI.removePackages('Travel')end
end
local function enabled(data)
    if type(data)~='table'or type(data.enabled)~='boolean'or state.phase=='LOAD_HOLD'then return end
    state.enabled=data.enabled
    if not state.enabled then
        stopOwnTravel();needsNavigation=false;state.awaitAuthority=true;phase('WAIT_OWNER')
    end
end
local function goal(data)
    if type(data)~='table'or not integer(data.seq)or data.seq<1 or not C.locations[data.place]
        or state.phase=='LOAD_HOLD'or not owned()or not state.enabled then return end
    local expected=C.locations[data.place]
    if type(data.position)~='table'or data.position.x~=expected.x or data.position.y~=expected.y
        or data.position.z~=expected.z then return end
    local old=state.goal
    if old and data.seq<old.seq then return end
    if old and data.seq==old.seq then
        if data.place~=old.place then return end
        state.awaitAuthority=false
        if state.terminalHold then phase(state.terminalHold);return end
        if state.phase=='STALLED'or state.phase=='POSITION_JUMP_HOLD'
            or state.phase=='ARRIVED_OBSERVED'or state.phase=='AT_DESTINATION_POSITION_ONLY'then return end
        needsNavigation=true;return
    end
    stopOwnTravel()
    state.goal={seq=data.seq,place=data.place};state.replans=0;state.terminalHold=nil
    state.totalMeasuredDistance=0;state.awaitAuthority=false;needsNavigation=true
    resetWindow('NEW_GOAL_WINDOW');phase('NAV_REQUEST_PENDING')
end
local function inCombat()
    local package=I.AI.getActivePackage()
    return I.AI.isFleeing()or package and(package.type=='Combat'or package.type=='Pursue')
end
local function navigate(now)
    if now-lastNavTry<C.activationRetrySeconds then return end;lastNavTry=now
    local p=C.locations[state.goal.place]
    local flags=nearby.NAVIGATOR_FLAGS.Walk+nearby.NAVIGATOR_FLAGS.OpenDoor
    local bounds=types.Actor.getPathfindingAgentBounds(self)
    local projected=nearby.findNearestNavMeshPosition(vector(p),{agentBounds=bounds,includeFlags=flags,
        searchAreaHalfExtents=util.vector3(160,160,240)})
    if not projected then phase('WAIT_NAV');return end
    local status,path=nearby.findPath(self.position,projected,{agentBounds=bounds,
        includeFlags=flags,destinationTolerance=60})
    if status~=nearby.FIND_PATH_STATUS.Success then phase('WAIT_NAV');return end
    destination=projected
    if (self.position-destination):length()<=C.arrivalTolerance then
        needsNavigation=false;phase('AT_DESTINATION_POSITION_ONLY');return
    end
    -- The native interface accepts Travel.destPosition, not an invented target.
    I.AI.startPackage({type='Travel',destPosition=destination,isRepeat=false,cancelOther=true})
    previous=self.position;windowOrigin=self.position;state.windowDistance=0
    lastSample=now;lastProgress=now
    needsNavigation=false;phase('TRAVEL_STARTED')
    local points=0;for _ in ipairs(path)do points=points+1 end
    print('VEYRA_TOWN|kind=TRAVEL_STARTED|role='..state.meta.role..'|seq='..state.goal.seq
        ..'|pathPoints='..points..'|arrivalObserved=false')
end
local function sample(now)
    if now-lastSample<C.sampleSeconds then return end;lastSample=now
    local current=self.position
    local step=(current-previous):length()
    if step>C.maximumSampleJump then
        stopOwnTravel();state.observationContinuity='POSITION_JUMP_GAP'
        phase('POSITION_JUMP_HOLD');return
    end
    local distance=horizontal(current,previous)
    state.totalMeasuredDistance=state.totalMeasuredDistance+distance
    state.windowDistance=state.windowDistance+distance;previous=current
    if distance>=2 then lastProgress=now end
    local remaining=(current-destination):length()
    if remaining<=C.arrivalTolerance then
        stopOwnTravel()
        if state.windowDistance>=C.minimumObservedMovement
            and horizontal(current,windowOrigin)>=C.minimumObservedMovement then
            phase('ARRIVED_OBSERVED')
        else phase('AT_DESTINATION_POSITION_ONLY')end
    elseif now-lastProgress>=C.stallSeconds then
        stopOwnTravel()
        if state.replans>=C.maximumReplans then phase('STALLED')
        else
            state.replans=state.replans+1;needsNavigation=true
            phase('REPLAN_PENDING')
        end
    else report('TRAVEL_PROGRESS')end
end
local function update()
    if not active or not self:isActive()or state.phase=='LOAD_HOLD'then return end
    if not owned()then state.phase='IDENTITY_HOLD';return end
    if core.isWorldPaused()then return end
    if types.Actor.isDead(self)then needsNavigation=false;phase('DEAD_HOLD');return end
    if not state.enabled or state.awaitAuthority or not state.goal then return end
    local now=core.getSimulationTime()
    if inCombat()then
        -- Preserve Combat/Pursue/flee packages. No movement or journey sampling
        -- is attributed to the daily route during this observation gap.
        resetWindow('COMBAT_OBSERVATION_GAP');needsNavigation=true
        phase('COMBAT_DEFERRED');return
    end
    if state.phase=='STALLED'or state.phase=='POSITION_JUMP_HOLD'
        or state.phase=='ARRIVED_OBSERVED'or state.phase=='AT_DESTINATION_POSITION_ONLY'then return end
    if needsNavigation then navigate(now)
    elseif destination and previous then sample(now)end
end
local function activation()
    active=true
    if state.phase=='LOAD_HOLD'then return end
    if not owned()then state.phase='IDENTITY_HOLD';return end
    stopOwnTravel();state.awaitAuthority=true;needsNavigation=false
    if state.observationContinuity~='SAVE_RELOAD_GAP'then resetWindow('CELL_ACTIVATION_GAP')end
    phase('WAIT_AUTHORITY');report('READY')
end
local function inactive()
    active=false;state.awaitAuthority=true;needsNavigation=false
    resetWindow('CELL_UNLOAD_GAP');state.phase='WAIT_ACTIVE';report('INACTIVE')
end
local function load(data)
    active=false;needsNavigation=false;resetWindow('SAVE_RELOAD_GAP')
    if type(data)~='table'or data.schema~=C.saveSchema or data.phase=='LOAD_HOLD'
        or not metaValid(data.meta)or type(data.enabled)~='boolean'
        or not integer(data.replans)or data.replans>C.maximumReplans
        or(data.terminalHold~=nil and data.terminalHold~='STALLED'and data.terminalHold~='POSITION_JUMP_HOLD')
        or not finite(data.totalMeasuredDistance)or data.totalMeasuredDistance<0 then
        state={schema=C.saveSchema,enabled=false,phase='LOAD_HOLD',awaitAuthority=true,
            replans=0,totalMeasuredDistance=0,windowDistance=0,observationContinuity='SAVE_RELOAD_GAP'}
        return
    end
    if data.goal and(type(data.goal)~='table'or not integer(data.goal.seq)or data.goal.seq<1
        or not C.locations[data.goal.place])then
        state={schema=C.saveSchema,enabled=false,phase='LOAD_HOLD',awaitAuthority=true,
            replans=0,totalMeasuredDistance=0,windowDistance=0,observationContinuity='SAVE_RELOAD_GAP'}
        return
    end
    state={schema=C.saveSchema,meta=data.meta,enabled=data.enabled,goal=data.goal,
        replans=data.replans,totalMeasuredDistance=data.totalMeasuredDistance,windowDistance=0,
        terminalHold=data.terminalHold,
        phase='WAIT_ACTIVE',awaitAuthority=true,observationContinuity='SAVE_RELOAD_GAP'}
end
local function init(data)
    if not metaValid(data)then state.phase='LOAD_HOLD';return end
    state.meta={schema=data.schema,boundEntrySha256=data.boundEntrySha256,
        role=data.role,actorId=data.actorId,recordId=data.recordId}
    state.phase='WAIT_ACTIVE'
end
local function save()
    return {schema=C.saveSchema,meta=state.meta,enabled=state.enabled,goal=state.goal,
        replans=state.replans,totalMeasuredDistance=state.totalMeasuredDistance,phase=state.phase,
        terminalHold=state.terminalHold}
end
return {interfaceName='VeyraTownResident',interface={version=1,getState=snapshot},
    engineHandlers={onInit=init,onActive=activation,onInactive=inactive,onUpdate=update,
        onSave=save,onLoad=load},
    eventHandlers={VEYRA_TownPing=function()if active and owned()then report('READY')end end,
        VEYRA_TownEnabled=enabled,VEYRA_TownGoal=goal}}
