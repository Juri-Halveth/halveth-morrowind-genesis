-- SPDX-License-Identifier: MIT
-- Own, bounded workshop. Inputs are actual player items; no free seeds.
local world=require('openmw.world')
local core=require('openmw.core')
local types=require('openmw.types')
local util=require('openmw.util')
local C=require('scripts.veyra_fieldwork.config')
local state,player,lastScan,fault=nil,nil,-100,nil
local function valid(o)return o and o:isValid()end
local function same(a,b)return valid(a) and valid(b) and a.id==b.id end
local function inventory()return types.Actor.inventory(player)end
local function amount(id)return valid(player) and inventory():countOf(id) or 0 end
local function log(kind,text)print('FIELDWORK|kind='..kind..'|'..(text or ''))end
local function near(object)
    return valid(player) and valid(object) and object.cell==player.cell
        and (object.position-player.position):length()<=C.range
end
local function status()
    local out={version=C.version,placed=state~=nil,phase=fault and 'LOAD_HOLD' or 'UNPLACED',
        saltrice=amount(C.saltrice),comberry=amount(C.comberry),gameSeconds=world.getGameTime(),
        cropHarvests=state and state.cropHarvests or 0,rationsMade=state and state.rationsMade or 0,
        noFreeSeeds=true,networkEffects=0}
    if not state then return out end
    local j=state.job
    out.phase=j and j.phase or 'EMPTY';out.kind=j and j.kind or nil
    out.dueSeconds=j and j.dueSeconds or nil
    out.remainingHours=j and j.dueSeconds and math.max(0,(j.dueSeconds-world.getGameTime())/3600) or nil
    out.plotValid=valid(state.plot);out.benchValid=valid(state.bench);out.nearPlot=near(state.plot);out.nearBench=near(state.bench)
    out.plotId=valid(state.plot) and state.plot.id or nil
    out.benchId=valid(state.bench) and state.bench.id or nil
    out.depotValid=valid(state.depot);out.depotEnabled=valid(state.depot) and state.depot.enabled or false
    out.depotSaltrice=valid(state.depot)and types.Container.content(state.depot):countOf(C.saltrice)or 0
    out.depotComberry=valid(state.depot)and types.Container.content(state.depot):countOf(C.comberry)or 0
    out.inputObserved=j and j.inputObserved or false
    out.outputObserved=j and j.outputObserved or false
    out.rationRecordId=state.rationRecordId
    return out
end
local function report()
    if valid(player) then player:sendEvent('VEYRA_FieldworkStatus',status())end
end
local function notice(text,kind)
    if valid(player) then player:sendEvent('VEYRA_FieldworkNotice',{message=text,kind=kind})end
    report()
end
local function rationRecord()
    local template
    for _,p in ipairs(types.Potion.records)do if p.model and p.icon and p.model~='' then template=p;break end end
    assert(template,'Native potion model/icon template unavailable')
    return world.createRecord(types.Potion.createRecordDraft({template=template,
        name=C.rationName,mwscript='',weight=.3,value=0,isAutocalc=false,
        effects={{id=core.magic.EFFECT_TYPE.RestoreFatigue,range=core.magic.RANGE.Self,
            area=0,duration=15,magnitudeMin=2,magnitudeMax=2}}})).id
end
local function place(data)
    if state then notice('Deine Feldwerkstatt steht bereits. Reise zu ihr zurueck.','WAIT');return end
    if not player.cell or not player.cell.isExterior or data.cellId~=player.cell.id
        or not data.plotPosition or not data.benchPosition then return end
    for _,p in ipairs({data.plotPosition,data.benchPosition})do
        local d=(p-player.position):length()
        if d<70 or d>400 or d~=d or (player.cell.hasWater and p.z<=player.cell.waterLevel+10)then
            log('PLACEMENT_REJECTED','distance='..d..'|pointZ='..p.z..'|waterLevel='..tostring(player.cell.waterLevel))
            notice('Hier fehlt ein trockener, erreichbarer Platz fuer Beet und Bank.','WAIT');return
        end
    end
    local flora=assert(types.Container.records[C.plotTemplate],'Native Saltrice model missing')
    local tableRecord=assert(types.Static.records[C.benchTemplate],'Native table model missing')
    local plotRecord=world.createRecord(types.Activator.createRecordDraft({name='LEVIATH Saltrice-Beet',model=flora.model,mwscript=''}))
    local benchRecord=world.createRecord(types.Activator.createRecordDraft({name='LEVIATH Feldwerkbank',model=tableRecord.model,mwscript=''}))
    local depotRecord=world.createRecord(types.Container.createRecordDraft({template=assert(types.Container.records['chest_small_01']),
        name='LEVIATH Werkstattdepot',mwscript='',isRespawning=false,isOrganic=false,weight=1000000}))
    local plot=world.createObject(plotRecord.id);local bench=world.createObject(benchRecord.id)
    local depot=world.createObject(depotRecord.id)
    plot:teleport(player.cell,data.plotPosition,{onGround=true})
    bench:teleport(player.cell,data.benchPosition,{rotation=util.transform.rotateZ(player.rotation:getYaw()),onGround=true})
    depot:teleport(player.cell,player.position-util.vector3(0,0,100000))
    for _,item in ipairs(types.Container.content(depot):getAll())do item:remove()end
    state={version=C.version,plot=plot,bench=bench,depot=depot,rationRecordId=rationRecord(),
        cropHarvests=0,rationsMade=0,job=nil,sequence=0}
    log('PLACED','actualActivators=2|freeSeeds=0')
    notice('Beet und Feldwerkbank stehen. Zutaten holst du selbst aus deiner Welt.','PLACED')
end
local function start(kind)
    if not state or not near(kind=='FARM' and state.plot or state.bench)then
        notice('Stehe bei deinem Beet oder deiner Werkbank.','WAIT');return
    end
    if state.job and state.job.phase~='DONE'then notice('Der bestehende Auftrag ist noch aktiv.','WAIT');return end
    local inputs={{recordId=C.saltrice,count=2}}
    if kind=='CRAFT'then inputs[#inputs+1]={recordId=C.comberry,count=1}end
    local baseline={};for _,need in ipairs(inputs)do
        baseline[need.recordId]=amount(need.recordId)
        if baseline[need.recordId]<need.count then notice('Du brauchst 2 Saltrice'..(kind=='CRAFT' and ' und 1 Comberry.' or ' als Saat.'),'MISSING');return end
    end
    state.sequence=state.sequence+1
    local job={kind=kind,sequence=state.sequence,phase='INPUT_PENDING',inputs=inputs,inputBaseline=baseline,
        requestedSeconds=world.getGameTime(),inputObserved=false,outputObserved=false}
    state.job=job
    for _,need in ipairs(inputs)do
        local left=need.count
        for _,item in ipairs(inventory():findAll(need.recordId))do
            if left<=0 then break end
            local take=math.min(left,item.count)
            if take==item.count then item:moveInto(state.depot)else item:split(take):moveInto(state.depot)end
            left=left-take
        end
        assert(left==0,'Input changed while workshop request was queued')
    end
    log('INPUT_REQUESTED','kind='..kind..'|sequence='..job.sequence)
end
local function harvest()
    local j=state and state.job
    if not j or j.phase~='READY'or not near(j.kind=='FARM'and state.plot or state.bench)then
        notice('Der Auftrag ist noch nicht bereit, oder du bist zu weit entfernt.','WAIT');return
    end
    local id=j.kind=='FARM'and C.saltrice or state.rationRecordId
    local n=j.kind=='FARM'and C.cropCount or 1
    j.output={recordId=id,count=n,baseline=amount(id),object=world.createObject(id,n)}
    j.phase='OUTPUT_PENDING'
    j.output.object:moveInto(inventory())
    log('OUTPUT_REQUESTED','kind='..j.kind..'|count='..n..'|sequence='..j.sequence)
end
local function action(data)
    if fault or type(data)~='table'or not same(data.player,player)then return end
    if data.action=='PLACE'then place(data)
    elseif data.action=='PLANT'then start('FARM')
    elseif data.action=='CRAFT'then start('CRAFT')
    elseif data.action=='HARVEST'then harvest()end
    report()
end
local function update(dt)
    if fault or not valid(player)or not state then return end
    if valid(state.depot)and state.depot.enabled then state.depot.enabled=false end
    -- Inventory actions also settle while the native UI pauses simulation.
    -- Growth and crafting still use only the game's clock below.
    local now=core.getRealTime();if now-lastScan<.25 then return end;lastScan=now
    local j=state.job;if not j then return end
    if j.phase=='INPUT_PENDING'then
        local paid=true
        for _,need in ipairs(j.inputs)do
            if types.Container.content(state.depot):countOf(need.recordId)~=need.count
                or amount(need.recordId)~=j.inputBaseline[need.recordId]-need.count then paid=false end
        end
        if paid then
            j.inputObserved=true;j.startedSeconds=world.getGameTime()
            j.dueSeconds=j.startedSeconds+3600*(j.kind=='FARM'and C.growHours or C.craftHours)
            j.phase='WORKING';log('INPUT_OBSERVED','kind='..j.kind..'|dueSeconds='..j.dueSeconds)
            notice(j.kind=='FARM'and 'Saat gesetzt. Saltrice waechst 24 Spielstunden.'or 'Feldration angesetzt. Die Werkbank braucht 6 Spielstunden.','WORKING')
        end
    elseif j.phase=='WORKING'and world.getGameTime()>=j.dueSeconds then
        j.phase='READY';log('READY','kind='..j.kind..'|sequence='..j.sequence)
        notice(j.kind=='FARM'and 'Dein Saltrice-Beet ist reif. Kehre zur Ernte zurueck.'or 'Die Feldration ist fertig. Hole sie an deiner Werkbank ab.','READY')
    elseif j.phase=='OUTPUT_PENDING'then
        local out=j.output
        -- A moved stack can merge and invalidate its old reference. Count delta
        -- is the bounded local oracle for fungible crops, not external provenance.
        if amount(out.recordId)==out.baseline+out.count then
            j.outputObserved=true;j.phase='CONSUMING'
            for _,need in ipairs(j.inputs)do
                for _,item in ipairs(types.Container.content(state.depot):findAll(need.recordId))do item:remove()end
            end
        end
    elseif j.phase=='CONSUMING'then
        local consumed=true
        for _,need in ipairs(j.inputs)do if types.Container.content(state.depot):countOf(need.recordId)~=0 then consumed=false end end
        if consumed then
            j.phase='DONE';j.finishedSeconds=world.getGameTime()
            if j.kind=='FARM'then state.cropHarvests=state.cropHarvests+1 else state.rationsMade=state.rationsMade+1 end
            log('DONE','kind='..j.kind..'|sequence='..j.sequence)
            notice(j.kind=='FARM'and 'Vier Saltrice geerntet. Die zwei Saatkoerner sind verbraucht.'or 'Eine Feldration liegt in deinem Inventar. Zutaten verbraucht.','DONE')
        end
    end
end
local function load(data)
    state,player,lastScan,fault=nil,nil,-100,nil
    if data==nil then return end
    if type(data)~='table'or data.version~=C.version or not data.plot or not data.bench or not data.depot
        or type(data.sequence)~='number'or type(data.cropHarvests)~='number'or type(data.rationsMade)~='number'then
        fault=data;log('LOAD_HOLD','savedData retained');return
    end
    state=data;log('LOAD','phase='..(state.job and state.job.phase or 'EMPTY'))
end
return {interfaceName='VeyraFieldwork',interface={version=C.version,status=status},
    engineHandlers={onPlayerAdded=function(p)player=p end,onUpdate=update,onSave=function()return fault or state end,
        onLoad=load,onNewGame=function()load(nil)end,onActivate=function(object,actor)
            if state and same(actor,player)and(same(object,state.plot)or same(object,state.bench))then
                player:sendEvent('VEYRA_FieldworkOpen',{})
            end
        end},eventHandlers={VEYRA_FieldworkAction=action,VEYRA_FieldworkStatusRequest=report}}
