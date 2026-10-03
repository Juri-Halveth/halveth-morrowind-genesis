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
    if not state then return {phase=loadFault and 'LOAD_HOLD' or 'UNSEEDED'} end
    return {phase=state.phase,routePhase=state.route.phase,
        elapsedDays=(world.getGameTime()-state.route.impact)/86400,
        impactSeconds=state.route.impact,gameSeconds=world.getGameTime(),
        giftCount=#state.items,deliveredCount=state.deliveredCount or 0,
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
        gift:moveInto(depot);letter:moveInto(depot)
        return {version=C.version,id=C.seedId,phase='DEPOT',depot=depot,
            items={{object=gift,recordId=gift.recordId,count=gift.count,delivered=false},
                {object=letter,recordId=letter.recordId,count=1,delivered=false}},
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
    if not state then seed() end
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
                notify('Elyra: Ein Brief und eine Klinge von jenseits deiner Welt. Druecke F10, um die Sendung anzunehmen.','ARRIVED')
                log('ARRIVED','distance='..(state.courier.position-player.position):length())
            end
        end
    elseif state.phase=='TRANSFERRING' then
        local delivered=0
        for _,item in ipairs(state.items) do
            if valid(item.object) and same(item.object.parentContainer,player) then item.delivered=true end
            if item.delivered then delivered=delivered+1 end
        end
        state.deliveredCount=delivered
        if delivered==#state.items then
            state.phase='CLAIMED'
            notify('Elyra: Die Weltenpost ist uebergeben. Brief und Geschenk sind jetzt in deinem Inventar.','CLAIMED')
            log('CLAIMED','items='..delivered..'|record='..C.giftRecordId)
            if valid(state.courier) then state.courier:sendEvent('StartAIPackage',{type='Wander',distance=250,duration=3600,isRepeat=true}) end
            report()
        end
    end
end
local function load(data)
    state,player,lastScan,followWarmup,loadFault,landingAt=nil,nil,-100,0,nil,-100
    if data==nil then return end
    if type(data)~='table' or data.version~=C.version or data.id~=C.seedId
        or type(data.route)~='table' or type(data.items)~='table' or #data.items~=2
        or type(data.route.impact)~='number' or type(data.route.lastTime)~='number' then
        loadFault=data;log('LOAD_HOLD','savedData retained');return
    end
    state=data
    if state.phase=='APPROACH' then followWarmup=0 end
    log('LOAD','phase='..state.phase)
end
return {interfaceName='VeyraCourier',interface={version=1,status=serialStatus},
    engineHandlers={onPlayerAdded=function(p)player=p;lastScan=-100 end,onUpdate=update,
        onSave=function()return loadFault or state end,onLoad=load,onNewGame=function()load(nil)end},
    eventHandlers={VEYRA_CourierClaim=claim,VEYRA_CourierStatusRequest=report,VEYRA_CourierLanding=landing}}
