-- A save-backed social chronicle inside the running Morrowind world.
-- Observations and the derived regional pulse are separate: no original AI,
-- quest, dialogue or faction record is modified by this script.
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')

local MAX_PEOPLE,MAX_PULSES=128,96
local people,pulses={},{}
local selected,window,detail,summary,rows,mode,addedMode=nil,nil,nil,nil,{},nil,false
local retainedInvalidSave,lastScan,lastCell=nil,-100,nil
local message='Diese Chronik beobachtet echte Begegnungen. Der Fraktionsimpuls ist eine zusaetzliche Spielsimulation.'
local scan,refresh,open

local function validText(s)
    return type(s)=='string' and #s>0 and #s<=256 and not s:find('[%z\1-\31]')
end
local function count(map)
    local n=0;for _ in pairs(map) do n=n+1 end;return n
end
local function day()
    return math.floor(math.max(0,core.getGameTime())/86400)
end
local function cellKey(cell)
    if not cell then return nil end
    if cell.isExterior then
        return tostring(cell.worldSpaceId or cell.id)..':'..tostring(cell.gridX)..':'..tostring(cell.gridY)
    end
    return cell.id
end
local function placeName(cell)
    if not cell then return '?' end
    local title=cell.displayName
    if type(title)~='string' or title=='' then title=cell.name end
    if type(title)~='string' or title=='' then title=cell.id end
    return C.head(tostring(title or '?'),100)
end
local function sortedPeople()
    local out=C.array()
    for _,p in pairs(people) do out[#out+1]=p end
    table.sort(out,function(a,b)
        if a.lastDay==b.lastDay then return a.name<b.name end
        return a.lastDay>b.lastDay
    end)
    return out
end
local function sortedPulses(cell)
    local out=C.array()
    for _,p in pairs(pulses) do if not cell or p.cell==cell then out[#out+1]=p end end
    table.sort(out,function(a,b)
        if a.day==b.day then
            if a.score==b.score then return a.faction<b.faction end
            return a.score>b.score
        end
        return a.day>b.day
    end)
    return out
end
local function pulse(cell,faction,kind)
    local d=day()
    local key=tostring(d)..'\0'..cell..'\0'..faction
    local item=pulses[key]
    if not item then
        if count(pulses)>=MAX_PULSES then
            message='Die regionale Chronik ist voll ('..MAX_PULSES..' Tagesimpulse). Vorhandene Eintraege bleiben erhalten.'
            return false
        end
        item={day=d,cell=cell,faction=faction,sightings=0,dialogues=0,score=0}
        pulses[key]=item
    end
    if kind=='dialogue' then item.dialogues=item.dialogues+1
    else item.sightings=item.sightings+1 end
    item.score=math.min(999,item.sightings+item.dialogues*2)
    return true
end
local function actorInfo(actor)
    if not actor or not actor:isValid() or not types.NPC.objectIsInstance(actor)
       or actor.id==self.id or types.Actor.isDead(actor) or not self.cell then return nil end
    if (actor.position-self.position):length()>3000 then return nil end
    local record=types.NPC.record(actor)
    local id=tostring(actor.id)
    local cell=cellKey(actor.cell or self.cell)
    if not validText(id) or not validText(cell) then return nil end
    local factions=C.array()
    for _,faction in ipairs(types.NPC.getFactions(actor)) do
        if validText(faction) and #factions<8 then factions[#factions+1]=faction end
    end
    table.sort(factions)
    local name=(type(record.name)=='string' and record.name~='') and record.name or actor.recordId
    local role=(type(record.class)=='string' and record.class~='') and record.class or 'npc'
    return {id=id,recordId=actor.recordId,name=C.head(name,100),
        role=C.head(role,100),cell=cell,place=placeName(actor.cell or self.cell),
        factions=factions,position=actor.position}
end
local function observe(actor,spoken)
    if retainedInvalidSave then return false end
    local info=actorInfo(actor)
    if not info then return false end
    local d=day()
    local p=people[info.id]
    if not p then
        if count(people)>=MAX_PEOPLE then
            message='Das NPC-Gedaechtnis ist voll ('..MAX_PEOPLE..' Figuren). Bisherige Erinnerungen bleiben erhalten.'
            return false
        end
        p={id=info.id,recordId=info.recordId,name=info.name,role=info.role,
            firstDay=d,lastDay=d,cell=info.cell,place=info.place,
            sightings=0,dialogues=0,lastPulseDay=-1,lastDialogueTime=-100000000,
            movement='Noch keine zweite Positionsbeobachtung.',factions=info.factions}
        people[info.id]=p
    end
    local changed=p.cell~=info.cell
    if p.lastX and p.cell==info.cell then
        local dx=info.position.x-p.lastX;local dy=info.position.y-p.lastY
        if dx*dx+dy*dy>=128*128 then
            p.movement='Bewegung am beobachteten Ort erkannt.'
        end
    elseif changed then p.movement='An einem anderen Ort erneut angetroffen.' end
    p.lastX=info.position.x;p.lastY=info.position.y
    p.cell=info.cell;p.place=info.place;p.lastDay=d
    -- One presence signal per person and game day; polling does not inflate it.
    if p.lastPulseDay~=d then
        p.sightings=p.sightings+1;p.lastPulseDay=d
        for _,faction in ipairs(p.factions) do pulse(info.cell,faction,'sighting') end
    end
    if spoken then
        local now=core.getGameTime()
        if now-p.lastDialogueTime<30 then return false end
        p.dialogues=p.dialogues+1;p.lastDialogueTime=now
        for _,faction in ipairs(p.factions) do pulse(info.cell,faction,'dialogue') end
        message='Gespraech mit '..p.name..' in '..p.place..' festgehalten.'
    end
    return true
end
local function snapshot()
    local personList=C.array();local pulseList=C.array()
    for _,p in ipairs(sortedPeople()) do
        personList[#personList+1]={id=p.id,name=p.name,role=p.role,place=p.place,
            firstDay=p.firstDay,lastDay=p.lastDay,sightings=p.sightings,
            dialogues=p.dialogues,movement=p.movement,factions=p.factions}
    end
    for _,p in ipairs(sortedPulses(cellKey(self.cell))) do
        pulseList[#pulseList+1]={day=p.day,cell=p.cell,faction=p.faction,
            sightings=p.sightings,dialogues=p.dialogues,score=p.score}
    end
    return {version=1,people=personList,pulses=pulseList,selected=selected,
        panelOpen=window~=nil,day=day(),cell=cellKey(self.cell),message=message,
        observationLimit=MAX_PEOPLE,pulseLimit=MAX_PULSES}
end
local function getContext(targetId)
    local s=snapshot()
    -- The chronicle's UI selection is not the current conversation partner.
    -- Bind optional actor history only to the exact actor chosen by player.lua.
    local target=targetId~=nil and people[tostring(targetId)] or nil
    local regional=C.array()
    for i=1,math.min(5,#s.pulses) do regional[#regional+1]=s.pulses[i] end
    return {gameDay=s.day,region=s.cell,observedPeople=#s.people,
        npc=target and {id=target.id,name=target.name,role=target.role,
            place=target.place,sightings=target.sightings,
            dialogues=target.dialogues,factions=target.factions} or nil,
        regionalPulse=regional,pulseMeaning='Eigene Simulation aus beobachteten NPC-Praesenzen und Dialogen; kein Original-Fraktionswert.'}
end
local function close()
    if window then window:destroy();window=nil end
    detail=nil;summary=nil;rows={}
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    mode=nil
end
local function button(label,x,y,w,fn,fontSize)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,30),text=label,textSize=fontSize or 17},
        events={mouseClick=async:callback(fn)}}
end
local function talkSelected()
    if not (selected and people[selected]) then
        message='Waehle zuerst eine beobachtete Figur.'
        refresh();return false
    end
    local target
    for _,actor in ipairs(nearby.actors) do
        local info=actorInfo(actor)
        if info and info.id==selected then target=actor;break end
    end
    if not target then
        message='Diese Figur ist gerade nicht mehr in der geladenen Umgebung.'
        refresh();return false
    end
    if not (I.HALVETH and I.HALVETH.talkTo) then
        message='Das native Gespraechsfenster ist gerade nicht verfuegbar.'
        refresh();return false
    end
    close()
    if I.HALVETH.talkTo(target) then return true end
    message='Diese Figur ist gerade nicht mehr ansprechbar.'
    open();return false
end
local function detailText()
    local p=selected and people[selected]
    local lines={'WELTLEBEN / BEOBACHTETE FIGUR',
        'Personen werden nur durch echte Naehe und echte Gespraeche notiert.'}
    if p then
        lines[#lines+1]=p.name..' · '..p.role
        lines[#lines+1]='Zuletzt gesehen: '..p.place..' | Spieltag '..p.lastDay
        lines[#lines+1]='Beobachtete Tage: '..p.sightings..' | Gespraeche: '..p.dialogues
        lines[#lines+1]='Bewegung: '..p.movement
        lines[#lines+1]='Fraktionen: '..(#p.factions>0 and table.concat(p.factions,', ') or 'keine erfasst')
        lines[#lines+1]='[Sprechen] oeffnet direkt die Unterhaltung, solange diese Figur noch in deiner Naehe ist.'
    else lines[#lines+1]='Waehle links eine beobachtete Figur.' end
    lines[#lines+1]='REGIONALER IMPULS / EIGENE SIMULATION'
    local items=sortedPulses(cellKey(self.cell))
    local shown=0
    for _,item in ipairs(items) do
        if item.day==day() and shown<8 then
            shown=shown+1
            lines[#lines+1]=item.faction..': '..item.score..' Impulse ('..item.sightings..' Sichtungen, '..item.dialogues..' Gespraeche)'
        end
    end
    if shown==0 then lines[#lines+1]='Heute noch keine Fraktionspraesenz hier beobachtet.' end
    lines[#lines+1]='Ein Impuls = eine neue Person am Spieltag; Gespraech = zwei weitere. Das ist eine neue Spielregel, keine Behauptung ueber ungesehene Ereignisse.'
    if I.HALVETHAmbient then
        local ambient=I.HALVETHAmbient.getState()
        lines[#lines+1]='EIGENER WANDERER / ECHTE OPENMW-AI'
        lines[#lines+1]=ambient.message or 'Noch kein Wanderer gerufen.'
        lines[#lines+1]='Draussen rufen, native Wander-Routine pausieren oder fortsetzen, nur diesen selbst erzeugten NPC entfernen.'
    end
    return table.concat(lines,'\n\n')
end
refresh=function()
    local list=sortedPeople()
    if not (selected and people[selected]) then selected=list[1] and list[1].id or nil end
    for i,row in ipairs(rows) do
        local p=list[i]
        row.props.text=p and ((p.id==selected and '> ' or '  ')..C.head(p.name,35)..' · '..p.dialogues..' Gespraeche') or ''
    end
    if detail then detail.props.text=detailText() end
    if summary then summary.props.text=#list..' beobachtete Figuren · Spieltag '..day()..' · '..message end
    if window then window:update() end
end
open=function()
    if window then close();return end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    if I.HALVETHFieldcraft then I.HALVETHFieldcraft.close() end
    if I.HALVETH then I.HALVETH.close() end
    mode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    local screen=ui.screenSize()
    local w,h=math.min(1080,screen.x-24),math.min(710,screen.y-24)
    local content={{type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
        props={position=util.vector2(18,14),text='HALVETH / MORROWIND / WELTLEBEN',textSize=22}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(18,48),text='Echte Begegnungen · lebende Chronik · regionaler Impuls',textSize=16}}}
    rows={}
    for i=1,math.max(4,math.min(12,math.floor((h-205)/38))) do
        local index=i
        local row=button('',20,83+(i-1)*38,370,function()
            local p=sortedPeople()[index]
            if p then selected=p.id;refresh() end
        end)
        rows[#rows+1]=row;content[#content+1]=row
    end
    detail={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(405,82),size=util.vector2(w-425,h-206),text='',textSize=17,
            readOnly=true,multiline=true,wordWrap=true}}
    summary={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(18,h-107),size=util.vector2(w-36,50),text='',textSize=15,wordWrap=true}}
    content[#content+1]=detail;content[#content+1]=summary
    local controls={
        {w<900 and '[Neu]' or '[Aktualisieren]',function()scan();refresh()end},
        {'[Sprechen]',talkSelected},
        {'[Rufen]',function()I.HALVETHAmbient.spawn();refresh()end},
        {'[Pause]',function()I.HALVETHAmbient.pause();refresh()end},
        {'[Weiter]',function()I.HALVETHAmbient.resume();refresh()end},
        {'[Entfernen]',function()I.HALVETHAmbient.dismiss();refresh()end},
        {'[Schliessen]',close},
    }
    local gap=6
    local slot=math.floor((w-36-gap*(#controls-1))/#controls)
    for i,control in ipairs(controls) do
        content[#content+1]=button(control[1],18+(i-1)*(slot+gap),h-48,
            slot,control[2],w<900 and 14 or 16)
    end
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},
        content=ui.content(content)}
    scan();refresh()
end
scan=function()
    if not self.cell or retainedInvalidSave then return end
    local n=0
    for _,actor in ipairs(nearby.actors) do
        if n>=32 then break end
        if actor:isValid() and types.NPC.objectIsInstance(actor) then
            observe(actor,false);n=n+1
        end
    end
    lastCell=cellKey(self.cell)
end
local function export()
    local a=C.array();local b=C.array()
    for _,p in ipairs(sortedPeople()) do
        a[#a+1]={id=p.id,recordId=p.recordId,name=p.name,role=p.role,
            firstDay=p.firstDay,lastDay=p.lastDay,cell=p.cell,place=p.place,
            sightings=p.sightings,dialogues=p.dialogues,lastPulseDay=p.lastPulseDay,
            lastDialogueTime=p.lastDialogueTime,movement=p.movement,
            factions=p.factions,lastX=p.lastX,lastY=p.lastY}
    end
    for _,p in ipairs(sortedPulses()) do b[#b+1]=p end
    return {version=1,people=a,pulses=b}
end
local function validNumber(n)
    return type(n)=='number' and n==n and math.abs(n)<1000000000
end
local function decode(data)
    if type(data)~='table' or data.version~=1 or type(data.people)~='table' or type(data.pulses)~='table'
        or #data.people>MAX_PEOPLE or #data.pulses>MAX_PULSES then return nil end
    local ppl,pls={},{}
    for _,p in ipairs(data.people) do
        if type(p)~='table' or not validText(p.id) or ppl[p.id] or not validText(p.recordId)
            or not validText(p.name) or not validText(p.role) or not validText(p.cell)
            or not validText(p.place) or not validText(p.movement) or type(p.factions)~='table'
            or #p.factions>8 then return nil end
        for _,f in ipairs(p.factions) do if not validText(f) then return nil end end
        for _,key in ipairs({'firstDay','lastDay','sightings','dialogues','lastPulseDay','lastDialogueTime'}) do
            if not validNumber(p[key]) then return nil end
        end
        if (p.lastX~=nil and not validNumber(p.lastX)) or (p.lastY~=nil and not validNumber(p.lastY)) then return nil end
        ppl[p.id]=p
    end
    for _,p in ipairs(data.pulses) do
        if type(p)~='table' or not validText(p.cell) or not validText(p.faction)
            or not validNumber(p.day) or not validNumber(p.sightings)
            or not validNumber(p.dialogues) or not validNumber(p.score) then return nil end
        local key=tostring(p.day)..'\0'..p.cell..'\0'..p.faction
        if pls[key] then return nil end
        pls[key]=p
    end
    return ppl,pls
end
local function onLoad(data)
    close();people={};pulses={};selected=nil;retainedInvalidSave=nil;lastScan=-100;lastCell=nil
    if data==nil then return end
    local a,b=decode(data)
    if not a then retainedInvalidSave=data;return end
    people=a;pulses=b
    message='Dein Weltleben wurde aus diesem Morrowind-Spielstand geladen.'
end
return {interfaceName='HALVETHWorldlife',
    interface={version=1,open=open,close=close,isOpen=function()return window~=nil end,
        getState=snapshot,getContext=getContext,observe=observe,refresh=refresh,
        select=function(id)
            if not people[id] then return false end
            selected=id
            if window then refresh() end
            return true
        end,
        talkSelected=talkSelected},
    engineHandlers={onLoad=onLoad,onSave=function()return retainedInvalidSave or export()end,
        onFrame=function()
            if window and I.UI.getMode()~=mode then close() end
            local now=core.getRealTime()
            if self.cell and (now-lastScan>2 or lastCell~=cellKey(self.cell)) then
                lastScan=now;scan();if window then refresh() end
            end
        end},
    eventHandlers={UiModeChanged=function(data)
        if type(data)=='table' and data.newMode=='Dialogue' and data.arg then
            if observe(data.arg,true) and window then refresh() end
        end
    end},
}
