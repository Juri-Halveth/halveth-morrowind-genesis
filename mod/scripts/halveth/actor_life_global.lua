-- Opt-in ambient NPC. Only the record and instance created here may be controlled.
local core=require('openmw.core')
local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')

local actorId,recordId,pending,actorRef=nil,nil,nil,nil
local function resolve()
    if not actorId or not recordId then return nil end
    local actor=actorRef
    if actor and actor:isValid() and actor.id==actorId and actor.recordId==recordId
        and types.NPC.objectIsInstance(actor) and actor.contentFile==nil then return actor end
    actorRef=nil
    -- Dynamically generated actor IDs have @... form, not content FormIds.
    for _,candidate in ipairs(world.activeActors) do
        if candidate.id==actorId and candidate.recordId==recordId
            and candidate.contentFile==nil and types.NPC.objectIsInstance(candidate) then
            actorRef=candidate;return candidate
        end
    end
end
local function report(player,requestId,ok,message)
    if not player or not player:isValid() then return end
    local actor=resolve()
    local position=actor and actor.position
    player:sendEvent('HALVETH_AmbientResult',{requestId=requestId,success=ok,message=message,
        actorId=actorId,recordId=recordId,loaded=actor~=nil,
        position=position and {x=position.x,y=position.y,z=position.z} or nil})
end
local function request(data)
    if type(data)~='table' then return end
    local player=data.player
    if not player or not player:isValid() or not types.Player.objectIsInstance(player)
        or type(data.requestId)~='string' or #data.requestId>96 then return end
    local command=data.command
    local actor=resolve()
    if command=='status' then
        report(player,data.requestId,true,actor and 'Wanderer in der geladenen Welt.'
            or actorId and 'Wanderer derzeit ausserhalb der geladenen Welt.' or 'Noch kein Wanderer gerufen.')
        return
    end
    if command=='spawn' then
        if actorId then report(player,data.requestId,false,'Es ist bereits ein HALVETH-Wanderer in diesem Spielstand registriert.');return end
        if not player.cell or not player.cell.isExterior then
            report(player,data.requestId,false,'Der Wanderer wird fuer diesen Prototyp nur draussen gerufen.');return
        end
        local ok,result=pcall(function()
            local template=assert(types.NPC.records['arrille'],'Morrowind-NPC-Vorlage fehlt')
            local record=world.createRecord(types.NPC.createRecordDraft({
                name='HALVETH Wanderer',race=template.race,class=template.class,
                head=template.head,hair=template.hair,model=template.model,
                isMale=template.isMale,isAutocalc=true,isEssential=true,
                isRespawning=false,baseDisposition=75,baseGold=0,mwscript='',
                servicesOffered={},travelDestinations={},
            }))
            local created=world.createObject(record.id)
            created:teleport(player.cell,player.position+util.vector3(320,0,0))
            return {actor=created,record=record}
        end)
        if not ok then report(player,data.requestId,false,'Wanderer konnte nicht erstellt werden: '..tostring(result));return end
        actorId=result.actor.id;recordId=result.actor.recordId;actorRef=result.actor
        pending={player=player,requestId=data.requestId,frames=0}
        return
    end
    if not actor then
        report(player,data.requestId,false,'Der eigene Wanderer ist hier nicht geladen.');return
    end
    if command=='pause' then
        actor:sendEvent('RemoveAIPackages','Wander')
        report(player,data.requestId,true,'Eigene Wander-Routine pausiert.')
    elseif command=='resume' then
        actor:sendEvent('StartAIPackage',{type='Wander',distance=520,duration=3600,
            idle={idle2=0,idle3=0,idle4=0,idle5=0,idle6=0,idle7=0,idle8=0,idle9=0},isRepeat=true})
        report(player,data.requestId,true,'Eigene Wander-Routine gestartet.')
    elseif command=='dismiss' then
        -- resolve() validates generated record, generated instance and no content file.
        actor:remove();actorId=nil;recordId=nil;actorRef=nil
        report(player,data.requestId,true,'Nur der HALVETH-Wanderer wurde entfernt.')
    else report(player,data.requestId,false,'Unbekannte Wanderer-Aktion.') end
end
local function update()
    if not pending then return end
    pending.frames=pending.frames+1
    if pending.frames<5 then return end
    local actor=resolve()
    if actor then
        actor:sendEvent('StartAIPackage',{type='Wander',distance=520,duration=3600,
            idle={idle2=0,idle3=0,idle4=0,idle5=0,idle6=0,idle7=0,idle8=0,idle9=0},isRepeat=true})
        report(pending.player,pending.requestId,true,'Eigener Wanderer ist sichtbar und laeuft mit nativer OpenMW-AI.')
    else report(pending.player,pending.requestId,false,'Wanderer wurde erstellt, ist aber noch nicht geladen.') end
    pending=nil
end
return {engineHandlers={onUpdate=update,
    onSave=function()return {version=1,actorId=actorId,recordId=recordId}end,
    onLoad=function(data)
        pending=nil;actorRef=nil
        actorId=type(data)=='table' and data.version==1 and data.actorId or nil
        recordId=type(data)=='table' and data.version==1 and data.recordId or nil
    end,
    onNewGame=function()actorId=nil;recordId=nil;pending=nil;actorRef=nil end},
    eventHandlers={HALVETH_AmbientRequest=request}}
