-- SPDX-License-Identifier: MIT
local core=require('openmw.core')
local self=require('openmw.self')
local input=require('openmw.input')
local nearby=require('openmw.nearby')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local cached={phase='CONNECTING',saltrice=0,comberry=0}
local window,body,footer,mode,addedMode=nil,nil,nil,nil,false
local lastStatus=-100
local close,refresh,open
local function request(action,extra)
    local data={player=self.object,action=action}
    if extra then for k,v in pairs(extra)do data[k]=v end end
    core.sendGlobalEvent('VEYRA_FieldworkAction',data)
end
local function place()
    if not self.cell or not self.cell.isExterior then ui.showMessage('Deine Feldwerkstatt braucht einen Aussenplatz.');return false end
    local points={}
    for _,offset in ipairs({util.vector3(-130,240,0),util.vector3(130,240,0)})do
        local center=self.position+self.rotation:apply(offset)
        local ray=nearby.castRay(center+util.vector3(0,0,180),center-util.vector3(0,0,500),
            {collisionType=nearby.COLLISION_TYPE.World+nearby.COLLISION_TYPE.HeightMap})
        if not ray.hit or not ray.hitPos or not ray.hitNormal or ray.hitNormal.z<.6 then
            ui.showMessage('Hier fehlt trockener, ebener Boden fuer Beet und Bank.');return false
        end
        points[#points+1]=ray.hitPos
    end
    request('PLACE',{cellId=self.cell.id,plotPosition=points[1],benchPosition=points[2]})
    return true
end
close=function()
    if window then window:destroy();window=nil end
    body,footer=nil,nil
    if I.VeyraPanelCoordinator then I.VeyraPanelCoordinator.release('VeyraFieldworkPlayer') end
    addedMode=false
end
local function button(label,x,y,w,handler)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,32),text=label,textSize=17},
        events={mouseClick=async:callback(handler)}}
end
local function detail()
    local phase=({UNPLACED='Noch keine Feldwerkstatt',EMPTY='Beet und Bank bereit',INPUT_PENDING='Zutaten werden eingelagert',
        WORKING='Wachstum / Verarbeitung',READY='Bereit zur Abholung',OUTPUT_PENDING='Ertrag wird uebergeben',
        CONSUMING='Zutatenverbrauch wird abgeschlossen',DONE='Auftrag abgeschlossen',LOAD_HOLD='Spielstand zur Pruefung gehalten'})[cached.phase]or cached.phase
    local lines={phase,'DEINE ZUTATEN\nSaltrice: '..tostring(cached.saltrice or 0)..'    Comberry: '..tostring(cached.comberry or 0),
        'BEET\n2 Saltrice als Saat → 4 Saltrice nach 24 Spielstunden.',
        'FELDWERKBANK\n2 Saltrice + 1 Comberry → 1 Feldration nach 6 Spielstunden.\nFeldration: Ausdauer wiederherstellen, 2 Punkte / Sekunde fuer 15 Sekunden.',
        'Setze die Werkstatt vor dir auf trockenen Boden. Saeen, Ansetzen und Abholen funktionieren bei deiner Werkstatt.\nAnfangszutaten sammelst oder kaufst du im normalen Spiel.'}
    if cached.remainingHours and cached.phase=='WORKING'then lines[#lines+1]=string.format('Noch %.1f Spielstunden · %s',cached.remainingHours,cached.kind=='FARM'and 'Beet' or 'Bank')end
    lines[#lines+1]='Abgeschlossene Ernten: '..tostring(cached.cropHarvests or 0)..'    Feldrationen: '..tostring(cached.rationsMade or 0)
    return table.concat(lines,'\n\n')
end
refresh=function()
    if body then body.props.text=detail()end
    if footer then footer.props.text=cached.placed and 'Dein Standort: '..(cached.nearPlot and 'beim Beet' or cached.nearBench and 'bei der Bank' or 'unterwegs')or 'F4 oeffnet und schliesst deine Feldwerkstatt.'end
    if window then window:update()end
end
open=function()
    if window then close();return end
    for _,name in ipairs({'HALVETHFieldcraft','HALVETHWorldlife','HALVETHKnowledge','HALVETHUniverse','HALVETHPaths'})do
        if I[name]and I[name].close then I[name].close()end
    end
    mode=assert(I.VeyraPanelCoordinator,'Panel coordinator is required').acquire('VeyraFieldworkPlayer')
    -- Interface mode ownership belongs to VeyraPanelCoordinator.
    local screen=ui.screenSize();local w,h=math.min(930,screen.x-30),math.min(630,screen.y-30)
    local content={{type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
        props={position=util.vector2(20,16),text='LEVIATH / FELDWERKSTATT',textSize=22}}}
    body={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(20,58),size=util.vector2(w-40,h-165),readOnly=true,multiline=true,wordWrap=true,text='',textSize=17}}
    footer={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(20,h-96),size=util.vector2(w-40,32),text='',textSize=15}}
    content[#content+1]=body;content[#content+1]=footer
    local actions={{'[Setzen]',place},{'[Saeen]',function()request('PLANT')end},{'[Ansetzen]',function()request('CRAFT')end},
        {'[Abholen]',function()request('HARVEST')end},
        {'[Sammelatlas]',function()close();if I.HALVETHFieldcraft then I.HALVETHFieldcraft.open()end end},
        {'[Schliessen]',close}}
    local slot=math.floor((w-40)/#actions)
    for i,a in ipairs(actions)do content[#content+1]=button(a[1],20+(i-1)*slot,h-50,slot-4,a[2])end
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},content=ui.content(content)}
    core.sendGlobalEvent('VEYRA_FieldworkStatusRequest',{});refresh()
end
return {interfaceName='VeyraFieldworkPlayer',interface={version=1,open=open,close=close,
        isOpen=function()return window~=nil end,place=place,
        plant=function()request('PLANT')end,craft=function()request('CRAFT')end,harvest=function()request('HARVEST')end,
        getState=function()local copy={};for k,v in pairs(cached)do copy[k]=v end;return copy end},
    engineHandlers={onLoad=function()close();cached={phase='CONNECTING',saltrice=0,comberry=0};lastStatus=-100 end,
        onKeyPress=function(key)if key.code==input.KEY.F4 then open()end end,
        onFrame=function()
            if window and I.UI.getMode()~=mode then close()end
            local now=core.getRealTime()
            if self.cell and now-lastStatus>.5 then lastStatus=now;core.sendGlobalEvent('VEYRA_FieldworkStatusRequest',{})end
        end},eventHandlers={VEYRA_FieldworkOpen=open,VEYRA_FieldworkStatus=function(data)cached=data;refresh()end,
        VEYRA_FieldworkNotice=function(data)
            ui.showMessage(data.message)
            if data.kind=='DONE'and I.HALVETHFieldcraft then I.HALVETHFieldcraft.refresh()end
            print('FIELDWORK|kind=PLAYER_NOTICE|'..tostring(data.kind))
        end}}
