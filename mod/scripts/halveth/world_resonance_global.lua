-- Save-backed fictional memories of exact plant instances. VFX are transient;
-- no source model, actor statistic, inventory or original quest is rewritten.
local core=require('openmw.core')
local world=require('openmw.world')
local types=require('openmw.types')
local vfs=require('openmw.vfs')
local R=require('scripts.halveth.resonance_rules')
local EFFECT_ID='HALVETH:WorldResonance'
local entries,entryCount,cooldown={},0,0
local active,clearOnUpdate=nil,true
local retained,blocked=nil,false
local effectSpawnCount,cleanupCount=0,0

local function clearEffect()
    -- Never use the empty id: that would also remove effects owned by the engine.
    if world.vfx then world.vfx.remove(EFFECT_ID) end
    if active then cleanupCount=cleanupCount+1 end
    active=nil
end
local function export()
    local out={}
    for id,e in pairs(entries) do out[id]=R.copy(e) end
    return {version=1,entries=out,cooldownRemaining=cooldown}
end
local function getState()
    local out=export()
    out.entryCount=entryCount;out.activeEffect=active~=nil;out.blocked=blocked
    out.effectSpawnCount=effectSpawnCount;out.cleanupCount=cleanupCount
    return out
end
local function result(player,success,status,message,entry,requestId)
    player:sendEvent('HALVETH_ResonanceResult',{success=success,status=status,message=message,
        entry=R.copy(entry),entryCount=entryCount,cooldownRemaining=cooldown,
        blocked=blocked,requestId=requestId})
end
local function usableTarget(player,target,point)
    if not target or not target:isValid() or not types.Static.objectIsInstance(target) then return nil,'UNSUPPORTED_TARGET' end
    local model,kind=R.model(types.Static.record(target).model)
    if not model then return nil,'UNSUPPORTED_TARGET' end
    local cell,other=player.cell,target.cell
    if not cell or not other or not cell.isExterior or not other.isExterior
        or cell.worldSpaceId~=other.worldSpaceId then return nil,'OUT_OF_RANGE' end
    if not point or not R.finite(point.x) or not R.finite(point.y) or not R.finite(point.z)
        or (point-player.position):length()>R.range
        or (target.position-player.position):length()>R.originRange
        or (point-target.position):length()>R.originRange then return nil,'OUT_OF_RANGE' end
    return {id=tostring(target.id),recordId=target.recordId,model=model,cell=R.cellKey(other),kind=kind}
end
local function effectModel(action)
    local names=action=='answer' and {'restorehealth','sanctuary'} or {'sanctuary','restorehealth'}
    for _,name in ipairs(names) do
        local effect=core.magic.effects.records[name]
        local record=effect and types.Static.records[effect.castStatic]
        if record and record.model~='' and vfs.fileExists(record.model) then return record.model end
    end
end
local function request(data)
    if type(data)~='table' then return end
    local player=data.player
    if not player or not player:isValid() or not types.Player.objectIsInstance(player) then return end
    local id=type(data.requestId)=='string' and #data.requestId<=100 and data.requestId or nil
    local function fail(status,message) result(player,false,status,message,nil,id) end
    if blocked then fail('INVALID_STATE','Diese Erinnerung stammt aus einem unbekannten Stand und bleibt unverändert erhalten.');return end
    if data.action~='listen' and data.action~='answer' then fail('INVALID_ACTION','Lauschen oder antworten?');return end
    local ok,target,status=pcall(usableTarget,player,data.target,data.point)
    if not ok or not target then
        fail(ok and status or 'UNSUPPORTED_TARGET','Sieh draußen einen nahen leuchtenden Kristall oder Baum an.');return
    end
    if cooldown>0 then fail('COOLDOWN','Der letzte Lichtkreis klingt noch aus.');return end
    local existing=entries[target.id]
    if existing and (existing.recordId~=target.recordId or existing.model~=target.model or existing.cell~=target.cell) then
        fail('IDENTITY_CHANGED','Diese Spur passt nicht mehr zu ihrer früheren Gestalt. Die Erinnerung bleibt erhalten.');return
    end
    if data.action=='answer' and not existing then
        fail('FIRST_LISTEN_REQUIRED','Lausche diesem Ort zuerst. Danach kannst du ihm antworten.');return
    end
    if not existing and entryCount>=R.maxEntries then
        fail('MEMORY_FULL','Das Buch dieser Orte ist voll. Die bisherigen Erinnerungen bleiben erhalten.');return
    end
    local day=math.floor(math.max(0,core.getGameTime())/86400)
    local priorStage=existing and existing.stage or 0
    local priorDay=existing and existing.lastDay or day
    local nextEntry=existing and R.copy(existing) or target
    nextEntry.firstDay=nextEntry.firstDay or day
    -- A player-controlled change to game time must not rewrite recorded chronology.
    nextEntry.lastDay=math.max(priorDay,day)
    nextEntry.visits=math.min(1000000,(nextEntry.visits or 0)+1)
    nextEntry.stage=math.max(1,priorStage)
    if data.action=='answer' then nextEntry.stage=math.max(2,nextEntry.stage)
    elseif priorStage==2 and day>priorDay then nextEntry.stage=3 end
    local model=effectModel(data.action)
    if not model or not world.vfx then fail('EFFECT_UNAVAILABLE','Das Licht dieses Ortes ist hier noch nicht verfügbar.');return end
    local spawned,err=pcall(function()
        clearEffect()
        clearOnUpdate=false
        world.vfx.spawn(model,data.point,{scale=data.action=='answer' and 0.7 or 0.5,
            loop=true,useAmbientLight=false,vfxId=EFFECT_ID})
    end)
    if not spawned then
        print('HALVETH_RESONANCE_EFFECT_ERROR '..tostring(err))
        fail('EFFECT_UNAVAILABLE','Der Lichtkreis konnte nicht entstehen. Versuche es später noch einmal.');return
    end
    entries[target.id]=nextEntry
    if not existing then entryCount=entryCount+1 end
    cooldown=R.cooldown;effectSpawnCount=effectSpawnCount+1
    active={player=player,cell=R.cellKey(player.cell),remaining=R.effectSeconds}
    local sun=R.finite(data.sun) and data.sun>=0 and data.sun<=1 and data.sun or nil
    local message=R.reply(nextEntry,data.action,priorStage,priorDay,day,sun,data.storm==true)
    local responseStatus=data.action=='answer' and 'ANSWERED' or nextEntry.stage==3 and priorStage==2 and 'REMEMBERED' or 'LISTENED'
    result(player,true,responseStatus,message,nextEntry,id)
end
local function onLoad(data)
    entries,entryCount,cooldown,active,clearOnUpdate={},0,0,nil,true
    retained,blocked=nil,false;effectSpawnCount,cleanupCount=0,0
    if data==nil then return end
    local valid=type(data)=='table' and data.version==1 and type(data.entries)=='table'
        and R.finite(data.cooldownRemaining) and data.cooldownRemaining>=0 and data.cooldownRemaining<=R.cooldown
    if valid then
        for key in pairs(data) do if key~='version' and key~='entries' and key~='cooldownRemaining' then valid=false end end
        for id,e in pairs(data.entries) do
            entryCount=entryCount+1
            if entryCount>R.maxEntries or not R.validEntry(id,e) then valid=false;break end
        end
    end
    if not valid then retained,blocked,entryCount=data,true,0;return end
    for id,e in pairs(data.entries) do entries[id]=R.copy(e) end
    cooldown=data.cooldownRemaining
end
return {interfaceName='HALVETHResonanceWorld',interface={version=1,getState=getState},
    engineHandlers={onLoad=onLoad,onSave=function() if blocked then return retained end;return export() end,
        onUpdate=function(dt)
            if clearOnUpdate then clearEffect();clearOnUpdate=false end
            if not R.finite(dt) or dt<=0 then return end
            cooldown=math.max(0,cooldown-dt)
            if active then
                active.remaining=active.remaining-dt
                if active.remaining<=0 or not active.player:isValid() or R.cellKey(active.player.cell)~=active.cell then clearEffect() end
            end
        end},eventHandlers={HALVETH_ResonanceRequest=request,
        HALVETH_ResonanceInspect=function(data)
            local player=type(data)=='table' and data.player
            if player and player:isValid() and types.Player.objectIsInstance(player) then
                player:sendEvent('HALVETH_ResonanceState',{entryCount=entryCount,blocked=blocked})
            end
        end}}
