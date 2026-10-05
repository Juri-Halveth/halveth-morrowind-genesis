-- SPDX-License-Identifier: MIT
-- Player-local navmesh preflight. No teleport and no original actor mutation.
local core=require('openmw.core')
local self=require('openmw.self')
local nearby=require('openmw.nearby')
local types=require('openmw.types')
local ui=require('openmw.ui')
local I=require('openmw.interfaces')
local util=require('openmw.util')
local C=require('scripts.veyra_townlife.config')
local function plain(p)return{x=p.x,y=p.y,z=p.z}end
local function preflight()
    if core.isWorldPaused()or not self.cell or not self.cell.isExterior or self.cell.name~=C.entry.name then return end
    local positions={}
    local flags=nearby.NAVIGATOR_FLAGS.Walk+nearby.NAVIGATOR_FLAGS.OpenDoor
    local bounds=types.Actor.getPathfindingAgentBounds(self)
    for _,role in ipairs(C.roles)do
        local p=C.locations[role.home]
        local wanted=util.vector3(p.x,p.y,p.z)
        local point=nearby.findNearestNavMeshPosition(wanted,
            {agentBounds=bounds,includeFlags=flags,searchAreaHalfExtents=util.vector3(160,160,240)})
        if not point then return end
        local status=nearby.findPath(self.position,point,{agentBounds=bounds,includeFlags=flags,destinationTolerance=60})
        local ground=nearby.castRay(point+util.vector3(0,0,160),point-util.vector3(0,0,300),
            {collisionType=nearby.COLLISION_TYPE.World})
        if status~=nearby.FIND_PATH_STATUS.Success or not ground.hit then return end
        positions[role.id]=plain(point)
    end
    core.sendGlobalEvent('VEYRA_TownCreate',{player=self.object,positions=positions})
    print('VEYRA_TOWN|kind=PREFLIGHT|roles=3|sourceDestinationsProjected=true')
end
local layer='VeyraTownlife'
local presentationVersion='0.1.2'
local cached={created=false,roles={},phase='CONNECTING'}
local element,layout,labels,screenX,screenY,lastMode,lastVisible
local elapsed,lastRequest=1,-100
local lastRefreshAtGameTime
local ink=util.color.rgb(0.96,0.95,0.91)
local gold=util.color.rgb(0.90,0.77,0.48)
local roleLabels={garden='KERA / GARTENBESUCHER',trade='LIO / HANDELSBESUCHER',watch='SENN / WACHBESUCHER'}
local placeLabels={home_garden='Hauskante',home_trade='Hauskante',home_watch='Hauskante',
    water='Wasserecke',field='Wiesenplatz',market='Marktrand',approach='Zugang',
    lookout='Aussicht',arrival_gate='Ankunftstor'}
local phases={TRAVEL_REQUESTED='Wegauftrag gestellt',TRAVEL_STARTED='Reise begonnen',
    TRAVEL_PROGRESS='Unterwegs / gemessen',ARRIVED_OBSERVED='Ankunft beobachtet',
    AT_DESTINATION_POSITION_ONLY='Am Ziel / Position',WAIT_NAV='Weg wird gesucht',
    WAIT_ACTIVE='Zelle ruht',WAIT_DISABLED='Figur deaktiviert',WAIT_OWNER='Tagesplan pausiert',
    COMBAT_DEFERRED='Kampf / Reise wartet',STALLED='Weg stockt',DEAD_HOLD='Figur gestorben',
    POSITION_JUMP_HOLD='Positionssprung / Reise wartet',LOAD_HOLD='Spielstandpruefung offen',
    WAIT_AUTHORITY='Aktivierung wartet',REPLAN_PENDING='Weg wird neu gesucht',
    NAV_REQUEST_PENDING='Navigation wartet'}
local function destroy()
    if element then element:destroy()end
    element,layout,labels=nil,nil,nil
end
local function text(name,x,y,width,size,color)
    return {name=name,type=ui.TYPE.Text,props={position=util.vector2(x,y),
        size=util.vector2(width,size+6),autoSize=false,text='',textSize=size,textColor=color or ink,
        textShadow=true,textShadowColor=util.color.rgb(0,0,0)}}
end
local function build()
    destroy();local screen=ui.screenSize();screenX,screenY=screen.x,screen.y
    if not ui.layers.indexOf(layer)then ui.layers.insertAfter('HUD',layer,{interactive=false})end
    local width,height=398,244
    local texture=ui.texture{path='Textures/veyra_townlife/white.png'}
    labels={};local content={{name='background',type=ui.TYPE.Image,
        props={position=util.vector2(0,0),size=util.vector2(width,height),resource=texture,
            color=util.color.rgb(0.035,0.048,0.064),alpha=0.84}}}
    labels.title=text('title',14,10,width-28,14,gold);content[#content+1]=labels.title
    for index,role in ipairs(C.roles)do
        local y=40+(index-1)*65
        local lines={text(role.id..'_role',14,y,width-28,14,gold),
            text(role.id..'_goal',14,y+21,width-28,13),text(role.id..'_state',14,y+40,width-28,13)}
        labels[role.id]=lines;for _,line in ipairs(lines)do content[#content+1]=line end
    end
    layout={name='VeyraTownPanel',type=ui.TYPE.Widget,layer=layer,
        props={position=util.vector2(460,28),size=util.vector2(width,height),visible=false},content=ui.content(content)}
    element=ui.create(layout)
end
local function refresh()
    local screen=ui.screenSize()
    if not element or screen.x~=screenX or screen.y~=screenY then build()end
    local visible=cached.created==true and self.cell and self.cell.isExterior
        and self.cell.name==C.entry.name and I.UI.isHudVisible()and I.UI.getMode()==nil
    layout.props.visible=visible and true or false
    if visible then
        labels.title.props.text=string.format('LEVIATH / TAG %d / %02d:%02d',
            cached.gameDayIndex or 0,cached.gameHour or 0,cached.gameMinute or 0)
        for _,role in ipairs(C.roles)do
            local row=cached.roles[role.id]or{};local line=labels[role.id]
            line[1].props.text=roleLabels[role.id]
            line[2].props.text=(row.daySlot or'--:--')..'  >  '..(placeLabels[row.goal or row.scheduledPlace]or'Aktivierung')
            local measured=row.measuredDistance and string.format(' / %.0f Weg',row.measuredDistance)or''
            line[3].props.text=(phases[row.phase]or'Aktivierung wartet')..measured
        end
    end
    element:update()
    lastRefreshAtGameTime=core.getGameTime()
end
local function frame(dt)
    local now=core.getSimulationTime()
    if now-lastRequest>=C.sampleSeconds then
        lastRequest=now;core.sendGlobalEvent('VEYRA_TownStatusRequest',{player=self.object})
    end
    local mode,visible=I.UI.getMode(),I.UI.isHudVisible()
    local changed=mode~=lastMode or visible~=lastVisible
    lastMode,lastVisible=mode,visible;elapsed=elapsed+dt
    if elapsed<0.25 and not changed then return end;elapsed=0
    refresh()
end
return {interfaceName='VeyraTownPanel',interface={version=1,getState=function()
        local roles={};for id,row in pairs(cached.roles)do
            local lines=labels and labels[id]
            roles[id]={phase=row.phase,goal=row.goal,daySlot=row.daySlot,measuredDistance=row.measuredDistance,
                displayedRole=lines and lines[1].props.text,displayedGoal=lines and lines[2].props.text,
                displayedState=lines and lines[3].props.text}
        end
    local index=ui.layers.indexOf(layer)
    local layerSize=index and ui.layers[index].size
    return{visible=layout and layout.props.visible or false,roles=roles,
            presentationVersion=presentationVersion,panelAnchor='FIXED_ADJACENT',
            layerWidth=layerSize and layerSize.x,layerHeight=layerSize and layerSize.y,
            gameDayIndex=cached.gameDayIndex,lastReadAtGameTime=cached.lastReadAtGameTime,
            displayedTitle=labels and labels.title.props.text or nil,screenX=screenX,screenY=screenY,
            lastRefreshAtGameTime=lastRefreshAtGameTime}
    end},engineHandlers={onFrame=frame,onLoad=function()
        cached={created=false,roles={},phase='CONNECTING'};lastRequest=-100;elapsed=1;destroy()
    end},eventHandlers={VEYRA_TownPreflight=preflight,VEYRA_TownStatus=function(data)
        if type(data)=='table'and type(data.roles)=='table'then cached=data;elapsed=1 end
    end}}
