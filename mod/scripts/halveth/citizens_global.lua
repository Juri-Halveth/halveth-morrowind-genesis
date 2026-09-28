-- Opt-in citizens created by HALVETH. Original Morrowind actors and AI are never changed.
local core = require('openmw.core')
local world = require('openmw.world')
local types = require('openmw.types')
local util = require('openmw.util')

local SPEC = {
    {name='Liora vom Morgenweg', template='eldafire', offset=util.vector3(120, 0, 0),
        line='Manchmal fuehrt der schoenste Weg einfach weiter als geplant.'},
    {name='Tarin am Regenpfad', template='fargoth', offset=util.vector3(210, 0, 0),
        line='Wenn du etwas wissen willst, frag mich. Ich bleibe nicht immer hier.'},
}
local MAX_RETIRED = 128
local citizens, retired, pending, invalidSave, warmups = {}, {}, nil, nil, {}
local lastMomentAt, lastMomentIndex = -100000, 0
local lastScanAt = -100
local noServices = {Spells=false,Spellmaking=false,Enchanting=false,
    Training=false,Repair=false,Barter=false,Weapon=false,Armor=false,
    Clothing=false,Books=false,Ingredients=false,Picks=false,Probes=false,
    Lights=false,Apparatus=false,RepairItems=false,Misc=false,
    Potions=false,MagicItems=false,Travel=false}

local function validEntry(entry)
    if type(entry) ~= 'table' or type(entry.actorId) ~= 'string'
        or type(entry.recordId) ~= 'string' or type(entry.name) ~= 'string' then return false end
    if not entry.actorId:match('^@0x[%da-fA-F]+$')
        or not entry.recordId:lower():match('^generated:') then return false end
    for _,spec in ipairs(SPEC) do if entry.name == spec.name then return true end end
    return false
end

local function loadedMap()
    local map = {}
    for _,actor in ipairs(world.activeActors) do map[actor.id] = actor end
    return map
end

local function ownActor(actor, entry)
    return actor and actor:isValid() and actor.id == entry.actorId
        and actor.recordId == entry.recordId and actor.contentFile == nil
        and types.NPC.objectIsInstance(actor)
end

local function startWander(actor)
    actor:sendEvent('StartAIPackage',{type='Wander',distance=220,
        duration=3600,
        idle={idle2=0,idle3=0,idle4=0,idle5=0,idle6=0,
            idle7=0,idle8=0,idle9=0},isRepeat=true})
end

local function report(player, requestId, success, message)
    if not player or not player:isValid() then return end
    local map, people = loadedMap(), {}
    for _,entry in ipairs(citizens) do
        local actor = map[entry.actorId]
        local position = ownActor(actor, entry) and actor.position or nil
        people[#people+1] = {actorId=entry.actorId, recordId=entry.recordId,
            name=entry.name, loaded=position ~= nil,
            position=position and {x=position.x,y=position.y,z=position.z} or nil}
    end
    player:sendEvent('HALVETH_CitizensResult', {requestId=requestId,
        success=success, message=message, people=people,
        retiredCount=#retired, pending=pending ~= nil})
end

local function request(data)
    if type(data) ~= 'table' then return end
    local player, requestId, command = data.player, data.requestId, data.command
    if not player or not player:isValid() or not types.Player.objectIsInstance(player)
        or type(requestId) ~= 'string' or #requestId > 96 then return end
    if invalidSave then
        report(player,requestId,false,'Buerger-Zustand im Spielstand ist ungueltig; unveraendert bewahrt.')
        return
    end
    if command == 'status' then
        local message = pending and 'Zwei eigene Buerger betreten die geladene Welt.'
            or #citizens > 0 and 'Eigene Buerger sind in diesem Spielstand aktiv.'
            or #retired > 0 and 'Eigene Buerger zur Entfernung vorgemerkt.'
            or 'Noch keine eigenen Buerger gerufen.'
        report(player,requestId,true,message)
        return
    end
    if command == 'spawn' then
        if #citizens > 0 or pending then
            report(player,requestId,false,'Eigene Buerger sind bereits aktiv.')
            return
        end
        if #retired > MAX_RETIRED-#SPEC then
            report(player,requestId,false,'Entfernungsvormerkung ist voll; alte Zellen zuerst laden.')
            return
        end
        if not player.cell or not player.cell.isExterior then
            report(player,requestId,false,'Eigene Buerger koennen nur draussen gerufen werden.')
            return
        end
        local created, entries = {}, {}
        local ok, err = pcall(function()
            for _,spec in ipairs(SPEC) do
                local template = assert(types.NPC.records[spec.template], 'Vorlage fehlt: '..spec.template)
                for service,offered in pairs(template.servicesOffered) do
                    assert(not offered,'Vorlage bietet unerwarteten Dienst: '..service)
                end
                local record = world.createRecord(types.NPC.createRecordDraft({
                    template=template, name=spec.name,
                    isMale=template.isMale, isAutocalc=true, isEssential=true,
                    isRespawning=false, baseDisposition=75, baseGold=0,
                    mwscript='', servicesOffered=noServices, travelDestinations={},
                }))
                local actor = world.createObject(record.id)
                created[#created+1] = actor
                actor:teleport(player.cell, player.position+spec.offset)
                entries[#entries+1] = {actorId=actor.id,recordId=actor.recordId,name=spec.name}
            end
        end)
        if not ok then
            -- Never leave a partly created group in the world.
            for _,actor in ipairs(created) do if actor:isValid() then pcall(actor.remove,actor) end end
            report(player,requestId,false,'Eigene Buerger konnten nicht vollstaendig erscheinen: '..tostring(err))
            return
        end
        citizens = entries
        pending = {player=player,requestId=requestId,frames=0,mode='warmup'}
        lastMomentAt = core.getRealTime()
        return
    end
    if command == 'dismiss' then
        if #citizens == 0 then
            report(player,requestId,false,'Keine aktiven eigenen Buerger vorhanden.')
            return
        end
        if #retired + #citizens > MAX_RETIRED then
            report(player,requestId,false,'Entfernungsvormerkung ist voll; alte Zellen zuerst laden.')
            return
        end
        -- Queue exact generated instance IDs first. The next update removes loaded
        -- instances; unloaded instances are removed when their cell is visited.
        for _,entry in ipairs(citizens) do retired[#retired+1] = entry end
        citizens, pending, warmups = {}, nil, {}
        report(player,requestId,true,'Eigene Buerger entfernt oder fuer ihre Zelle vorgemerkt.')
        return
    end
    report(player,requestId,false,'Unbekannte Buerger-Aktion.')
end

local function update(dt)
    if invalidSave then return end
    if #citizens==0 and #retired==0 and not pending then return end
    for _,warmup in pairs(warmups) do
        warmup.elapsed=warmup.elapsed+(dt or 0)
    end
    local now=core.getRealTime()
    if not pending and now-lastScanAt<0.5 then return end
    lastScanAt=now
    local map = loadedMap()
    for i=#retired,1,-1 do
        local entry, actor = retired[i], map[retired[i].actorId]
        if ownActor(actor,entry) then
            local ok = pcall(actor.remove,actor)
            if ok then table.remove(retired,i) end
        end
    end
    if pending then
        pending.frames = pending.frames + 1
        if pending.frames >= 5 then
            local started = 0
            for _,entry in ipairs(citizens) do
                local actor = map[entry.actorId]
                if ownActor(actor,entry) then
                    if pending.mode=='warmup' then
                        -- A short native path gives each new citizen a visible
                        -- first step before the less predictable Wander AI.
                        warmups[entry.actorId]={origin=actor.position,elapsed=0}
                        actor:sendEvent('StartAIPackage',{type='Travel',
                            destPosition=actor.position+util.vector3(90,0,0),
                            isRepeat=false})
                    else startWander(actor) end
                    started = started + 1
                end
            end
            if pending.player then
                report(pending.player,pending.requestId,started == #SPEC,
                    started == #SPEC and 'Zwei eigene Buerger bewegen sich mit OpenMW-AI.'
                        or 'Ein eigener Buerger ist noch nicht in der geladenen Welt.')
            end
            pending = nil
        end
    end
    if #citizens == 0 or world.isWorldPaused() then return end
    for _,entry in ipairs(citizens) do
        local warmup,actor=warmups[entry.actorId],map[entry.actorId]
        if warmup and ownActor(actor,entry) then
            local traveled=(actor.position-warmup.origin):length()
            if traveled>=30 or warmup.elapsed>=18 then
                startWander(actor)
                warmups[entry.actorId]=nil
            end
        end
    end
    if now-lastMomentAt < 90 then return end
    local player = world.players[1]
    if not player or not player:isValid() or not player.cell or not player.cell.isExterior then return end
    for step=1,#citizens do
        local i = (lastMomentIndex+step-1)%#citizens+1
        local entry, actor = citizens[i], map[citizens[i].actorId]
        if ownActor(actor,entry) and actor.cell == player.cell
            and (actor.position-player.position):length() < 700 then
            player:sendEvent('HALVETH_CitizensMoment',{
                actorId=entry.actorId,name=entry.name,line=SPEC[i].line})
            lastMomentIndex,lastMomentAt=i,now
            break
        end
    end
end

local function save()
    return invalidSave or {version=1,citizens=citizens,retired=retired}
end

local function load(data)
    citizens,retired,pending,invalidSave,warmups={}, {}, nil, nil, {}
    lastScanAt=-100
    lastMomentIndex,lastMomentAt=0,core.getRealTime()
    if data == nil then return end
    if type(data)~='table' or data.version~=1 or type(data.citizens)~='table'
        or type(data.retired)~='table' or #data.citizens>#SPEC
        or #data.retired>MAX_RETIRED then invalidSave=data;return end
    local seen={}
    for i,entry in ipairs(data.citizens) do
        if not validEntry(entry) or entry.name~=SPEC[i].name then invalidSave=data;return end
    end
    for _,list in ipairs({data.citizens,data.retired}) do
        for _,entry in ipairs(list) do
            if not validEntry(entry) or seen[entry.actorId] then invalidSave=data;return end
            seen[entry.actorId]=true
        end
    end
    citizens,retired=data.citizens,data.retired
    if #citizens>0 then pending={frames=0,mode='wander'} end
end

return {engineHandlers={onUpdate=update,onSave=save,onLoad=load,
    onNewGame=function()
        citizens,retired,pending,invalidSave,warmups={}, {}, nil, nil, {}
        lastMomentIndex,lastMomentAt,lastScanAt=0,core.getRealTime(),-100
    end},
    eventHandlers={HALVETH_CitizensRequest=request}}
