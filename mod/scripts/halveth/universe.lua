-- One in-game character, inventory, magic and encounter workbench.
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local input=require('openmw.input')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')
local inspect=require('scripts.halveth.inspect')
local window,detail,status,searchLayout,mode,addedMode,sortControl,actionControl
local tab,query,page,selection,order='character','',0,nil,'name'
local entries,filtered,rowLayouts={}, {}, {}
local pageSize,lastRefresh=9,0
local menuBar
local rebuild,refresh,open
local tabs={{'character','Figur'},{'inventory','Inventar'},{'magic','Magie'},{'nearby','Begegnungen'}}
local message='Waehle einen Eintrag. Alle Werte stammen aus deiner laufenden Welt.'
local function close()
    if window then window:destroy();window=nil end
    detail=nil;status=nil;searchLayout=nil;rowLayouts={}
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    mode=nil
end
local function feedback(text)
    message=text
    if status then status.props.text=text;if window then window:update() end end
end
local function sorted(list)
    table.sort(list,function(a,b)
        if order=='value' and a.ratio~=b.ratio then return (a.ratio or -1)>(b.ratio or -1) end
        if a.title==b.title then return a.id<b.id end
        return a.title<b.title
    end)
end
local function collect()
    local list={}
    if tab=='character' then
        list[#list+1]={id='self',title='Deine Figur',kind='actor',object=self.object}
        for _,skill in ipairs(inspect.skills(self)) do
            list[#list+1]={id=skill.id,title=skill.title..'  '..string.format('%.0f',skill.value),kind='skill',skill=skill}
        end
    elseif tab=='inventory' then
        local equipment={}
        for _,object in pairs(types.Actor.getEquipment(self)) do equipment[object.id]=true end
        for _,object in ipairs(types.Actor.inventory(self):getAll()) do
            local r=object.type.record(object)
            local kind=inspect.kind(object)
            list[#list+1]={id=object.id,title=(equipment[object.id] and '* ' or '')..(r.name or object.recordId)..' x'..object.count,
                name=r.name or object.recordId,kind='item',category=kind,object=object,
                ratio=(r.weight and r.weight>0) and (r.value or 0)/r.weight or 0}
        end
        sorted(list)
    elseif tab=='magic' then
        for _,spell in pairs(types.Actor.spells(self)) do
            list[#list+1]={id=spell.id,title=spell.name,kind='spell',spell=spell}
        end
        sorted(list)
    elseif tab=='nearby' then
        for _,actor in ipairs(nearby.actors) do
            if actor.id~=self.id and actor:isValid() then
                local r=actor.type.record(actor)
                local distance=(actor.position-self.position):length()
                if distance<=3000 then list[#list+1]={id=actor.id,title=r.name or actor.recordId,kind='actor',object=actor,distance=distance} end
            end
        end
        table.sort(list,function(a,b) if a.distance==b.distance then return a.id<b.id end;return a.distance<b.distance end)
    end
    return list
end
local function current()
    for _,entry in ipairs(filtered) do if entry.id==selection then return entry end end
end
local function describe(entry)
    if not entry then return 'Keine passenden Eintraege. Aendere die Suche oder besuche einen anderen Ort.' end
    if entry.kind=='actor' then
        if not entry.object:isValid() then return 'Diese Figur ist nicht mehr im geladenen Bereich.' end
        local text=inspect.actorText(entry.object,self)
        return text..(entry.object.id~=self.id and '\n\n[Gespraech] oeffnet die lokale Unterhaltung mit genau dieser Figur.' or '')
    elseif entry.kind=='item' then
        if not entry.object:isValid() then return 'Dieser Gegenstand ist nicht mehr vorhanden.' end
        return inspect.item(entry.object,self)
    elseif entry.kind=='spell' then return inspect.spell(entry.spell)
    elseif entry.kind=='skill' then
        local s=entry.skill
        return string.format('%s\n\n%s\n\nAktueller Wert: %.1f\nGrundwert: %.1f\nFortschritt zum naechsten Punkt: %.1f%%\n\nUebe die passende Handlung im normalen Spiel. Haupt- und Nebenfertigkeiten tragen zum Stufenaufstieg bei.\n\nBuecher und Studiennotizen findest du unter Wissen / F7.',s.title,s.rank,s.value,s.base,s.progress*100)
    end
    return ''
end
refresh=function()
    if not window then return end
    filtered={}
    local needle=query:lower()
    for _,entry in ipairs(entries) do
        if needle=='' or (entry.title..' '..(entry.category or '')):lower():find(needle,1,true) then filtered[#filtered+1]=entry end
    end
    local lastPage=math.max(0,math.ceil(#filtered/pageSize)-1)
    page=math.max(0,math.min(page,lastPage))
    if not current() then selection=filtered[1] and filtered[1].id or nil end
    for index,row in ipairs(rowLayouts) do
        local entry=filtered[page*pageSize+index]
        row.props.text=entry and ((entry.id==selection and '> ' or '  ')..C.head(entry.title,90)) or ''
    end
    local ok,text=pcall(describe,current())
    detail.props.text=ok and text or 'Die Spielwerte werden gerade erneuert. Bitte aktualisieren.'
    if not ok then print('HALVETH_UNIVERSE_DESCRIBE '..tostring(text)) end
    local entry=current()
    sortControl.props.text=tab=='inventory' and (order=='name' and '[Sortierung: Name]' or '[Sortierung: Wert / Gewicht]') or '[Aktualisieren]'
    actionControl.props.text=not entry and '[Kein Eintrag]' or entry.kind=='spell' and '[Zauber auswaehlen]'
        or entry.kind=='actor' and entry.object.id~=self.id and '[Mit dieser Figur sprechen]'
        or entry.kind=='item' and types.Book.objectIsInstance(entry.object) and '[Im Original lesen]'
        or '[Normales Inventar]'
    status.props.text=string.format('%d Eintraege | Seite %d/%d | %s',#filtered,page+1,lastPage+1,message)
    window:update()
end
rebuild=function()
    local ok,list=pcall(collect)
    if ok then entries=list else entries={};print('HALVETH_UNIVERSE_COLLECT '..tostring(list));feedback('Spielwerte noch nicht verfuegbar.') end
    refresh()
end
local function selectTab(id)
    local valid=false;for _,t in ipairs(tabs) do if t[1]==id then valid=true end end
    if not valid then return false end
    tab=id;page=0;selection=nil;query=''
    if searchLayout then searchLayout.props.text='' end
    rebuild();return true
end
local function perform()
    local entry=current()
    if not entry then return false end
    if entry.kind=='actor' and entry.object.id~=self.id and entry.object:isValid() then
        if types.Actor.isDead(entry.object) then feedback('Diese Figur ist verstorben.');return false end
        close()
        if I.HALVETH then I.HALVETH.talkTo(entry.object) end
        return true
    elseif entry.kind=='spell' then
        if entry.spell.type~=core.magic.SPELL_TYPE.Spell and entry.spell.type~=core.magic.SPELL_TYPE.Power then
            feedback('Diese Dauerwirkung ist kein auswaehlbarer Zauber.');return false
        end
        if not types.Actor.spells(self)[entry.id] then feedback('Der Zauber ist nicht mehr erlernt.');return false end
        types.Actor.setSelectedSpell(self,entry.id)
        feedback(entry.title..' ist ausgewaehlt. Schliessen und normal zaubern.');return true
    elseif entry.kind=='item' and entry.object:isValid() and types.Book.objectIsInstance(entry.object) then
        local object=entry.object;local record=types.Book.record(object)
        close();I.UI.addMode(record.isScroll and 'Scroll' or 'Book',{target=object});return true
    end
    close()
    if I.UI.getMode()~='Interface' then I.UI.addMode('Interface',{windows={'Inventory','Stats','Magic'}}) end
    return true
end
local function button(text,x,y,w,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,30),text=text,textSize=17},
        events={mouseClick=async:callback(fn)}}
end
local function updateMenuBar()
    local currentMode=I.UI.getMode()
    local show=(currentMode=='Interface' or currentMode=='Dialogue') and not window
        and not (I.HALVETH and I.HALVETH.isOpen())
        and not (I.HALVETHKnowledge and I.HALVETHKnowledge.isOpen())
        and not (I.HALVETHPaths and I.HALVETHPaths.isOpen())
        and not (I.HALVETHFieldcraft and I.HALVETHFieldcraft.isOpen())
        and not (I.HALVETHWorldlife and I.HALVETHWorldlife.isOpen())
    if show and not menuBar then
        local barWidth=math.min(1290,ui.screenSize().x-24)
        local slot=math.floor((barWidth-20)/7)
        menuBar=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
            props={relativePosition=util.vector2(.5,0),position=util.vector2(0,8),anchor=util.vector2(.5,0),size=util.vector2(barWidth,36)},
            content=ui.content{
                button('[HALVETH · Figur]',10,6,slot-4,function()open()end),
                button('[Wissen]',10+slot,6,slot-4,function()I.HALVETHKnowledge.open()end),
                button('[Gespraech]',10+slot*2,6,slot-4,function()I.HALVETH.open()end),
                button('[Pfade]',10+slot*3,6,slot-4,function()I.HALVETHPaths.open()end),
                button('[Sammeln]',10+slot*4,6,slot-4,function()I.HALVETHFieldcraft.open()end),
                button('[Weltleben]',10+slot*5,6,slot-4,function()I.HALVETHWorldlife.open()end),
                button('[Licht]',10+slot*6,6,slot-4,function()I.HALVETHVisuals.cycle()end)}}
    elseif not show and menuBar then menuBar:destroy();menuBar=nil end
end
open=function(requestedTab)
    if window then close();return end
    if I.HALVETH then I.HALVETH.close() end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    if I.HALVETHFieldcraft then I.HALVETHFieldcraft.close() end
    if I.HALVETHWorldlife then I.HALVETHWorldlife.close() end
    mode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    if requestedTab then selectTab(requestedTab) end
    local screen=ui.screenSize()
    local w,h=math.min(1180,screen.x-24),math.min(760,screen.y-24)
    local left=math.floor((w-54)*.38)
    local bodyHeight=h-238
    pageSize=math.max(3,math.floor((bodyHeight-62)/38))
    local content={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
            props={position=util.vector2(18,14),text='HALVETH / MORROWIND / DEINE WELT',textSize=23}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(18,48),text='Figuren verstehen · Ausruestung vergleichen · Magie bewusst einsetzen',textSize=16}},
    }
    for n,t in ipairs(tabs) do
        local id=t[1];content[#content+1]=button('['..t[2]..']',18+(n-1)*math.floor((w-36)/4),83,math.floor((w-36)/4)-8,function() selectTab(id) end)
    end
    searchLayout={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditLine,
        props={position=util.vector2(22,131),size=util.vector2(left-8,30),text=query,textSize=17},
        events={textChanged=async:callback(function(text) query=C.head(text,160);page=0;refresh() end)}}
    content[#content+1]=searchLayout
    content[#content+1]={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(22,115),text='Suche nach Name oder Kategorie',textSize=12}}
    rowLayouts={}
    for index=1,pageSize do
        local rowIndex=index
        local row=button('',22,175+(index-1)*38,left-8,function()
            local entry=filtered[page*pageSize+rowIndex]
            if entry then selection=entry.id;refresh() end
        end)
        rowLayouts[#rowLayouts+1]=row;content[#content+1]=row
    end
    detail={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(left+36,131),size=util.vector2(w-left-54,h-271),text='',textSize=18,readOnly=true,multiline=true,wordWrap=true}}
    status={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(18,h-87),size=util.vector2(w-36,44),text='',textSize=15,wordWrap=true}}
    content[#content+1]=detail;content[#content+1]=status
    content[#content+1]=button('[<]',22,h-130,48,function()page=math.max(0,page-1);refresh()end)
    content[#content+1]=button('[>]',78,h-130,48,function()page=page+1;refresh()end)
    sortControl=button('',138,h-130,left-115,function()if tab=='inventory' then order=order=='name' and 'value' or 'name' end;rebuild()end)
    actionControl=button('',left+40,h-130,w-left-70,perform)
    content[#content+1]=sortControl;content[#content+1]=actionControl
    content[#content+1]=button('[Wissen / F7]',18,h-37,170,function()close();I.HALVETHKnowledge.open()end)
    content[#content+1]=button('[Gespraeche / F8]',192,h-37,200,function()close();I.HALVETH.open()end)
    content[#content+1]=button('[Pfade]',402,h-37,112,function()close();I.HALVETHPaths.open()end)
    content[#content+1]=button('[Sammeln]',520,h-37,115,function()close();I.HALVETHFieldcraft.open()end)
    content[#content+1]=button('[Weltleben]',635,h-37,130,function()close();I.HALVETHWorldlife.open()end)
    content[#content+1]=button('[Licht]',770,h-37,65,function()I.HALVETHVisuals.cycle()end)
    content[#content+1]=button('[Aktualisieren]',w-340,h-37,165,rebuild)
    content[#content+1]=button('[Schliessen / F6]',w-170,h-37,155,close)
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},content=ui.content(content)}
    rebuild()
end
local function snapshot()
    local result={tab=tab,query=query,page=page,entryCount=#entries,filteredCount=#filtered,selectedId=selection,
        panelOpen=window~=nil,detail=detail and detail.props.text or '',message=message,entries=C.array()}
    for _,entry in ipairs(filtered) do result.entries[#result.entries+1]={id=entry.id,title=entry.title,kind=entry.kind,category=entry.category} end
    return result
end
return {interfaceName='HALVETHUniverse',
    interface={version=1,open=open,close=close,getState=snapshot,selectTab=selectTab,refresh=rebuild,perform=perform,
        select=function(id)for _,entry in ipairs(filtered)do if entry.id==id then selection=id;refresh();return true end end;return false end,
        search=function(text)query=C.head(text,160);page=0;if searchLayout then searchLayout.props.text=query end;refresh()end},
    engineHandlers={onLoad=function()close();if menuBar then menuBar:destroy();menuBar=nil end end,onKeyPress=function(key)
        if key.code==input.KEY.F6 then open()
        elseif window and key.code==input.KEY.Escape then close()
        elseif window and key.code==input.KEY.PageDown then page=page+1;refresh()
        elseif window and key.code==input.KEY.PageUp then page=math.max(0,page-1);refresh() end
    end,onFrame=function()
        if window and I.UI.getMode()~=mode then close() end
        updateMenuBar()
        if window and core.getRealTime()-lastRefresh>2 then lastRefresh=core.getRealTime();rebuild() end
    end}}
