-- Player-centred camera controls and a bounded view of the loaded Morrowind scene.
local core=require('openmw.core')
local self=require('openmw.self')
local nearby=require('openmw.nearby')
local types=require('openmw.types')
local camera=require('openmw.camera')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')

local window,detail,summary,mode,addedMode=nil,nil,nil,nil,false
local baseline,lastRefresh=nil,-100
local message='Deine Figur bleibt in der echten Morrowind-Welt. Drehe die Kamera oder waehle die Sicht.'
local refresh

local function label(value)
    if value==camera.MODE.FirstPerson then return 'Ich-Sicht' end
    if value==camera.MODE.ThirdPerson then return 'Aussen-Sicht' end
    if value==camera.MODE.Preview then return 'Freier Blick' end
    if value==camera.MODE.Vanity then return 'Umlaufende Kamera' end
    return 'Sonderansicht'
end

local function viewState()
    local current=camera.getMode()
    local result={version=1,mode=label(current),yawDegrees=math.floor(math.deg(camera.getYaw())+.5),
        pitchDegrees=math.floor(math.deg(camera.getPitch())+.5),
        cell=self.cell and self.cell.name or '',inFrame=C.array(),
        scope='LOADED_ACTORS_IN_VIEWPORT_PROJECTION',lineOfSightChecked=false}
    if I.Camera then
        local ok,distance=pcall(I.Camera.getBaseThirdPersonDistance)
        if ok and type(distance)=='number' then result.thirdPersonDistance=math.floor(distance+.5) end
    end
    if not self.cell then return result end
    local candidates={}
    for _,actor in ipairs(nearby.actors) do
        if actor.id~=self.id and actor:isValid() and not types.Actor.isDead(actor) then
            local distance=(actor.position-self.position):length()
            if distance<=2400 then
                local ok,projection=pcall(camera.worldToViewportVector,actor.position+util.vector3(0,0,100))
                if ok and projection and projection.z>0 and projection.x>=0 and projection.x<=1
                    and projection.y>=0 and projection.y<=1 then
                    local record=actor.type.record(actor)
                    candidates[#candidates+1]={name=C.head(record.name or actor.recordId,80),
                        recordId=actor.recordId,distance=math.floor(distance+.5)}
                end
            end
        end
    end
    table.sort(candidates,function(a,b)
        if a.distance==b.distance then return a.name<b.name end
        return a.distance<b.distance
    end)
    for index=1,math.min(#candidates,6) do result.inFrame[#result.inFrame+1]=candidates[index] end
    return result
end

local function close()
    if window then window:destroy();window=nil end
    detail=nil;summary=nil
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    mode=nil
end

refresh=function()
    if not window then return end
    local state=viewState()
    local lines={
        'PERSPEKTIVE / '..state.mode,
        'Ort: '..(state.cell~='' and state.cell or 'Welt wird geladen'),
        'Drehung: '..state.yawDegrees..' Grad  |  Neigung: '..state.pitchDegrees..' Grad',
        'Abstand aussen: '..(state.thirdPersonDistance or '?')..' Spieleinheiten',
        '',
        'FIGUREN IM AKTUELLEN BILDAUSSCHNITT',
    }
    if #state.inFrame==0 then lines[#lines+1]='Gerade keine geladene Figur im Bildausschnitt.' end
    for _,person in ipairs(state.inFrame) do
        lines[#lines+1]='- '..person.name..'  ·  etwa '..person.distance..' Einheiten'
    end
    lines[#lines+1]=''
    lines[#lines+1]='Diese Liste nutzt die Kameraprojektion; verdeckte Figuren koennen darin stehen.'
    lines[#lines+1]='Mausbewegung und normale Morrowind-Steuerung bleiben erhalten.'
    detail.props.text=table.concat(lines,'\n')
    summary.props.text=message
    window:update()
end

local function setView(name)
    local modes={first=camera.MODE.FirstPerson,third=camera.MODE.ThirdPerson,look=camera.MODE.Preview}
    if not modes[name] then return false end
    camera.setMode(modes[name],true)
    message=name=='first' and 'Ich-Sicht gewaehlt.' or name=='third' and 'Aussen-Sicht gewaehlt.'
        or 'Freier Blick: Kamera drehen, ohne die Figur mitzudrehen.'
    refresh();return true
end

local function turn(degrees)
    if type(degrees)~='number' or degrees~=degrees or degrees<-30 or degrees>30 then return false end
    camera.setYaw(camera.getYaw()+math.rad(degrees))
    message='Blick um '..math.abs(degrees)..' Grad '..(degrees<0 and 'nach links' or 'nach rechts')..' gedreht.'
    refresh();return true
end

local function zoom(delta)
    if (delta~=-60 and delta~=60) or not I.Camera then return false end
    local ok,current=pcall(I.Camera.getBaseThirdPersonDistance)
    if not ok or type(current)~='number' then return false end
    if camera.getMode()==camera.MODE.FirstPerson then camera.setMode(camera.MODE.ThirdPerson,true) end
    local nextDistance=math.max(120,math.min(700,current+delta))
    I.Camera.setBaseThirdPersonDistance(nextDistance)
    message='Aussenkamera: '..math.floor(nextDistance+.5)..' Spieleinheiten Abstand.'
    refresh();return true
end

local function reset()
    if not baseline then return false end
    camera.setMode(baseline.mode,true)
    if baseline.distance and I.Camera then I.Camera.setBaseThirdPersonDistance(baseline.distance) end
    message='Kamera auf die Ansicht vor Oeffnen dieses Fensters zurueckgesetzt.'
    refresh();return true
end

local function button(text,x,y,width,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(width,30),text=text,textSize=15},
        events={mouseClick=async:callback(fn)}}
end

local function open()
    if window then close();return end
    if I.HALVETH then I.HALVETH.close() end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    if I.HALVETHFieldcraft then I.HALVETHFieldcraft.close() end
    if I.HALVETHWorldlife then I.HALVETHWorldlife.close() end
    baseline={mode=camera.getMode()}
    if I.Camera then
        local ok,distance=pcall(I.Camera.getBaseThirdPersonDistance)
        if ok and type(distance)=='number' then baseline.distance=distance end
    end
    mode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    local screen=ui.screenSize()
    local w,h=math.min(800,screen.x-24),math.min(540,screen.y-24)
    local gap=8
    local slot=math.floor((w-36-3*gap)/4)
    local controls={
        {'[Ich-Sicht]',function()setView('first')end},
        {'[Aussen-Sicht]',function()setView('third')end},
        {'[Freier Blick]',function()setView('look')end},
        {'[Zuruecksetzen]',reset},
        {'[Links 15]',function()turn(-15)end},
        {'[Rechts 15]',function()turn(15)end},
        {'[Naeher]',function()zoom(-60)end},
        {'[Weiter weg]',function()zoom(60)end},
    }
    local content={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
            props={position=util.vector2(18,15),text='HALVETH / SICHT UM DEINE FIGUR',textSize=22}},
    }
    detail={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(18,52),size=util.vector2(w-36,h-204),text='',
            textSize=17,readOnly=true,multiline=true,wordWrap=true}}
    content[#content+1]=detail
    for index,control in ipairs(controls) do
        local column=(index-1)%4
        local row=math.floor((index-1)/4)
        content[#content+1]=button(control[1],18+column*(slot+gap),h-143+row*38,slot,control[2])
    end
    summary={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(18,h-62),size=util.vector2(w-170,48),text='',textSize=14,wordWrap=true}}
    content[#content+1]=summary
    content[#content+1]=button('[Schliessen]',w-150,h-46,132,close)
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},
        content=ui.content(content)}
    refresh()
end

return {interfaceName='HALVETHPerspective',
    interface={version=1,open=open,close=close,isOpen=function()return window~=nil end,
        getState=viewState,setView=setView,turn=turn,zoom=zoom,reset=reset},
    engineHandlers={onLoad=function()close();baseline=nil end,
        onFrame=function()
            if window and I.UI.getMode()~=mode then close() end
            if window and core.getRealTime()-lastRefresh>0.8 then
                lastRefresh=core.getRealTime();refresh()
            end
        end}}
