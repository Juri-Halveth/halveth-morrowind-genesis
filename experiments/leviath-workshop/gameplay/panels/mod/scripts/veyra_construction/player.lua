-- SPDX-License-Identifier: MIT
local core=require('openmw.core')
local self=require('openmw.self')
local input=require('openmw.input')
local nearby=require('openmw.nearby')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local C=require('scripts.veyra_construction.config')
local cached={phase='CONNECTING',plots={},metal=0,rice=0,plotCount=0}
local selectedId,window,body,footer,mode,addedMode=nil,nil,nil,nil,nil,false
local lastStatus=-100
local open,close,refresh
local function request(action,extra)
    local data={player=self.object,action=action,plotId=selectedId}
    if extra then for k,v in pairs(extra)do data[k]=v end end
    core.sendGlobalEvent('VEYRA_ConstructionAction',data)
end
local function selected()
    for _,plot in ipairs(cached.plots or{})do if plot.id==selectedId then return plot end end
end
local function build()
    if not self.cell or not self.cell.isExterior then ui.showMessage('Dein Beet braucht einen freien Aussenplatz in der Frontier.');return false end
    local centre=self.position+self.rotation:apply(util.vector3(0,200,0))
    local checks,points={},{}
    local mask=nearby.COLLISION_TYPE.World+nearby.COLLISION_TYPE.HeightMap
    for _,offset in ipairs({util.vector3(0,0,0),util.vector3(-62,-92,0),util.vector3(62,-92,0),
        util.vector3(62,92,0),util.vector3(-62,92,0)})do
        local p=centre+self.rotation:apply(offset)
        local ray=nearby.castRay(p+util.vector3(0,0,160),p-util.vector3(0,0,350),{collisionType=mask})
        if not ray.hit or not ray.hitPos or not ray.hitNormal or ray.hitNormal.z<.92 then
            ui.showMessage('Fuenf ebene Bodenpunkte sind hier nicht frei.');return false
        end
        points[#points+1]=ray.hitPos;checks[#checks+1]={height=ray.hitPos.z,normalZ=ray.hitNormal.z}
    end
    for _,point in ipairs(points)do
        if math.abs(point.z-points[1].z)>12 then ui.showMessage('Der Boden ist fuer dieses Beet zu uneben.');return false end
        local head=nearby.castRay(point+util.vector3(0,0,15),point+util.vector3(0,0,160),{collisionType=nearby.COLLISION_TYPE.World})
        if head.hit then ui.showMessage('Ueber dem Beet fehlt freier Raum.');return false end
    end
    -- Check the reachable line above the ground for intervening architecture.
    local line=nearby.castRay(self.position+util.vector3(0,0,50),points[1]+util.vector3(0,0,50),
        {collisionType=nearby.COLLISION_TYPE.World,ignore=self.object})
    if line.hit then ui.showMessage('Zwischen dir und dem Beet steht ein Hindernis.');return false end
    request('BUILD',{position=points[1],yaw=self.rotation:getYaw(),cellId=self.cell.id,
        groundChecks=checks,headroomClear=true});return true
end
close=function()
    if window then window:destroy();window=nil end;body,footer=nil,nil
    if I.VeyraPanelCoordinator then I.VeyraPanelCoordinator.release('VeyraConstructionPlayer') end;addedMode=false
end
local function detail()
    local lines={'PFLANZBEET BAUEN\n2 echte Scrap-Metal bilden den Rahmen.\nFreie, ebene Flaeche vor dir in der LEVIATH-Frontier.',
        'DEIN INVENTAR\nScrap-Metal: '..tostring(cached.metal or 0)..'    Saltrice: '..tostring(cached.rice or 0),
        'EIGENE BEETE\n'..tostring(cached.plotCount or 0)..' / 32 · Ernten: '..tostring(cached.harvests or 0)..' · Rueckbauten: '..tostring(cached.dismantles or 0),
        'SAAT UND ERTRAG\n2 eigene Saltrice einsetzen, 24 Spielstunden wachsen lassen,\neinmal 4 Saltrice am Beet ernten. Danach neue Saat einsetzen.',
        'RUECKBAU\nVorhandene Rahmen und unverbrauchte Saat kommen zurueck.\nBereits geerntete Saat ist verbraucht.'}
    local plot=selected()
    if plot then
        local phase=({EMPTY='Leeres Beet',GROWING='Saat waechst',RIPE='Reif zur Ernte'})[plot.phase]or plot.phase
        lines[#lines+1]='AUSGEWAEHLTES BEET\n'..phase..' · '..(plot.near and 'in Reichweite'or 'zu weit entfernt')
        if plot.phase=='GROWING'and plot.remainingHours then lines[#lines+1]=string.format('Noch %.1f Spielstunden.',plot.remainingHours)end
    else lines[#lines+1]='Aktiviere dein eigenes Beet, um es auszuwaehlen.'end
    if cached.phase~='READY'then lines[#lines+1]='Materialvorgang: '..tostring(cached.phase)end
    return table.concat(lines,'\n\n')
end
refresh=function()
    if body then body.props.text=detail()end
    if footer then footer.props.text=cached.inFrontier and 'Du bist in der Frontier. Boden und Abstand werden beim Bau geprueft.'or 'Reise zuerst durch deinen Seelenstein in die Frontier.'end
    if window then window:update()end
end
local function button(label,x,y,w,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,32),text=label,textSize=17},events={mouseClick=async:callback(fn)}}
end
open=function(data)
    close();if type(data)=='table'and data.plotId then selectedId=data.plotId end
    for _,name in ipairs({'HALVETHFieldcraft','HALVETHWorldlife','HALVETHKnowledge','HALVETHUniverse','HALVETHPaths',
        'VeyraFieldworkPlayer','VeyraPortalPlayer','VeyraCourierPlayer'})do if I[name]and I[name].close then I[name].close()end end
    mode=assert(I.VeyraPanelCoordinator,'Panel coordinator is required').acquire('VeyraConstructionPlayer')
    -- Interface mode ownership belongs to VeyraPanelCoordinator.
    local screen=ui.screenSize();local w,h=math.min(930,screen.x-30),math.min(710,screen.y-30)
    local content={{type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
        props={position=util.vector2(20,16),text='LEVIATH / BEETBAU',textSize=22}}}
    body={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(20,58),size=util.vector2(w-40,h-165),readOnly=true,multiline=true,wordWrap=true,text='',textSize=17}}
    footer={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(20,h-96),size=util.vector2(w-40,32),text='',textSize=15}}
    content[#content+1]=body;content[#content+1]=footer
    local actions={{'[Bauen]',build},{'[Saeen]',function()request('PLANT')end},
        {'[Ernten]',function()request('HARVEST')end},{'[Rueckbau]',function()request('DISMANTLE')end},{'[Schliessen / F3]',close}}
    local slot=math.floor((w-40)/#actions)
    for i,a in ipairs(actions)do content[#content+1]=button(a[1],20+(i-1)*slot,h-50,slot-4,a[2])end
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},content=ui.content(content)}
    core.sendGlobalEvent('VEYRA_ConstructionStatusRequest',{});refresh()
end
return {interfaceName='VeyraConstructionPlayer',interface={version=C.version,open=open,close=close,build=build,
        plant=function()request('PLANT')end,harvest=function()request('HARVEST')end,dismantle=function()request('DISMANTLE')end,
        getState=function()return {promptOpen=window~=nil,selectedId=selectedId,cached=cached}end},
    engineHandlers={onLoad=function()close();selectedId=nil;cached={phase='CONNECTING',plots={}};lastStatus=-100 end,
        onKeyPress=function(key)if key.code==input.KEY.F3 then if window then close()else open()end end end,
        onFrame=function()
            if window and I.UI.getMode()~=mode then close()end
            local now=core.getRealTime()
            if self.cell and now-lastStatus>.5 then lastStatus=now;core.sendGlobalEvent('VEYRA_ConstructionStatusRequest',{})end
        end},eventHandlers={VEYRA_ConstructionOpen=open,VEYRA_ConstructionStatus=function(data)
            cached=data;if not selected()then selectedId=data.nearestId end;refresh()
        end,VEYRA_ConstructionNotice=function(data)ui.showMessage(data.message)end,
        VEYRA_ConstructionRemovalProbe=function(data)
            local clear=false
            if self.cell and(data.position-self.position):length()<=C.range then
                local ray=nearby.castRay(data.position+util.vector3(0,0,80),data.position-util.vector3(0,0,2),
                    {collisionType=nearby.COLLISION_TYPE.World})
                clear=not ray.hit or(ray.hitObject~=nil and ray.hitObject.id~=data.plotId)
            end
            core.sendGlobalEvent('VEYRA_ConstructionRemovalObservation',{player=self.object,plotId=data.plotId,
                sequence=data.sequence,clear=clear})
        end}}
