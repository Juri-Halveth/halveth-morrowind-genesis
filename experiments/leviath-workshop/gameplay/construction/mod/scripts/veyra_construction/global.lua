-- SPDX-License-Identifier: MIT
-- Own frontier plantbeds; all material inputs come from the actual inventory.
local world=require('openmw.world')
local core=require('openmw.core')
local types=require('openmw.types')
local util=require('openmw.util')
local C=require('scripts.veyra_construction.config')
local state,player,lastScan,fault=nil,nil,-100,nil
local function valid(o)return o and o:isValid()end
local function same(a,b)return valid(a)and valid(b)and a.id==b.id end
local function inventory()return types.Actor.inventory(player)end
local function amount(id)return valid(player)and inventory():countOf(id)or 0 end
local function signature(item)
    local owner=item.owner
    return {recordId=item.recordId,ownerRecord=owner.recordId,ownerFaction=owner.factionId,ownerRank=owner.factionRank}
end
local function signatureSame(a,b)
    return a and b and a.recordId==b.recordId and a.ownerRecord==b.ownerRecord
        and a.ownerFaction==b.ownerFaction and a.ownerRank==b.ownerRank
end
local function inputSignature(id,count)
    local left,sig=count,nil
    for _,item in ipairs(inventory():findAll(id))do
        if left<=0 then break end
        local current=signature(item)
        if sig and not signatureSame(sig,current)then return nil end
        sig=current;left=left-math.min(left,item.count)
    end
    return left==0 and sig or nil
end
local function inventorySignatureMatches(id,sig)
    for _,item in ipairs(inventory():findAll(id))do if not signatureSame(signature(item),sig)then return false end end
    return true
end
local function contents(plot)return types.Container.content(plot.depot)end
local function depotMatches(plot,id,count,sig)
    if contents(plot):countOf(id)~=count then return false end
    for _,item in ipairs(contents(plot):findAll(id))do if not signatureSame(signature(item),sig)then return false end end
    return true
end
local function finite(n)return type(n)=='number'and n==n and math.abs(n)<100000000 end
local function log(kind,text)print('CONSTRUCT|kind='..kind..'|'..(text or ''))end
local function frontier(cell)
    return cell and cell.isExterior and cell.gridX>=C.grid.minX and cell.gridX<=C.grid.maxX
        and cell.gridY>=C.grid.minY and cell.gridY<=C.grid.maxY
end
local function near(plot)
    return valid(player)and plot and valid(plot.object)and plot.object.cell==player.cell
        and(plot.object.position-player.position):length()<=C.range
end
local function find(id)
    for _,plot in ipairs(state and state.plots or{})do if plot.object.id==id then return plot end end
end
local function nearest()
    local best,dist=nil,C.range+1
    for _,plot in ipairs(state and state.plots or{})do
        if near(plot)then local d=(plot.object.position-player.position):length()
            if d<dist then best,dist=plot,d end
        end
    end
    return best
end
local function status()
    local out={version=C.version,saveSchema=C.saveSchema,phase=fault and'LOAD_HOLD'or'READY',
        metal=amount(C.metal),rice=amount(C.rice),cap=C.cap,plotCount=state and#state.plots or 0,
        inFrontier=valid(player)and frontier(player.cell)or false,networkEffects=0,noFreeInputs=true,
        builds=state and state.builds or 0,dismantles=state and state.dismantles or 0,
        harvests=state and state.harvests or 0,plots={}}
    if state and state.transaction then out.phase=state.transaction.phase;out.transactionKind=state.transaction.kind end
    for _,plot in ipairs(state and state.plots or{})do
        out.plots[#out.plots+1]={id=plot.object.id,valid=valid(plot.object),depotId=plot.depot.id,
            depotValid=valid(plot.depot),depotEnabled=valid(plot.depot)and plot.depot.enabled or false,
            position=valid(plot.object)and plot.object.position or nil,cellId=valid(plot.object)and plot.object.cell.id or nil,
            phase=plot.phase,near=near(plot),harvests=plot.harvests,
            metal=valid(plot.depot)and contents(plot):countOf(C.metal)or 0,
            seeds=valid(plot.depot)and contents(plot):countOf(C.rice)or 0,metalSignature=plot.metalSignature,seedSignature=plot.seedSignature,
            dueSeconds=plot.dueSeconds,remainingHours=plot.dueSeconds and math.max(0,(plot.dueSeconds-world.getGameTime())/3600)or nil}
    end
    local best=valid(player)and nearest()or nil;out.nearestId=best and best.object.id or nil
    return out
end
local function report()if valid(player)then player:sendEvent('VEYRA_ConstructionStatus',status())end end
local function notice(text)if valid(player)then player:sendEvent('VEYRA_ConstructionNotice',{message=text})end;report()end
local function hold(reason)
    if state and state.transaction then state.transaction.phase='TRANSACTION_HOLD';state.transaction.holdReason=reason end
    log('HOLD',reason);notice('Materialstand gehalten: '..reason..'. Deine gebundenen Objekte bleiben erhalten.')
end
local function emptyState()
    return {version=C.saveSchema,moduleVersion=C.version,sequence=0,plots={},transaction=nil,
        builds=0,dismantles=0,harvests=0}
end
local function ensureRecords()
    if state.plotRecordId then return end
    state.plotRecordId=world.createRecord(types.Activator.createRecordDraft({name='LEVIATH Pflanzbeet',model=C.model,mwscript=''})).id
    local draft=types.Container.createRecordDraft({template=assert(types.Container.records['chest_small_01']),
        name='LEVIATH Baumaterialdepot',mwscript='',isRespawning=false,isOrganic=false,weight=1000000})
    state.depotRecordId=world.createRecord(draft).id
end
local function deposit(plot,id,count)
    local left=count
    for _,item in ipairs(inventory():findAll(id))do
        if left<=0 then break end
        local take=math.min(left,item.count)
        if take==item.count then item:moveInto(plot.depot)else item:split(take):moveInto(plot.depot)end
        left=left-take
    end
    assert(left==0,'Construction input changed before move')
end
local function placement(data)
    if not frontier(player.cell)or data.cellId~=player.cell.id or not data.position
        or not finite(data.yaw)or type(data.groundChecks)~='table'or#data.groundChecks~=5 then return false end
    local p=data.position
    if not finite(p.x)or not finite(p.y)or not finite(p.z)then return false end
    local gx,gy=math.floor(p.x/8192),math.floor(p.y/8192)
    if gx<C.grid.minX or gx>C.grid.maxX or gy<C.grid.minY or gy>C.grid.maxY then return false end
    local d=(p-player.position):length()
    if d<100 or d>300 or(player.cell.hasWater and p.z<=player.cell.waterLevel+12)then return false end
    for _,check in ipairs(data.groundChecks)do
        if not finite(check.height)or not finite(check.normalZ)or check.normalZ<.92 or math.abs(check.height-p.z)>12 then return false end
    end
    if not data.headroomClear then return false end
    for _,plot in ipairs(state.plots)do
        if valid(plot.object)and plot.object.cell==player.cell and(plot.object.position-p):length()<C.spacing then return false end
    end
    return true
end
local function build(data)
    if#state.plots>=C.cap then notice('Die Grenze von 32 eigenen Beeten ist erreicht.');return end
    if not placement(data)then log('PLACEMENT_REJECTED');notice('Hier passt kein trockenes, freies Beet.');return end
    if amount(C.metal)<C.metalCost then notice('Du brauchst 2 echte Scrap-Metal aus deinem Inventar.');return end
    local sig=inputSignature(C.metal,C.metalCost)
    if not sig then notice('Die Rahmenmaterialien brauchen einen eindeutigen gemeinsamen Gegenstandstand.');return end
    ensureRecords();state.sequence=state.sequence+1
    local depot=world.createObject(state.depotRecordId)
    depot:teleport(player.cell,player.position-util.vector3(0,0,100000))
    for _,item in ipairs(types.Container.content(depot):getAll())do item:remove()end
    local plot={sequence=state.sequence,depot=depot,phase='BUILDING',harvests=0}
    state.transaction={kind='BUILD',phase='INPUT_PENDING',plot=plot,position=data.position,
        yaw=data.yaw,cellId=player.cell.id,inputBaseline=amount(C.metal),inputSignature=sig,scans=0}
    deposit(plot,C.metal,C.metalCost);log('BUILD_INPUT_REQUESTED','count='..C.metalCost)
end
local function plant(plot)
    if plot.phase~='EMPTY'then notice('Das Beet hat bereits eine Saat oder einen Ertrag.');return end
    if amount(C.rice)<C.seedCount then notice('Du brauchst 2 echte Saltrice als Saat.');return end
    local sig=inputSignature(C.rice,C.seedCount)
    if not sig then notice('Die Saat braucht einen eindeutigen gemeinsamen Gegenstandstand.');return end
    state.transaction={kind='PLANT',phase='INPUT_PENDING',plot=plot,inputBaseline=amount(C.rice),inputSignature=sig,scans=0}
    deposit(plot,C.rice,C.seedCount);log('SEEDS_REQUESTED','count='..C.seedCount)
end
local function harvest(plot)
    if plot.phase~='RIPE'then notice('Die Saat braucht 24 Spielstunden.');return end
    local output=world.createObject(C.rice,C.cropCount)
    local actual=output.count;assert(actual==C.cropCount,'Native crop count mismatch')
    state.transaction={kind='HARVEST',phase='OUTPUT_PENDING',plot=plot,output=output,
        outputBaseline=amount(C.rice),outputCount=actual,scans=0}
    output:moveInto(inventory());log('CROP_OUTPUT_REQUESTED','actualCount='..actual)
end
local function dismantle(plot)
    local expectedRice=(plot.phase=='GROWING'or plot.phase=='RIPE')and C.seedCount or 0
    if not depotMatches(plot,C.metal,C.metalCost,plot.metalSignature)
        or(expectedRice>0 and not depotMatches(plot,C.rice,expectedRice,plot.seedSignature))
        or(expectedRice==0 and contents(plot):countOf(C.rice)~=0)then
        state.transaction={kind='DISMANTLE',phase='TRANSACTION_HOLD',plot=plot,holdReason='Depot quantities changed'}
        notice('Der Depotstand muss geklaert werden.');return
    end
    local tx={kind='DISMANTLE',phase='RETURN_PENDING',plot=plot,scans=0,
        metalBaseline=amount(C.metal),riceBaseline=amount(C.rice),metalCount=C.metalCost,riceCount=expectedRice,movedIds={},
        metalSignature=plot.metalSignature,riceSignature=plot.seedSignature,removePosition=plot.object.position,removedObjectId=plot.object.id}
    state.transaction=tx
    if not inventorySignatureMatches(C.metal,tx.metalSignature)
        or(expectedRice>0 and not inventorySignatureMatches(C.rice,tx.riceSignature))then hold('Refund destination has a different material signature');return end
    for _,item in ipairs(contents(plot):getAll())do
        if item.recordId~=C.metal and item.recordId~=C.rice then hold('Unexpected item in own depot');return end
        tx.movedIds[#tx.movedIds+1]={id=item.id,recordId=item.recordId,count=item.count,signature=signature(item)}
    end
    for _,item in ipairs(contents(plot):getAll())do item:moveInto(inventory())end
    log('RETURN_REQUESTED','metal='..C.metalCost..'|seeds='..expectedRice)
end
local function action(data)
    if fault or type(data)~='table'or not same(data.player,player)then return end
    if not state then state=emptyState()end
    if state.transaction then notice('Der bestehende Materialvorgang muss erst abgeschlossen werden.');return end
    if data.action=='BUILD'then build(data)
    else
        local plot=find(data.plotId)
        if not plot or not near(plot)or not valid(plot.depot)then notice('Stehe bei dem ausgewaehlten eigenen Beet.');return end
        if data.action=='PLANT'then plant(plot)
        elseif data.action=='HARVEST'then harvest(plot)
        elseif data.action=='DISMANTLE'then dismantle(plot)end
    end
    report()
end
local function update()
    if fault or not valid(player)or not state then return end
    for _,plot in ipairs(state.plots)do
        if valid(plot.depot)and plot.depot.enabled then plot.depot.enabled=false end
        if plot.phase=='GROWING'and world.getGameTime()>=plot.dueSeconds then
            plot.phase='RIPE';log('RIPE','sequence='..plot.sequence);notice('Ein LEVIATH-Beet ist reif. Kehre zur Ernte zurueck.')
        end
    end
    local now=core.getRealTime();if now-lastScan<.25 then return end;lastScan=now
    local tx=state.transaction;if not tx or tx.phase=='TRANSACTION_HOLD'then return end
    local plot=tx.plot
    if valid(plot.depot)and plot.depot.enabled then plot.depot.enabled=false end
    if tx.phase~='REMOVING'and not valid(plot.depot)then hold('Own depot reference unavailable');return end
    tx.scans=tx.scans+1
    if tx.phase=='INPUT_PENDING'then
        local id,n=tx.kind=='BUILD'and C.metal or C.rice,tx.kind=='BUILD'and C.metalCost or C.seedCount
        if amount(id)==tx.inputBaseline-n and depotMatches(plot,id,n,tx.inputSignature)then
            if tx.kind=='BUILD'then
                plot.metalSignature=tx.inputSignature
                plot.object=world.createObject(state.plotRecordId)
                plot.object:teleport(world.getCellById(tx.cellId),tx.position,{rotation=util.transform.rotateZ(tx.yaw),onGround=true})
                tx.phase='OBJECT_PENDING';tx.scans=0
            else
                plot.seedSignature=tx.inputSignature
                plot.phase='GROWING';plot.startedSeconds=world.getGameTime();plot.dueSeconds=plot.startedSeconds+C.growHours*3600
                state.transaction=nil;log('SEEDS_OBSERVED','sequence='..plot.sequence);notice('2 Saat eingesetzt. Wachstum: 24 Spielstunden.')
            end
        end
    elseif tx.phase=='OBJECT_PENDING'then
        if valid(plot.object)and plot.object.enabled and plot.object.cell.id==tx.cellId
            and(plot.object.position-tx.position):length()<20 then
            plot.phase='EMPTY';state.plots[#state.plots+1]=plot;state.builds=state.builds+1;state.transaction=nil
            log('BUILD_OBSERVED','id='..plot.object.id);notice('Dein eigenes Beet steht. Die 2 Rahmenmaterialien sind gebunden.')
        end
    elseif tx.phase=='OUTPUT_PENDING'then
        if amount(C.rice)==tx.outputBaseline+tx.outputCount then
            tx.phase='CONSUMING';tx.scans=0
            for _,item in ipairs(contents(plot):findAll(C.rice))do item:remove()end
        end
    elseif tx.phase=='CONSUMING'then
        if contents(plot):countOf(C.rice)==0 then
            plot.phase='EMPTY';plot.dueSeconds=nil;plot.startedSeconds=nil;plot.seedSignature=nil;plot.harvests=plot.harvests+1
            state.harvests=state.harvests+1;state.transaction=nil
            log('HARVEST_OBSERVED','sequence='..plot.sequence);notice('Vier Saltrice erhalten; zwei Saat verbraucht. Fuer die naechste Ernte neu saeen.')
        end
    elseif tx.phase=='RETURN_PENDING'then
        if amount(C.metal)==tx.metalBaseline+tx.metalCount and amount(C.rice)==tx.riceBaseline+tx.riceCount
            and inventorySignatureMatches(C.metal,tx.metalSignature)
            and(tx.riceCount==0 or inventorySignatureMatches(C.rice,tx.riceSignature))and#contents(plot):getAll()==0 then
            plot.object:remove();plot.depot:remove();tx.phase='REMOVING';tx.scans=0
        end
    elseif tx.phase=='REMOVING'then
        local objectGone=not valid(plot.object)or(plot.object.count==0 and not plot.object.enabled)
        local depotGone=not valid(plot.depot)or(plot.depot.count==0 and not plot.depot.enabled)
        if objectGone and depotGone and not tx.removalProbeRequested then
            if not tx.removePosition or not tx.removedObjectId then hold('Saved removal lacks bound location witness');return end
            tx.removalProbeRequested=true
            player:sendEvent('VEYRA_ConstructionRemovalProbe',{plotId=tx.removedObjectId,position=tx.removePosition,sequence=plot.sequence})
        end
        if objectGone and depotGone and tx.removalWorldClear then
            for i,p in ipairs(state.plots)do if p.sequence==plot.sequence then table.remove(state.plots,i);break end end
            state.dismantles=state.dismantles+1;state.transaction=nil
            log('DISMANTLE_OBSERVED','sequence='..plot.sequence);notice('Beet rueckgebaut. Die vorhandenen Rahmen und unverbauten Saatreferenzen sind zurueck.')
        end
    end
    if state.transaction and tx.scans>=80 then hold('Native material or reference observation remained ambiguous')end
end
local function removalObservation(data)
    local tx=state and state.transaction
    if fault or not tx or tx.phase~='REMOVING'or type(data)~='table'or not same(data.player,player)
        or data.plotId~=tx.removedObjectId or data.sequence~=tx.plot.sequence then return end
    if data.clear==true then tx.removalWorldClear=true;log('REMOVAL_WORLD_OBSERVED','id='..tx.removedObjectId)end
end
local function load(data)
    state,player,lastScan,fault=nil,nil,-100,nil
    if data==nil then return end
    if type(data)=='table'and data.loadHold then fault=data;return end
    if type(data)~='table'or data.version~=C.saveSchema or type(data.plots)~='table'or#data.plots>C.cap
        or type(data.sequence)~='number'or type(data.builds)~='number'or type(data.dismantles)~='number'
        or type(data.harvests)~='number'then fault={loadHold=true,savedData=data};log('LOAD_HOLD');return end
    state=data
    if state.transaction and state.transaction.phase=='REMOVING'then state.transaction.removalProbeRequested=false end
    log('LOAD','plotCount='..#state.plots)
end
return {interfaceName='VeyraConstruction',interface={version=C.version,status=status},
    engineHandlers={onPlayerAdded=function(p)player=p end,onUpdate=update,onSave=function()return fault or state end,
        onLoad=load,onNewGame=function()load(nil)end,onActivate=function(object,actor)
            if not fault and same(actor,player)then local plot=find(object.id)
                if plot and near(plot)then player:sendEvent('VEYRA_ConstructionOpen',{plotId=object.id})end
            end
        end},eventHandlers={VEYRA_ConstructionAction=action,VEYRA_ConstructionStatusRequest=report,
            VEYRA_ConstructionRemovalObservation=removalObservation}}
