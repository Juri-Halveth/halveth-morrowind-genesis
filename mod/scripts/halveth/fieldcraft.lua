-- A native field guide for loose ingredients in the currently loaded world.
-- Only observations are saved. Gathering remains the ordinary Morrowind action.
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')

local MAX_RANGE,MAX_SIGHTINGS=3000,256
local entries,sightings={},{}
local selected,tracked=nil,nil
local window,detail,footer,rows,hud,hudText,addedMode,mode=nil,nil,nil,{},nil,nil,false,nil
local retainedInvalidSave,lastUpdate=nil,0
local message='Suche nach losen Zutaten in deiner geladenen Umgebung.'
local refresh,close

local function validText(value)
    return type(value)=='string' and #value>0 and #value<=256 and not value:find('[%z\1-\31]')
end

local function cellKey(cell)
    if not cell then return nil end
    if cell.isExterior then
        return tostring(cell.worldSpaceId or cell.id)..':'..tostring(cell.gridX)..':'..tostring(cell.gridY)
    end
    return cell.id
end

local function cellTitle()
    return self.cell and C.head(self.cell.displayName or self.cell.name or cellKey(self.cell),120) or 'Unbekannter Ort'
end

local function direction(object)
    local dx,dy=object.position.x-self.position.x,object.position.y-self.position.y
    if math.abs(dx)<40 and math.abs(dy)<40 then return 'direkt hier' end
    local horizontal=math.abs(dx)>120 and (dx>0 and 'Ost' or 'West') or ''
    local vertical=math.abs(dy)>120 and (dy>0 and 'Nord' or 'Sued') or ''
    return vertical..horizontal~='' and vertical..horizontal or 'direkt hier'
end

local function live(entry)
    return entry and entry.object and entry.object:isValid() and entry.object.cell~=nil
        and types.Ingredient.objectIsInstance(entry.object)
        and (entry.object.position-self.position):length()<=MAX_RANGE
end

local function gatherNearby()
    local list={}
    if not self.cell then return list end
    for _,object in ipairs(nearby.items) do
        if object:isValid() and object.cell~=nil and types.Ingredient.objectIsInstance(object) then
            local distance=(object.position-self.position):length()
            if distance<=MAX_RANGE then
                local record=types.Ingredient.record(object)
                list[#list+1]={id=tostring(object.id),recordId=record.id,name=C.head(record.name or record.id,120),
                    distance=distance,object=object}
            end
        end
    end
    table.sort(list,function(a,b)
        if a.distance==b.distance then return a.id<b.id end
        return a.distance<b.distance
    end)
    while #list>64 do table.remove(list) end
    return list
end

local function chosen()
    for _,entry in ipairs(entries) do if entry.id==selected then return entry end end
end

local function trackedEntry()
    for _,entry in ipairs(entries) do if entry.id==tracked then return entry end end
end

local function orderedSightings()
    local list=C.array()
    for _,s in pairs(sightings) do list[#list+1]={recordId=s.recordId,name=s.name,cell=s.cell,place=s.place} end
    table.sort(list,function(a,b)
        if a.place==b.place then return a.recordId<b.recordId end
        return a.place<b.place
    end)
    return list
end

local function snapshot()
    local found=C.array()
    for _,e in ipairs(entries) do found[#found+1]={id=e.id,recordId=e.recordId,name=e.name,
        distance=math.floor(e.distance),direction=live(e) and direction(e.object) or 'nicht mehr sichtbar'} end
    return {version=1,nearby=found,sightings=orderedSightings(),selected=selected,tracked=tracked,
        panelOpen=window~=nil,trackerOpen=hud~=nil,message=message,detail=detail and detail.props.text or ''}
end

local function feedback(text)
    message=text
    if footer then footer.props.text=text end
    if window then window:update() end
end

local function historyText()
    local history=orderedSightings()
    local lines={'DEIN SAMMELATLAS',#entries..' lose Zutaten in Reichweite (maximal 64 angezeigt).',
        #history..' eigene Ortssichtungen gespeichert (maximal 256).'}
    local e=chosen()
    if e and live(e) then
        lines[#lines+1]=string.format('AUSGEWAEHLT\n%s\n%.0f Welteinheiten · %s',e.name,e.distance,direction(e.object))
        lines[#lines+1]='[Ort notieren] speichert diese Zutatenart an diesem Ort. [Verfolgen] zeigt einen Hinweis im normalen Spielbild.'
    else
        lines[#lines+1]='Waehle links eine lose Zutat. Pflanzen, Kisten und fremde Inventare werden nicht durchsucht.'
    end
    lines[#lines+1]='LETZTE ORTSSICHTUNGEN'
    for i=math.max(1,#history-7),#history do
        local s=history[i];lines[#lines+1]=s.name..' · '..s.place
    end
    lines[#lines+1]='Die Richtung ist Luftlinie in Weltkoordinaten; Waende und Wege werden nicht berechnet. Aufheben bleibt deine normale Spielaktion.'
    return table.concat(lines,'\n\n')
end

refresh=function()
    entries=gatherNearby()
    if not chosen() then selected=entries[1] and entries[1].id or nil end
    if tracked and not trackedEntry() then tracked=nil end
    if detail then detail.props.text=historyText() end
    for i,row in ipairs(rows) do
        local e=entries[i]
        row.props.text=e and string.format('%s%s · %.0f',e.id==selected and '> ' or '  ',e.name,e.distance) or ''
    end
    if footer then footer.props.text=message end
    if window then window:update() end
end

local function select(id)
    for _,e in ipairs(entries) do
        if e.id==id and live(e) then selected=id;refresh();return true end
    end
    return false
end

local function survey()
    if retainedInvalidSave then feedback('Alter Atlasstand ist inkompatibel und bleibt unveraendert im Save.');return false end
    local e=chosen()
    if not live(e) then feedback('Die Zutat ist hier nicht mehr sichtbar.');return false end
    local cell=cellKey(self.cell)
    if not validText(cell) or not validText(e.recordId) then return false end
    local key=e.recordId..'\0'..cell
    if sightings[key] then feedback(e.name..' ist an diesem Ort bereits notiert.');return false end
    if #orderedSightings()>=MAX_SIGHTINGS then feedback('Der Atlas ist voll; vorhandene Orte bleiben erhalten.');return false end
    sightings[key]={recordId=e.recordId,name=e.name,cell=cell,place=cellTitle()}
    feedback(e.name..' in '..cellTitle()..' notiert.')
    refresh();return true
end

local function clearHud()
    if hud then hud:destroy();hud=nil;hudText=nil end
end

local function setTracked(id)
    if id==nil then tracked=nil;clearHud();feedback('Sammelziel entfernt.');return true end
    if not select(id) then feedback('Dieses Sammelziel ist nicht mehr sichtbar.');return false end
    tracked=id
    feedback(chosen().name..' als Sammelziel markiert. Schliessen und in der Welt aufsammeln.')
    return true
end

local function updateHud()
    if not tracked then clearHud();return end
    local e=trackedEntry()
    if not live(e) then tracked=nil;clearHud();feedback('Sammelziel ist nicht mehr in Reichweite.');return end
    local label=string.format('HALVETH / SAMMELZIEL   %s   %.0f · %s',e.name,e.distance,direction(e.object))
    if not hud then
        hudText={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(12,7),text=label,textSize=17}}
        hud=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='HUD',
            props={relativePosition=util.vector2(.5,0),position=util.vector2(0,55),anchor=util.vector2(.5,0),
                size=util.vector2(math.min(700,ui.screenSize().x-24),36)},content=ui.content{hudText}}
    else hudText.props.text=label;hud:update() end
end

close=function()
    if window then window:destroy();window=nil end
    detail=nil;footer=nil;rows={}
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    mode=nil
end

local function button(label,x,y,width,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(width,30),text=label,textSize=17},
        events={mouseClick=async:callback(fn)}}
end

local function open()
    if window then close();return end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    if I.HALVETH then I.HALVETH.close() end
    mode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    local screen=ui.screenSize()
    local w,h=math.min(1070,screen.x-24),math.min(700,screen.y-24)
    local body=h-200
    detail={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(430,82),size=util.vector2(w-450,body),text='',textSize=17,
            readOnly=true,multiline=true,wordWrap=true}}
    footer={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(18,h-110),size=util.vector2(w-36,44),text=message,textSize=15,wordWrap=true}}
    local content={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
            props={position=util.vector2(18,14),text='HALVETH / MORROWIND / SAMMELATLAS',textSize=22}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(18,45),text='Echte Zutaten sehen · Ort merken · in der Welt verfolgen',textSize=16}},
        detail,footer,
    }
    rows={}
    for i=1,math.max(4,math.min(12,math.floor((body-4)/38))) do
        local index=i
        local row=button('',22,82+(i-1)*38,395,function()
            local e=entries[index];if e then select(e.id) end
        end)
        rows[#rows+1]=row;content[#content+1]=row
    end
    content[#content+1]=button('[Ort notieren]',18,h-58,165,survey)
    content[#content+1]=button('[Verfolgen]',190,h-58,145,function()
        local e=chosen();if e then setTracked(e.id);close() end
    end)
    content[#content+1]=button('[Ziel entfernen]',344,h-58,170,function()setTracked(nil)end)
    content[#content+1]=button('[Aktualisieren]',w-332,h-58,155,refresh)
    content[#content+1]=button('[Schliessen]',w-165,h-58,145,close)
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},
        content=ui.content(content)}
    refresh()
end

local function decode(data)
    if type(data)~='table' or data.version~=1 or type(data.sightings)~='table' or #data.sightings>MAX_SIGHTINGS then return nil end
    local count=0
    for k in pairs(data.sightings) do
        if type(k)~='number' or k%1~=0 or k<1 or k>#data.sightings then return nil end
        count=count+1
    end
    if count~=#data.sightings then return nil end
    local result={}
    for _,s in ipairs(data.sightings) do
        if type(s)~='table' or not validText(s.recordId) or not validText(s.cell)
            or not validText(s.name) or not validText(s.place) then return nil end
        local key=s.recordId..'\0'..s.cell
        if result[key] then return nil end
        result[key]={recordId=s.recordId,cell=s.cell,name=s.name,place=s.place}
    end
    return result
end

local function onLoad(data)
    close();clearHud();selected=nil;tracked=nil;entries={};sightings={};retainedInvalidSave=nil
    if data==nil then return end
    local decoded=decode(data)
    if not decoded then retainedInvalidSave=data;return end
    sightings=decoded
    message='Dein Sammelatlas wurde aus diesem Morrowind-Spielstand geladen.'
end

return {interfaceName='HALVETHFieldcraft',
    interface={version=1,open=open,close=close,isOpen=function()return window~=nil end,
        getState=snapshot,refresh=refresh,select=select,survey=survey,track=setTracked},
    engineHandlers={onLoad=onLoad,onSave=function()
        return retainedInvalidSave or {version=1,sightings=orderedSightings()}
    end,onFrame=function()
        if window and I.UI.getMode()~=mode then close() end
        if window and I.HALVETHUniverse and I.HALVETHUniverse.getState().panelOpen then close() end
        local now=core.getRealTime()
        if now-lastUpdate>.5 then lastUpdate=now;if window or tracked then refresh();updateHud() end end
    end},
}
