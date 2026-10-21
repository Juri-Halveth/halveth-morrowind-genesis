-- SPDX-License-Identifier: MIT
-- Native local world travel. Existing CELL records and original refs untouched.
local core=require('openmw.core')
local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')
local C=require('scripts.veyra_portal.config')
local state,player,fault=nil,nil,nil
local function valid(obj)return obj and obj:isValid()end
local function same(a,b)return valid(a)and valid(b)and a.id==b.id end
local function log(kind,detail)print('VEYRA_PORTAL|kind='..kind..'|'..(detail or ''))end
local function closeEnough(gate)
    return valid(player)and valid(gate)and player.cell and gate.cell
        and player.cell.id==gate.cell.id and (player.position-gate.position):length()<=C.range
end
local function status()
    if not state then return {phase=fault and fault.phase or 'UNPLACED',trips=0,gateCount=0,networkEffects=0}end
    local function coordinates(obj)
        return valid(obj)and {x=obj.position.x,y=obj.position.y,z=obj.position.z}or nil
    end
    return {phase=state.phase,trips=state.trips,moduleVersion=C.moduleVersion,gateCount=(valid(state.sourceGate)and 1 or 0)+(valid(state.frontierGate)and 1 or 0),
        sourceGateId=valid(state.sourceGate)and state.sourceGate.id or nil,
        frontierGateId=valid(state.frontierGate)and state.frontierGate.id or nil,
        sourceCellId=state.sourceCellId,frontierCellId=state.frontierCellId,
        sourcePosition=coordinates(state.sourceGate),frontierPosition=coordinates(state.frontierGate),
        nearSource=closeEnough(state.sourceGate)or false,nearFrontier=closeEnough(state.frontierGate)or false,
        returnPoint=state.returnPoint and {cellId=state.returnPoint.cellId,x=state.returnPoint.x,
            y=state.returnPoint.y,z=state.returnPoint.z,yaw=state.returnPoint.yaw}or nil,
        entryManifestSha256=C.entryManifestSha256,pluginSha256=C.pluginSha256,
        networkEffects=0,automaticTeleportOnLoad=false}
end
local function report()if valid(player)then player:sendEvent('VEYRA_PortalStatus',status())end end
local function notice(message)
    if valid(player)then player:sendEvent('VEYRA_PortalNotice',{message=message})end
end
local function boundCell(def)
    local cell=world.getExteriorCell(def.gridX,def.gridY,def.cellName)
    assert(cell and cell.isExterior and cell.name==def.cellName and cell.gridX==def.gridX and cell.gridY==def.gridY,
        'Portal cell does not match its bound entry')
    return cell
end
local function setup()
    local created={}
    local ok,result=pcall(function()
        local sourceCell,frontierCell=boundCell(C.source),boundCell(C.frontier)
        local gem=assert(types.Miscellaneous.records[C.modelRecordId],'Local Soulgem record unavailable')
        assert(gem.model and gem.model~='','Local Soulgem model reference unavailable')
        local record=world.createRecord(types.Activator.createRecordDraft({name='LEVIATH-Seelenstein',model=gem.model,mwscript=''}))
        local sourceGate=world.createObject(record.id);created[#created+1]=sourceGate
        local frontierGate=world.createObject(record.id);created[#created+1]=frontierGate
        sourceGate:setScale(C.modelScale);frontierGate:setScale(C.modelScale)
        sourceGate:teleport(sourceCell,util.vector3(C.source.x,C.source.y,C.source.z),{onGround=true})
        -- A stationary inactive-cell object keeps its supplied Z. Its stone
        -- uses the bound land height, while the arriving actor keeps the
        -- separately declared vertical safety margin.
        frontierGate:teleport(frontierCell,util.vector3(C.frontier.x+128,C.frontier.y,C.frontier.terrainHeight),{onGround=true})
        return {version=C.version,phase='SETTING_UP',sourceGate=sourceGate,frontierGate=frontierGate,
            sourceCellId=sourceCell.id,frontierCellId=frontierCell.id,trips=0,returnPoint=nil}
    end)
    if not ok then
        for _,obj in ipairs(created)do if valid(obj)then pcall(obj.remove,obj)end end
        fault={phase='INIT_HOLD',reason=tostring(result)};log('INIT_HOLD',tostring(result));return
    end
    state=result;log('PAIR_CREATED','count=2|entryDigest='..C.entryManifestSha256)
end
local function activate(object,actor)
    if not state or state.phase~='READY' or not same(actor,player)or not closeEnough(object)then return end
    local branch=same(object,state.sourceGate)and 'OUTBOUND' or same(object,state.frontierGate)and 'RETURN' or nil
    if not branch then return end
    if branch=='RETURN'and not state.returnPoint then
        notice('Dieser Seelenstein besitzt noch keinen gebundenen Rueckweg. Beginne deine Reise in Seyda Neen.');return
    end
    state.prompt={gateId=object.id,branch=branch}
    player:sendEvent('VEYRA_PortalOpen',{gateId=object.id,branch=branch,
        target=branch=='OUTBOUND'and C.frontier.cellName or 'dein gespeicherter Rueckkehrpunkt'})
    log('PROMPT_OPENED','branch='..branch);report()
end
local function confirm(data)
    if not state or state.phase~='READY' or type(data)~='table' or not same(data.player,player)
        or not state.prompt or data.gateId~=state.prompt.gateId or data.branch~=state.prompt.branch then return end
    local branch=state.prompt.branch
    local gate=branch=='OUTBOUND'and state.sourceGate or state.frontierGate
    if not closeEnough(gate)then state.prompt=nil;notice('Komm zuerst wieder zum Seelenstein.');report();return end
    local point
    if branch=='OUTBOUND'then
        state.returnPoint={cellId=player.cell.id,x=player.position.x,y=player.position.y,z=player.position.z,yaw=player.rotation:getYaw()}
        point={cellId=state.frontierCellId,x=C.frontier.x,y=C.frontier.y,z=C.frontier.z,yaw=C.frontier.yaw}
    else point=state.returnPoint end
    if not point then state.prompt=nil;return end
    -- Queue exactly one trip following the explicit local confirmation.
    -- An incomplete saved trip is observed or held on load, never replayed.
    state.pending={target=point,branch=branch,startedRealTime=core.getRealTime()}
    state.prompt=nil;state.phase='TRAVELLING'
    player:teleport(world.getCellById(point.cellId),util.vector3(point.x,point.y,point.z),
        {rotation=util.transform.rotateZ(point.yaw),onGround=true})
    log('TRAVEL_REQUESTED','branch='..branch);report()
end
local function update()
    if fault or not valid(player)then return end
    if not state then setup();return end
    if not valid(state.sourceGate)or not valid(state.frontierGate)then
        if state.phase~='REF_HOLD'then state.phase='REF_HOLD';log('REF_HOLD','noReplacementObjects=true');report()end
        return
    end
    if state.phase=='SETTING_UP'then
        if state.sourceGate.cell and state.frontierGate.cell and state.sourceGate.cell.id==state.sourceCellId
            and state.frontierGate.cell.id==state.frontierCellId then state.phase='READY';report()end
    elseif state.phase=='TRAVELLING'and state.pending then
        local target=state.pending.target
        local distance=(player.position-util.vector3(target.x,target.y,target.z)):length()
        if player.cell and player.cell.id==target.cellId and distance<=C.range+300 then
            state.trips=state.trips+1;state.phase='READY';state.pending=nil
            notice('Der Seelenstein hat dich getragen. Dein Rueckweg bleibt im Spielstand.');log('TRAVEL_OBSERVED','trips='..state.trips);report()
        elseif core.getRealTime()-state.pending.startedRealTime>C.travelTimeoutSeconds then
            state.phase='TRAVEL_HOLD';notice('Die Reise bleibt zur Pruefung angehalten. Es wird keine zweite Reise ausgeloest.')
            log('TRAVEL_HOLD','noAutomaticReplay=true');report()
        end
    end
end
local function load(data)
    state,player,fault=nil,nil,nil
    if data==nil then return end
    if type(data)=='table'and (data.phase=='LOAD_HOLD'or data.phase=='INIT_HOLD')then
        fault=data;log('LOAD_HOLD','existing hold retained');return
    end
    if type(data)~='table'or data.version~=C.version or not data.sourceGate or not data.frontierGate
        or type(data.sourceCellId)~='string'or type(data.frontierCellId)~='string'or type(data.trips)~='number'then
        fault={phase='LOAD_HOLD',savedData=data};log('LOAD_HOLD','savedData retained');return
    end
    state=data;state.prompt=nil
    if state.phase=='TRAVELLING'and state.pending then state.pending.startedRealTime=core.getRealTime()end
    log('LOAD','phase='..state.phase..'|automaticTeleport=false')
end
return {interfaceName='VeyraPortal',interface={version=C.version,status=status},
    engineHandlers={onPlayerAdded=function(p)player=p end,onUpdate=update,onActivate=activate,
        onSave=function()return fault or state end,onLoad=load,onNewGame=function()load(nil)end},
    eventHandlers={VEYRA_PortalConfirm=confirm,VEYRA_PortalStatusRequest=report,
        VEYRA_PortalCancel=function(data)if state and type(data)=='table'and same(data.player,player)then state.prompt=nil end end}}
