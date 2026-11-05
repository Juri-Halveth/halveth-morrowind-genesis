-- SPDX-License-Identifier: MIT
-- OpenMW 0.51/API129 adapter. No network and no in-game console input.
local core=require('openmw.core')
local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')
local C=require('scripts.veyra_courier.config')
local R=require('scripts.veyra_courier.routes')
local state, player, lastScan, followWarmup, loadFault, landingAt = nil,nil,-100,0,nil,-100
local noServices={Spells=false,Spellmaking=false,Enchanting=false,Training=false,
    Repair=false,Barter=false,Weapon=false,Armor=false,Clothing=false,Books=false,
    Ingredients=false,Picks=false,Probes=false,Lights=false,Apparatus=false,
    RepairItems=false,Misc=false,Potions=false,MagicItems=false,Travel=false}
local function log(kind,detail)
    print('VEYRA|kind='..kind..'|'..(detail or ''))
end
local function valid(obj) return obj and obj:isValid() end
local function same(obj,other) return valid(obj) and valid(other) and obj.id==other.id end
local signatureFields={'recordId','condition','enchantmentCharge','soul','ownerId','ownerFaction','ownerRank'}
local function signature(obj)
    local data=types.Item.itemData(obj)
    local owner=obj.owner
    return {recordId=obj.recordId,condition=data.condition,enchantmentCharge=data.enchantmentCharge,
        soul=data.soul,ownerId=owner.recordId,ownerFaction=owner.factionId,ownerRank=owner.factionRank}
end
local function signatureEquals(a,b)
    for _,key in ipairs(signatureFields) do if a[key]~=b[key] then return false end end
    return true
end
local function inventoryBinding(item)
    local before,total={},0
    for _,obj in ipairs(types.Actor.inventory(player):getAll()) do
        if obj.recordId==item.recordId then
            before[obj.id]={count=obj.count,signature=signature(obj)}
            total=total+obj.count
        end
    end
    return {sourceObjectId=item.object.id,sourceSignature=signature(item.object),
        beforeStacks=before,beforeTotal=total,pendingChecks=0}
end
local function resolveTransfer(item)
    local transfer=item.transfer
    if not transfer then return false end
    if valid(item.object) and same(item.object.parentContainer,player)
        and item.object.count>=item.count and signatureEquals(signature(item.object),transfer.sourceSignature) then
        item.delivered=true;item.transferMethod='MOVED_REFERENCE';return true
    end
    -- A native merge consumes the source reference. Resolve the *surviving real
    -- stack*, using its saved identity/count and item state, never just totals.
    local seen,total,candidate,candidateCount={},0,nil,0
    local clean=true
    for _,obj in ipairs(types.Actor.inventory(player):getAll()) do
        if obj.recordId==item.recordId then
            seen[obj.id]=true;total=total+obj.count
            local prior=transfer.beforeStacks[obj.id]
            local delta=obj.count-(prior and prior.count or 0)
            if delta==item.count and same(obj.parentContainer,player)
                and signatureEquals(signature(obj),transfer.sourceSignature)
                and (not prior or signatureEquals(signature(obj),prior.signature)) then
                candidate=obj;candidateCount=candidateCount+1
            elseif delta~=0 or (prior and not signatureEquals(signature(obj),prior.signature)) then clean=false end
        end
    end
    for id in pairs(transfer.beforeStacks) do if not seen[id] then clean=false end end
    local depotCount=valid(state.depot) and types.Container.content(state.depot):countOf(item.recordId) or -1
    if transfer.pendingChecks==2 then
        log('TRANSFER_OBSERVATION','record='..item.recordId..'|before='..transfer.beforeTotal..'|after='..total
            ..'|depot='..depotCount..'|clean='..tostring(clean)..'|candidates='..candidateCount)
        local function describe(label,id,count,sig)
            local values={label,'id='..id,'count='..count}
            for _,key in ipairs(signatureFields) do values[#values+1]=key..'='..tostring(sig[key]) end
            log('TRANSFER_ITEM_STATE',table.concat(values,'|'))
        end
        describe('SOURCE',transfer.sourceObjectId,item.count,transfer.sourceSignature)
        for id,prior in pairs(transfer.beforeStacks) do describe('BEFORE',id,prior.count,prior.signature) end
        for _,obj in ipairs(types.Actor.inventory(player):getAll()) do
            if obj.recordId==item.recordId then describe('AFTER',obj.id,obj.count,signature(obj)) end
        end
    end
    if clean and candidateCount==1 and total==transfer.beforeTotal+item.count and depotCount==0 then
        item.object=candidate;item.delivered=true;item.transferMethod='ENGINE_STACK_MERGE'
        log('STACK_REBOUND','record='..item.recordId..'|sourceId='..transfer.sourceObjectId
            ..'|survivingId='..candidate.id..'|beforeCount='..(transfer.beforeStacks[candidate.id]
                and transfer.beforeStacks[candidate.id].count or 0)..'|afterCount='..candidate.count)
        return true
    end
    transfer.pendingChecks=transfer.pendingChecks+1
    return false
end
local function notify(message,kind)
    if valid(player) then player:sendEvent('VEYRA_CourierNotice',{message=message,kind=kind}) end
end
local function mapPosition()
    if not valid(player) or not player.cell then return nil end
    if player.cell.isExterior then
        return {x=math.floor(player.position.x/8192),y=math.floor(player.position.y/8192)}
    end
    return state and state.lastExterior or {x=C.origin.x,y=C.origin.y}
end
local function serialStatus()
    if not state then return {phase=loadFault and 'LOAD_HOLD' or 'UNSEEDED',schemaVersion=C.version,
        moduleVersion=C.moduleVersion,seedDemoOnEmpty=C.seedDemoOnEmpty==true,giftCount=0,
        deliveredCount=0,depotValid=false,courierValid=false} end
    local merged=0
    for _,item in ipairs(state.items) do if item.transferMethod=='ENGINE_STACK_MERGE' then merged=merged+1 end end
    return {phase=state.phase,routePhase=state.route.phase,schemaVersion=C.version,moduleVersion=C.moduleVersion,
        elapsedDays=(world.getGameTime()-state.route.impact)/86400,
        impactSeconds=state.route.impact,gameSeconds=world.getGameTime(),
        giftCount=#state.items,deliveredCount=state.deliveredCount or 0,mergedCount=merged,
        depotItemCount=valid(state.depot) and #types.Container.content(state.depot):getAll() or 0,
        depotValid=valid(state.depot),depotEnabled=valid(state.depot) and state.depot.enabled or false,
        courierValid=valid(state.courier),courierId=valid(state.courier) and state.courier.id or nil,
        courierRecord=valid(state.courier) and state.courier.recordId or nil,
        giftRecordId=C.giftRecordId,synthetic=true,networkEffects=0}
end
local function report()
    if valid(player) then player:sendEvent('VEYRA_CourierStatus',serialStatus()) end
end
local function seed()
    assert(types.Weapon.records[C.giftRecordId], 'Gift engine record not found')
    local chestTemplate=assert(types.Container.records['chest_small_01'],'Depot template not found')
    local depotRecord=world.createRecord(types.Container.createRecordDraft({template=chestTemplate,
        name='Verborgenes Weltenpost-Depot',mwscript='',isRespawning=false,isOrganic=false,weight=1000000}))
    local depot=world.createObject(depotRecord.id)
    local created={depot}
    local ok,result=pcall(function()
        -- A real, disabled engine reference anchored below an existing cell. It is
        -- preserved by the candidate save, not exposed as a playable chest.
        depot:teleport('Seyda Neen',util.vector3(-10150,-71300,-100000))
        for _,item in ipairs(types.Container.content(depot):getAll()) do item:remove() end
        local scroll
        for _,record in ipairs(types.Book.records) do
            if record.isScroll and record.model and record.model~='' then scroll=record;break end
        end
        assert(scroll,'Letter asset reference not found')
        local letterRecord=world.createRecord(types.Book.createRecordDraft({template=scroll,
            name=C.letterTitle,text=C.letterText,mwscript='',enchant='',skill='',
            weight=0.01,value=0,isScroll=true,enchantCapacity=0}))
        local gift=world.createObject(C.giftRecordId,C.giftCount)
        local letter=world.createObject(letterRecord.id,1)
        created[#created+1]=gift;created[#created+1]=letter
        local giftCount,letterCount=gift.count,letter.count
        assert(giftCount==C.giftCount and letterCount==1,'Native parcel quantity differs from declared creation')
        log('DEPOT_INPUT_BOUND','giftCount='..giftCount..'|letterCount='..letterCount)
        gift:moveInto(depot);letter:moveInto(depot)
        return {version=C.version,id=C.seedId,phase='DEPOT',depot=depot,
            items={{object=gift,recordId=gift.recordId,count=giftCount,delivered=false},
                {object=letter,recordId=letter.recordId,count=letterCount,delivered=false}},
            route=R.new(world.getGameTime(),C.origin),lastExterior=mapPosition(),
            deliveredCount=0,courier=nil,announced=false}
    end)
    if not ok then
        for _,obj in ipairs(created) do if valid(obj) then pcall(obj.remove,obj) end end
        error(result)
    end
    state=result
    log('IMPACT','synthetic=true|phase=DEPOT|items=2|gameSeconds='..state.route.impact)
end
local function spawnCourier(position)
    local template=assert(types.NPC.records[C.courierTemplate],'Courier NPC template not found')
    local record=world.createRecord(types.NPC.createRecordDraft({template=template,
        name=C.courierName,mwscript='',isMale=template.isMale,isAutocalc=true,
        isEssential=true,isRespawning=false,baseDisposition=90,baseGold=0,
        servicesOffered=noServices,travelDestinations={}}))
    local actor=world.createObject(record.id)
    state.courier=actor
    actor:teleport(player.cell,position,{onGround=true})
    state.phase='APPROACH'
    followWarmup=0
    log('COURIER_CREATED','name='..C.courierName..'|actorId='..actor.id..'|recordId='..actor.recordId)
end
local function landing(data)
    if not state or state.phase~='TRAVEL' or state.route.phase~='FINAL_LEG'
        or type(data)~='table' or not same(data.player,player) or data.cellId~=player.cell.id
        or not player.cell.isExterior or not data.position then return end
    local distance=(data.position-player.position):length()
    if distance<280 or distance>800 or distance~=distance then return end
    log('LANDING_PATH','pathPoints='..tostring(data.pathPoints)..'|distance='..distance)
    spawnCourier(data.position)
end
local function claim(data)
    if not valid(player) or type(data)~='table' or not same(data.player,player) then return end
    if not state or state.phase~='ARRIVED' or not valid(state.courier)
        or state.courier.cell~=player.cell or (state.courier.position-player.position):length()>320 then
        notify('Die Botin hat dich noch nicht erreicht.','WAIT');report();return
    end
    -- Bind all destination stacks before queuing any native move. These plain
    -- data witnesses persist if a save captures the TRANSFERRING phase.
    for _,item in ipairs(state.items) do
        if not item.delivered then
            if not valid(item.object) or item.object.count<1 then
                state.phase='TRANSFER_HOLD';notify('Die Depot-Referenz braucht eine Pruefung.','HOLD');report();return
            end
            -- moveInto may zero the source reference immediately. Observe the
            -- positive native quantity before moving and retain this number.
            item.count=item.object.count
            item.transfer=inventoryBinding(item)
        end
    end
    state.phase='TRANSFERRING'
    for _,item in ipairs(state.items) do
        if not item.delivered then
            assert(valid(item.object),'Depot item reference unavailable')
            item.object:moveInto(types.Actor.inventory(player))
        end
    end
    log('TRANSFER_REQUESTED','items='..#state.items)
end
local function update(dt)
    if loadFault or not valid(player) or not player.cell then return end
    if not state then
        if C.seedDemoOnEmpty==true then seed()else return end
    end
    if valid(state.depot) and state.depot.enabled then state.depot.enabled=false end
    local now=core.getSimulationTime()
    if now-lastScan<0.25 then return end
    lastScan=now
    local pos=mapPosition()
    if player.cell.isExterior then state.lastExterior=pos end
    if state.phase=='DEPOT' or state.phase=='TRAVEL' then
        R.advance(state.route,world.getGameTime(),pos,C.departureDays,C.cellsPerDay)
        state.phase=state.route.phase=='DEPOT' and 'DEPOT' or 'TRAVEL'
        if state.route.phase=='FINAL_LEG' and player.cell.isExterior and not world.isWorldPaused() and now-landingAt>2 then
            landingAt=now
            player:sendEvent('VEYRA_CourierFindLanding',{})
        end
    elseif state.phase=='APPROACH' and valid(state.courier) then
        if world.isWorldPaused() then return end
        followWarmup=followWarmup+1
        if followWarmup==3 then
            state.courier:sendEvent('StartAIPackage',{type='Follow',target=player,duration=0,isRepeat=false})
            log('FOLLOW_REQUESTED','target=PLAYER')
        end
        if state.courier.cell==player.cell and (state.courier.position-player.position):length()<=260 then
            state.phase='ARRIVED'
            state.arrivedSeconds=world.getGameTime()
            if not state.announced then
                state.announced=true
                notify('Elyra: Ein Brief und eine Klinge von jenseits deiner Welt. Druecke K, um die Sendung anzunehmen.','ARRIVED')
                log('ARRIVED','distance='..(state.courier.position-player.position):length())
            end
        end
    elseif state.phase=='TRANSFERRING' then
        local delivered=0
        for _,item in ipairs(state.items) do
            if not item.delivered then resolveTransfer(item) end
            if item.delivered then delivered=delivered+1 end
        end
        state.deliveredCount=delivered
        if delivered==#state.items then
            state.phase='CLAIMED'
            notify('Elyra: Die Weltenpost ist uebergeben. Brief und Geschenk sind jetzt in deinem Inventar.','CLAIMED')
            log('CLAIMED','items='..delivered..'|record='..C.giftRecordId)
            if valid(state.courier) then state.courier:sendEvent('StartAIPackage',{type='Wander',distance=250,duration=3600,isRepeat=true}) end
            report()
        else
            for _,item in ipairs(state.items) do
                if not item.delivered and (not item.transfer or item.transfer.pendingChecks>=40) then
                    state.phase='TRANSFER_HOLD'
                    notify('Die Weltenpost bleibt zur Pruefung angehalten. Die Botin erzeugt keine zweite Sendung.','HOLD')
                    log('TRANSFER_HOLD','record='..item.recordId..'|delivered='..delivered)
                    report();break
                end
            end
        end
    end
end
local function load(data)
    state,player,lastScan,followWarmup,loadFault,landingAt=nil,nil,-100,0,nil,-100
    if data==nil then return end
    if type(data)~='table' or (data.version~=1 and data.version~=C.version) or data.id~=C.seedId
        or type(data.route)~='table' or type(data.items)~='table' or #data.items~=2
        or type(data.route.impact)~='number' or type(data.route.lastTime)~='number' then
        loadFault=data;log('LOAD_HOLD','savedData retained');return
    end
    state=data
    if state.version==1 then
        state.version=C.version
        if state.phase=='TRANSFERRING' then
            -- Version 1 never captured a pre-move witness. Do not invent one.
            state.phase='TRANSFER_HOLD';log('TRANSFER_HOLD','legacyUnboundTransfer=true')
        end
    end
    if state.phase=='TRANSFERRING' then
        for _,item in ipairs(state.items) do
            if not item.delivered then
                local tr=item.transfer
                if type(item.count)~='number' or item.count<1 or type(tr)~='table' or type(tr.sourceObjectId)~='string'
                    or type(tr.sourceSignature)~='table' or type(tr.beforeStacks)~='table'
                    or type(tr.beforeTotal)~='number' or type(tr.pendingChecks)~='number' then
                    state.phase='TRANSFER_HOLD';log('TRANSFER_HOLD','savedTransferBindingUnavailable=true');break
                end
            end
        end
    end
    if state.phase=='APPROACH' then followWarmup=0 end
    log('LOAD','phase='..state.phase)
end
return {interfaceName='VeyraCourier',interface={version=2,status=serialStatus},
    engineHandlers={onPlayerAdded=function(p)player=p;lastScan=-100 end,onUpdate=update,
        onSave=function()return loadFault or state end,onLoad=load,onNewGame=function()load(nil)end},
    eventHandlers={VEYRA_CourierClaim=claim,VEYRA_CourierStatusRequest=report,VEYRA_CourierLanding=landing}}
