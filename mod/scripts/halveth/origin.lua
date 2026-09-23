-- A new-game-only origin scene inside the existing Morrowind world.
-- It does not replace the original character creator or manufacture a partner.
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')

local CHOICES={love='Liebe',witness='Erkenntnis',journey='Reise'}
local armed,completed,choice=false,false,nil
local name,counterpart=nil,nil
local window,addedMode=nil,false
local lastAttempt=0

local function close()
    if window then window:destroy();window=nil end
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
end

local function state()
    return {version=1,armed=armed,completed=completed,choice=choice,
        name=name,counterpart=counterpart}
end

local function select(id)
    if not CHOICES[id] or completed or not armed then return false end
    choice=id;completed=true;armed=false
    close()
    ui.showMessage('Pulsar-Erwachen: '..CHOICES[id]..' ist deine erste HALVETH-Spur. F8 kennt diesen Anfang.')
    print('HALVETH_ORIGIN_SELECTED '..id)
    return true
end

local function button(text,x,y,w,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,36),text=text,textSize=19},
        events={mouseClick=async:callback(fn)}}
end

local function open()
    if window or completed or not armed then return end
    local screen=ui.screenSize()
    local w,h=math.min(830,screen.x-32),math.min(490,screen.y-32)
    if w<480 or h<340 then return end
    local body='Du bist angekommen. Der Name '..C.head(name or 'deiner Figur',80)
        ..' ist der erste Satz, nicht deine ganze Geschichte.\n\n'
        ..'Ein fremder Puls hat diese Welt beruehrt. In deiner Reise kann '
        ..(counterpart=='woman' and 'eine Frau' or 'ein Mann')
        ..' als Gegenfigur wichtig werden. Begegnung, Vertrauen und Liebe entstehen erst durch Handlungen.\n\n'
        ..'Welchen ersten Impuls traegst du in diese Welt?'
    local contents={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
            props={position=util.vector2(22,18),text='HALVETH / PULSAR-ERWACHEN',textSize=25}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(22,61),text='Seelensnapshot · einmal pro neuer Reise',textSize=16}},
        {type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
            props={position=util.vector2(22,99),size=util.vector2(w-44,h-205),
                text=body,textSize=18,readOnly=true,multiline=true,wordWrap=true}},
        button('[Liebe]',22,h-77,160,function()select('love')end),
        button('[Erkenntnis]',195,h-77,190,function()select('witness')end),
        button('[Reise]',398,h-77,160,function()select('journey')end),
    }
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,
        layer='Windows',props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),
            size=util.vector2(w,h)},content=ui.content(contents)}
    print('HALVETH_ORIGIN_OPEN '..tostring(w)..'x'..tostring(h))
end

local function frame()
    if not armed or completed or window or not self.cell or not self.cell.isExterior then return end
    if core.getRealTime()-lastAttempt<0.5 then return end
    lastAttempt=core.getRealTime()
    local ok,record=pcall(types.NPC.record,self)
    if not ok or not record or type(record.name)~='string' or record.name=='' then return end
    name=C.head(record.name,160)
    counterpart=record.isMale and 'woman' or 'man'
    if I.UI.getMode() then return end
    local drawn,err=pcall(open)
    if not drawn then print('HALVETH_ORIGIN_UI_ERROR '..tostring(err)) end
end

local function load(data)
    close();armed=false;completed=false;choice=nil;name=nil;counterpart=nil
    if type(data)~='table' or data.version~=1 then return end
    completed=data.completed==true
    armed=data.armed==true and not completed
    if CHOICES[data.choice] then choice=data.choice end
    if type(data.name)=='string' and #data.name<=160 then name=data.name end
    if data.counterpart=='woman' or data.counterpart=='man' then counterpart=data.counterpart end
end

return {interfaceName='HALVETHOrigin',
    interface={version=1,getState=state,select=select},
    engineHandlers={onFrame=frame,onLoad=load,onSave=state},
    eventHandlers={HALVETH_OriginNewGame=function()
        if not completed then armed=true end
    end}}
