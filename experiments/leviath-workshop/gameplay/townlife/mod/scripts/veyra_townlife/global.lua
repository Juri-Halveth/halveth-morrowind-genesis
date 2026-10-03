-- SPDX-License-Identifier: MIT
-- Own generated actors only; candidate native integration NOT_RUN.
local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')
local C=require('scripts.veyra_townlife.config')
local localScript='scripts/veyra_townlife/actor.lua'
local state={schema=C.saveSchema,enabled=true,created=false,phase='WAIT_ENTRY',roles={}}
local player,lastTick,lastEntryRequest=nil,-100,-100
local roleConfig={};for _,r in ipairs(C.roles)do roleConfig[r.id]=r end
local function log(kind,detail) print('VEYRA_TOWN|kind='..kind..'|'..(detail or '')) end
local function valid(o)
    local ok,value=pcall(function()return o and o:isValid()end)
    return ok and value==true
end
local function own(o,row)
    return valid(o) and types.NPC.objectIsInstance(o) and o.contentFile==nil
        and o.id==row.actorId and o.recordId==row.recordId
end
local function active(row)
    for _,o in ipairs(world.activeActors)do if own(o,row)then return o end end
end
local function finite(v) return type(v)=='number' and v==v and math.abs(v)<10000000 end
local function vector(p) return util.vector3(p.x,p.y,p.z) end
local function pointValid(point,wanted)
    return type(point)=='table' and finite(point.x) and finite(point.y) and finite(point.z)
        and math.abs(point.x-wanted.x)<=180 and math.abs(point.y-wanted.y)<=180
        and math.abs(point.z-wanted.z)<=256
end
local function getPlayer()
    if valid(player)then return player end
    player=world.players[1];return player
end
local function inEntry(o)
    return valid(o) and o.cell and o.cell.isExterior and o.cell.name==C.entry.name
        and (o.position-util.vector3(C.entry.x,C.entry.y,o.position.z)):length()<=C.entry.radius
end
local function schedule(role)
    local hour=(world.getGameTime()%86400)/3600
    local result=role.schedule[1]
    for _,step in ipairs(role.schedule)do if hour>=step.at then result=step end end
    local ending=24
    for _,step in ipairs(role.schedule)do if step.at>result.at then ending=step.at;break end end
    return result.place,result.at,ending
end
local noServices={Spells=false,Spellmaking=false,Enchanting=false,Training=false,
    Repair=false,Barter=false,Weapon=false,Armor=false,Clothing=false,Books=false,
    Ingredients=false,Picks=false,Probes=false,Lights=false,Apparatus=false,
    RepairItems=false,Misc=false,Potions=false,MagicItems=false,Travel=false}
local function createResidents(data)
    if type(data)~='table'then return end
    if state.created or not state.enabled or state.phase=='LOAD_HOLD' then return end
    local p=getPlayer()
    if not valid(data.player) or not valid(p) or data.player.id~=p.id or not inEntry(p) then return end
    local templates={}
    for _,r in ipairs(C.roles)do
        local point=data.positions and data.positions[r.id]
        if not pointValid(point,C.locations[r.home])then return end
        templates[r.id]=types.NPC.records[r.template]
        if not templates[r.id]then state.phase='TEMPLATE_HOLD';log('TEMPLATE_HOLD','role='..r.id);return end
    end
    local created={}
    local ok,fault=pcall(function()
        for _,r in ipairs(C.roles)do
            local template=templates[r.id]
            local rec=world.createRecord(types.NPC.createRecordDraft({template=template,name=r.name,
                mwscript='',isMale=template.isMale,isAutocalc=true,isEssential=false,isRespawning=false,
                baseDisposition=90,baseGold=0,servicesOffered=noServices,travelDestinations={}}))
            local actor=world.createObject(rec.id)
            local row={role=r.id,actorId=actor.id,recordId=actor.recordId,actor=actor,
                       seq=0,ready=false,phase='WAIT_ACTIVE',lastPing=-100,goal=nil}
            state.roles[r.id]=row;created[#created+1]=row
            actor:addScript(localScript,{schema=C.saveSchema,boundEntrySha256=C.boundEntrySha256,
                role=r.id,actorId=row.actorId,recordId=row.recordId})
            actor:teleport(p.cell,vector(data.positions[r.id]),{onGround=true})
        end
    end)
    if not ok then
        for _,row in ipairs(created)do if own(row.actor,row)then pcall(row.actor.remove,row.actor)end end
        state.phase='CREATE_HOLD';state.enabled=false;log('CREATE_HOLD','detail='..tostring(fault));return
    end
    state.created=true;state.phase='RESIDENTS_CREATED'
    log('CREATED','roles=3|entrySource='..C.boundEntrySha256..'|playerTeleport=false')
end
local function report(data)
    if type(data)~='table'then return end
    local row=state.roles[data.role]
    if not row or not own(data.actor,row)then return end
    if data.seq and (type(data.seq)~='number' or data.seq~=row.seq)then return end
    if data.kind=='READY' then row.ready=true;row.lastIssued=nil;row.lastEnabled=nil
    elseif data.kind=='INACTIVE' then row.ready=false;row.phase='WAIT_ACTIVE';row.lastIssued=nil
    else
        row.phase=data.kind;row.lastReport=world.getSimulationTime()
        row.measuredDistance=data.measuredDistance;row.remainingDistance=data.remainingDistance
        row.observationContinuity=data.observationContinuity
        if data.kind=='ARRIVED_OBSERVED' then
            log('ARRIVED_OBSERVED','role='..row.role..'|goal='..tostring(row.goal)
                ..'|sampledDistance='..tostring(data.measuredDistance)..'|remaining='..tostring(data.remainingDistance))
        end
    end
end
local function snapshot()
    local time=world.getGameTime()
    local result={version=C.version,schema=C.saveSchema,enabled=state.enabled,created=state.created,
                  phase=state.phase,roles={},lastReadAtGameTime=time,
                  gameDayIndex=math.floor(time/86400),gameHour=math.floor(time/3600)%24,
                  gameMinute=math.floor(time/60)%60}
    for id,row in pairs(state.roles)do
        local role=roleConfig[id]
        local scheduled,from,to=schedule(role)
        result.roles[id]={actorId=row.actorId,recordId=row.recordId,phase=row.phase,goal=row.goal,
            seq=row.seq,measuredDistance=row.measuredDistance,remainingDistance=row.remainingDistance,
            observationContinuity=row.observationContinuity,roleName=role.name,
            daySlot=string.format('%02d:00-%02d:00',from,to),scheduledPlace=scheduled}
    end
    return result
end
local function setEnabled(value)
    if type(value)~='boolean'then error('Townlife enabled must be boolean')end
    state.enabled=value
    for _,row in pairs(state.roles)do
        local actor=active(row)
        if actor then actor:sendEvent('VEYRA_TownEnabled',{enabled=value})end
        row.lastIssued=nil
    end
end
local function update()
    if state.phase=='LOAD_HOLD' or world.isWorldPaused()then return end
    local now=world.getSimulationTime()
    if now-lastTick<C.sampleSeconds then return end;lastTick=now
    local p=getPlayer()
    if not state.created then
        if state.enabled and valid(p) and inEntry(p) and now-lastEntryRequest>C.activationRetrySeconds then
            lastEntryRequest=now;p:sendEvent('VEYRA_TownPreflight',{})
        end
        return
    end
    for _,r in ipairs(C.roles)do
        local row=state.roles[r.id]
        local actor=active(row)
        if not actor then row.phase='WAIT_ACTIVE';row.ready=false;row.lastIssued=nil;row.lastEnabled=nil
        elseif not actor.enabled then row.phase='WAIT_DISABLED';row.ready=false;row.lastIssued=nil
        elseif types.Actor.isDead(actor)then row.phase='DEAD_HOLD';row.lastIssued=nil
        elseif not row.ready then
            if now-row.lastPing>=C.activationRetrySeconds then
                row.lastPing=now;actor:sendEvent('VEYRA_TownPing',{})
            end
        else
            if row.lastEnabled~=state.enabled then
                actor:sendEvent('VEYRA_TownEnabled',{enabled=state.enabled})
                row.lastEnabled=state.enabled
            end
            local goal=schedule(r)
            if not state.enabled then row.phase='WAIT_OWNER'
            elseif row.goal~=goal or not row.lastIssued then
                if row.goal~=goal then row.seq=row.seq+1 end
                row.goal=goal;row.lastIssued=now;row.phase='TRAVEL_REQUESTED'
                actor:sendEvent('VEYRA_TownGoal',{seq=row.seq,place=goal,position=C.locations[goal]})
                log('TRAVEL_REQUESTED','role='..r.id..'|seq='..row.seq..'|place='..goal)
            end
        end
    end
end
local function load(data)
    lastTick,lastEntryRequest,player=-100,-100,nil
    if not data then state={schema=C.saveSchema,enabled=true,created=false,phase='WAIT_ENTRY',roles={}};return end
    if type(data)~='table' or data.phase=='LOAD_HOLD' or data.schema~=C.saveSchema or data.boundEntrySha256~=C.boundEntrySha256
        or type(data.enabled)~='boolean' or type(data.created)~='boolean' or type(data.roles)~='table'then
        state={schema=C.saveSchema,enabled=false,created=false,phase='LOAD_HOLD',roles={}};log('LOAD_HOLD');return
    end
    if data.created then
        local seen={}
        for id in pairs(data.roles)do if not roleConfig[id]then
            state={schema=C.saveSchema,enabled=false,created=false,phase='LOAD_HOLD',roles={}};return
        end end
        for _,r in ipairs(C.roles)do
            local row=data.roles[r.id]
            if type(row)~='table' or row.role~=r.id or type(row.actorId)~='string'
                or type(row.recordId)~='string' or seen[row.actorId] or not finite(row.seq)
                or row.seq<0 or row.seq~=math.floor(row.seq) then
                state={schema=C.saveSchema,enabled=false,created=false,phase='LOAD_HOLD',roles={}};return
            end
            if row.goal~=nil and not C.locations[row.goal]then
                state={schema=C.saveSchema,enabled=false,created=false,phase='LOAD_HOLD',roles={}};return
            end
            seen[row.actorId]=true;row.ready=false;row.lastPing=-100;row.lastIssued=nil
            row.lastEnabled=nil;row.phase='WAIT_ACTIVE'
        end
    end
    state=data;state.phase=data.created and 'RESUME_WAIT_ACTIVE' or 'WAIT_ENTRY'
end
local function save()
    local data={schema=C.saveSchema,boundEntrySha256=C.boundEntrySha256,
        enabled=state.enabled,created=state.created,phase=state.phase,roles={}}
    for id,row in pairs(state.roles)do
        data.roles[id]={role=row.role,actorId=row.actorId,recordId=row.recordId,
            seq=row.seq,goal=row.goal,phase=row.phase}
    end
    return data
end
return {interfaceName='VeyraTownlife',interface={version=1,getState=snapshot,setEnabled=setEnabled},
    engineHandlers={onUpdate=update,onPlayerAdded=function(p)player=p end,onLoad=load,
        onSave=save},
    eventHandlers={VEYRA_TownCreate=createResidents,VEYRA_TownReport=report,
        VEYRA_TownStatusRequest=function(data)
            local p=getPlayer()
            if type(data)=='table'and valid(data.player)and valid(p)and data.player.id==p.id then
                p:sendEvent('VEYRA_TownStatus',snapshot())
            end
        end}}
