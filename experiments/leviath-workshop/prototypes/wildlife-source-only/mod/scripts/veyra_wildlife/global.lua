-- SPDX-License-Identifier: MIT
-- Optional single owned creature. No original actor mutation or replacement.
local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')
local C=require('scripts.veyra_wildlife.config')
local state={schema=C.schema,enabled=C.defaultEnabled,phase='DISABLED',created=false}
local player,lastPing=nil,-100
local function own(o)
    return o and o:isValid() and types.Creature.objectIsInstance(o)
        and o.contentFile==nil and o.id==state.actorId and o.recordId==state.recordId
end
local function snapshot()
    return {version=C.version,schema=C.schema,enabled=state.enabled,phase=state.phase,
        created=state.created,actorId=state.actorId,recordId=state.recordId,
        actor=state.actor,localPhase=state.localPhase,measuredDistance=state.measuredDistance,
        ready=state.ready,goalIssued=state.goalIssued}
end
local function actorActive()
    for _,actor in ipairs(world.activeActors)do if own(actor)then return true end end
    return false
end
local function enabled(value)
    assert(type(value)=='boolean','enabled must be a boolean')
    if state.phase=='LOAD_HOLD'or state.phase=='CREATE_HOLD'then return false end
    state.enabled=value
    if own(state.actor)then state.actor:sendEvent('VEYRA_WildEnabled',{enabled=value})end
    if not value then state.phase='DISABLED' else state.phase=state.created and 'WAIT_ACTIVE'or 'WAIT_FRONTIER' end
    return true
end
local function update()
    if not state.enabled or not player or not player:isValid() then return end
    if not state.created then
        local p=player.position
        if not player.cell or not player.cell.isExterior or player.cell.gridX<65 or player.cell.gridX>66
            or player.cell.gridY< -63 or player.cell.gridY> -62
            or(util.vector2(p.x-C.spawn.x,p.y-C.spawn.y)):length()>3000 then return end
        local ok,fault=pcall(function()
            local template=types.Creature.records['mudcrab'];assert(template,'bound template missing')
            local rec=world.createRecord(types.Creature.createRecordDraft({template=template,
                name='LEVIATH Felsenhirsch',model=C.model,mwscript='',canWalk=true,canSwim=false,
                canFly=false,isBiped=false,isEssential=false,isRespawning=false,baseGold=0}))
            local actor=world.createObject(rec.id)
            state.actor=actor;state.actorId=actor.id;state.recordId=actor.recordId
            -- Allocation itself commits the single-instance slot. A later
            -- attachment/teleport failure remains held, including after reload.
            state.created=true
            actor:addScript('scripts/veyra_wildlife/actor.lua',{schema=C.schema,
                actorId=actor.id,recordId=actor.recordId,frontierSha256=C.frontierSha256})
            actor:teleport(world.getExteriorCell(65,-62),util.vector3(C.spawn.x,C.spawn.y,C.spawn.z),{onGround=true})
        end)
        if not ok then state.phase='CREATE_HOLD';state.enabled=false;print('VEYRA_WILDLIFE|CREATE_HOLD|'..tostring(fault));return end
        state.created=true;state.phase='WAIT_ACTIVE'
    end
    if not own(state.actor)then state.phase='MISSING_HOLD';state.enabled=false;return end
    if types.Actor.isDead(state.actor)then state.phase='DEAD_HOLD';return end
    if not actorActive()then state.ready=false;state.goalIssued=false;state.phase='WAIT_ACTIVE';return end
    local now=world.getSimulationTime()
    if not state.ready and now-lastPing>1 then state.actor:sendEvent('VEYRA_WildPing',{});lastPing=now end
    if state.ready and not state.goalIssued then
        state.actor:sendEvent('VEYRA_WildEnabled',{enabled=true})
        state.actor:sendEvent('VEYRA_WildGoal',C.target)
        state.goalIssued=true;state.phase='GOAL_REQUESTED'
    end
end
local function load(data)
    if type(data)~='table'or data.schema~=C.schema or type(data.created)~='boolean'
        or data.phase=='LOAD_HOLD'or data.phase=='CREATE_HOLD'
        or(data.created and(type(data.actorId)~='string'or type(data.recordId)~='string'))then
        state={schema=C.schema,enabled=false,phase='LOAD_HOLD',created=false};return
    end
    state={schema=C.schema,enabled=false,phase='DISABLED',created=data.created,
        actor=data.actor,actorId=data.actorId,recordId=data.recordId,ready=false,goalIssued=false}
end
return {interfaceName='VeyraWildlife',interface={version=1,setEnabled=enabled,getState=snapshot},
 engineHandlers={onPlayerAdded=function(p)player=p end,onUpdate=update,onSave=function()return state end,onLoad=load},
 eventHandlers={VEYRA_WildReport=function(data)
    if type(data)~='table'or not own(data.actor)then return end
    if data.phase=='READY'then state.ready=true;state.goalIssued=false end
    state.localPhase=data.phase;state.measuredDistance=data.distance
 end}}
