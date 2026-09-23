-- Three original, nonviolent routes through the existing Morrowind world.
-- Actual books, NPCs and cells advance the path; state lives in the savegame.
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')

local ROUTES={
    lore={title='Spur des Wissens',description='Lies zwei verschiedene echte Texte und begegne einer Figur.',books=2,people=1,places=0},
    people={title='Spur der Begegnung',description='Sprich mit zwei verschiedenen Figuren und entdecke einen neuen Ort.',books=0,people=2,places=2},
    world={title='Spur der Welt',description='Besuche drei verschiedene Orte und lies einen Text.',books=1,people=0,places=3},
}
local ORDER={'lore','people','world'}
local active,books,people,places=nil,{},{},{}
local done,claimed={},{}
local lastCell,window,detail,footer,mode,addedMode,retainedInvalidSave=nil,nil,nil,nil,nil,false,nil
local message='Waehle eine Spur. Jede Beobachtung stammt aus deiner laufenden Welt.'
local update

local function validId(s)
    return type(s)=='string' and #s>0 and #s<=256 and not s:find('[%z\1-\31]')
end
local function count(t)
    local n=0;for _ in pairs(t) do n=n+1 end;return n
end
local function orderedKeys(t)
    local a=C.array();for key in pairs(t) do a[#a+1]=key end;table.sort(a);return a
end
local function cellKey(cell)
    if not cell then return nil end
    if cell.isExterior then
        return tostring(cell.worldSpaceId or cell.id)..':'..tostring(cell.gridX)..':'..tostring(cell.gridY)
    end
    return cell.id
end
local function currentCell()
    return self.cell and cellKey(self.cell)
end
local function snapshot()
    local completed=C.array();local rewarded=C.array()
    for _,id in ipairs(ORDER) do
        if done[id] then completed[#completed+1]=id end
        if claimed[id] then rewarded[#rewarded+1]=id end
    end
    return {version=1,active=active,books=orderedKeys(books),people=orderedKeys(people),places=orderedKeys(places),
        completed=completed,rewarded=rewarded,message=message,panelOpen=window~=nil}
end
local function close()
    if window then window:destroy();window=nil end
    detail=nil;footer=nil
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    mode=nil
end
local function progressText()
    local lines={'RACHEL / NEU · IN ARBEIT · ERLEDIGT','',
        'Eine Spur ist ein zusaetzliches Ziel in deiner echten Morrowind-Reise. Originalquests und NPCs bleiben erhalten.',''}
    for _,id in ipairs(ORDER) do
        local route=ROUTES[id]
        local status=done[id] and 'Erledigt' or active==id and 'In Arbeit' or 'Neu'
        lines[#lines+1]=route.title..' — '..status
        lines[#lines+1]=route.description
        if active==id then
            if route.books>0 then lines[#lines+1]='Texte: '..math.min(count(books),route.books)..' / '..route.books end
            if route.people>0 then lines[#lines+1]='Figuren: '..math.min(count(people),route.people)..' / '..route.people end
            if route.places>0 then lines[#lines+1]='Orte: '..math.min(count(places),route.places)..' / '..route.places end
        end
        if done[id] then lines[#lines+1]=claimed[id] and 'Ausdauerimpuls abgeholt.' or 'Ausdauerimpuls bereit: bis zu 30 Punkte.' end
        lines[#lines+1]=''
    end
    lines[#lines+1]='Eine gelesene Seite, eine tatsaechliche Begegnung oder ein betretenes Gebiet zaehlt einmal. Keine Wartezeit und kein Leerlauf-Fortschritt.'
    return table.concat(lines,'\n')
end
update=function()
    if detail then detail.props.text=progressText() end
    if footer then footer.props.text=message end
    if window then window:update() end
end
local function feedback(s)
    message=s;update()
end
local function checkComplete()
    if not active or retainedInvalidSave then return false end
    local r=ROUTES[active]
    if count(books)<r.books or count(people)<r.people or count(places)<r.places then return false end
    local title=r.title
    done[active]=true;active=nil;books={};people={};places={}
    feedback(title..' erfuellt. Hole den einmaligen Ausdauerimpuls ab oder beginne eine andere Spur.')
    return true
end
local function begin(id)
    if retainedInvalidSave then feedback('Dieser alte Pfadstand ist inkompatibel und bleibt unveraendert im Save.');return false end
    local r=ROUTES[id]
    if not r then return false end
    if done[id] then feedback(r.title..' wurde schon erfuellt.');return false end
    if active then feedback('Beende zuerst '..ROUTES[active].title..' oder verlasse diese Spur bewusst.');return false end
    active=id;books={};people={};places={}
    local key=currentCell()
    if key then places[key]=true;lastCell=key end
    feedback(r.title..' begonnen. Der aktuelle Ort ist dein Ausgangspunkt.')
    checkComplete();return true
end
local function abandon()
    if not active then return false end
    active=nil;books={};people={};places={}
    feedback('Spur verlassen. Bereits erfuellte Spuren und abgeholte Wirkungen bleiben erhalten.')
    return true
end
local function noteBook(object)
    if not active or retainedInvalidSave or not object or not object:isValid() or not types.Book.objectIsInstance(object) then return false end
    local id=object.recordId
    if not validId(id) or books[id] then return false end
    books[id]=true;feedback('Gelesener Text notiert: '..C.head(types.Book.record(object).name or id,100))
    checkComplete();return true
end
local function noteNpc(actor)
    if not active or retainedInvalidSave or not actor or not actor:isValid() or not types.Actor.objectIsInstance(actor)
       or types.Actor.isDead(actor) or actor.id==self.id or (actor.position-self.position):length()>3000 then return false end
    local key=tostring(actor.id)
    if not validId(key) or people[key] then return false end
    people[key]=true;feedback('Begegnung notiert: '..C.head(actor.type.record(actor).name or actor.recordId,100))
    checkComplete();return true
end
local function noteCell()
    if not active or retainedInvalidSave then return false end
    local key=currentCell()
    if not validId(key) or places[key] then return false end
    places[key]=true;feedback('Neuen Ort betreten: '..C.head(self.cell.displayName or self.cell.name or key,100))
    checkComplete();return true
end
local function claim()
    if retainedInvalidSave then return false end
    for _,id in ipairs(ORDER) do
        if done[id] and not claimed[id] then
            local stat=types.Actor.stats.dynamic.fatigue(self)
            local ceiling=math.max(0,stat.base+stat.modifier)
            local before=stat.current
            stat.current=math.min(ceiling,math.max(0,before)+30)
            claimed[id]=true
            feedback(ROUTES[id].title..': Ausdauerimpuls abgeholt. '..string.format('%.0f',stat.current-before)..' Ausdauer wiederhergestellt.')
            return true
        end
    end
    feedback('Noch kein offener Ausdauerimpuls.');return false
end
local function button(label,x,y,w,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,30),text=label,textSize=17},
        events={mouseClick=async:callback(fn)}}
end
local function open()
    if window then close();return end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETH then I.HALVETH.close() end
    mode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    local screen=ui.screenSize()
    local w,h=math.min(950,screen.x-24),math.min(700,screen.y-24)
    detail={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(20,75),size=util.vector2(w-40,h-195),text=progressText(),textSize=17,readOnly=true,multiline=true,wordWrap=true}}
    footer={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(18,h-110),size=util.vector2(w-36,43),text=message,textSize=15,wordWrap=true}}
    local content={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,props={position=util.vector2(18,15),text='HALVETH / MORROWIND / LEBENDIGE PFADE',textSize=22}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,props={position=util.vector2(18,46),text='Lesen · begegnen · erkunden · anwenden',textSize=16}},
        detail,footer,
        button('[Wissen]',18,h-160,150,function()begin('lore')end),
        button('[Begegnung]',177,h-160,174,function()begin('people')end),
        button('[Welt]',360,h-160,142,function()begin('world')end),
        button('[Spur verlassen]',510,h-160,195,abandon),
        button('[Ausdauer abholen]',18,h-46,220,claim),
        button('[Schliessen]',w-158,h-46,140,close),
    }
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},content=ui.content(content)}
end
local function export()
    return {version=1,active=active,books=orderedKeys(books),people=orderedKeys(people),places=orderedKeys(places),
        completed=orderedKeys(done),rewarded=orderedKeys(claimed)}
end
local function decodeList(value,allowed)
    if type(value)~='table' or #value>32 then return nil end
    local result={};local seen=0
    for key in pairs(value) do if type(key)~='number' or key%1~=0 or key<1 or key>#value then return nil end;seen=seen+1 end
    if seen~=#value then return nil end
    for _,id in ipairs(value) do
        if not validId(id) or result[id] or (allowed and not ROUTES[id]) then return nil end
        result[id]=true
    end
    return result
end
local function onLoad(data)
    close();active=nil;books={};people={};places={};done={};claimed={};lastCell=nil;retainedInvalidSave=nil
    if data==nil then return end
    if type(data)~='table' or data.version~=1 or (data.active~=nil and not ROUTES[data.active]) then retainedInvalidSave=data;return end
    local b,p,l=decodeList(data.books),decodeList(data.people),decodeList(data.places)
    local d,c=decodeList(data.completed,true),decodeList(data.rewarded,true)
    if not b or not p or not l or not d or not c then retainedInvalidSave=data;return end
    for id in pairs(c) do if not d[id] then retainedInvalidSave=data;return end end
    if data.active and d[data.active] then retainedInvalidSave=data;return end
    active=data.active;books=b;people=p;places=l;done=d;claimed=c
    message=active and 'Spur aus deinem Spielstand fortgesetzt.' or 'Dein Pfadstand ist geladen.'
end
return {interfaceName='HALVETHPaths',
    interface={version=1,open=open,close=close,isOpen=function()return window~=nil end,getState=snapshot,
        begin=begin,abandon=abandon,noteBook=noteBook,noteNpc=noteNpc,claim=claim,checkSaveRoundTrip=function()
            local s=export();return decodeList(s.books)~=nil and decodeList(s.people)~=nil and decodeList(s.places)~=nil end},
    engineHandlers={onLoad=onLoad,onSave=function()return retainedInvalidSave or export()end,onFrame=function()
        if window and I.UI.getMode()~=mode then close() end
        if active and self.cell then
            local key=currentCell()
            if key~=lastCell then lastCell=key;noteCell() end
        end
    end},
    eventHandlers={UiModeChanged=function(data)
        if not active or type(data)~='table' then return end
        if (data.newMode=='Book' or data.newMode=='Scroll') and data.arg then noteBook(data.arg) end
        if data.newMode=='Dialogue' and data.arg then noteNpc(data.arg) end
    end},
}
