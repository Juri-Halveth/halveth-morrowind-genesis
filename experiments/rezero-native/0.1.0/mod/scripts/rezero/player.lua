-- REZERO 0.1.0. Newly authored native UI; viewport-bound geometry, real game objects.
local ui=require('openmw.ui')
local async=require('openmw.async')
local core=require('openmw.core')
local types=require('openmw.types')
local self=require('openmw.self')
local util=require('openmw.util')
local vfs=require('openmw.vfs')
local I=require('openmw.interfaces')
local data=require('scripts.rezero.data')
local ownIcons=require('scripts.rezero.item_icons')
local V,C=util.vector2,util.color.rgb
local color={ink=C(.94,.93,.88),muted=C(.67,.73,.75),canvas=C(.026,.032,.042),pane=C(.052,.067,.081),
    tile=C(.079,.102,.121),hover=C(.13,.17,.19),selected=C(.16,.21,.22),copper=C(.89,.67,.40),
    health=C(.78,.32,.30),magicka=C(.44,.58,.85),fatigue=C(.40,.74,.60),black=C(.02,.03,.04),white=C(1,1,1)}
local categories={{'all','Alles'},{'weapon','Waffen'},{'armor','Rüstung'},{'clothing','Kleidung'},
    {'potion','Tränke'},{'ingredient','Zutaten'},{'book','Schriften'},{'other','Objekte'}}
local layerName,hudLayer='RezeroInventory','RezeroVitals'
local root,hud,layout,hudLayout,white,geometry
local nodes,cards,hudNodes,handlers,icons={},{},{},{},{}
local entries,filtered={},{}
local tab,category,query,sort,page,selected,hovered='inventory','all','','name',0,nil,nil
local visible,pending,layerRequested,hudRequested=false,false,false,false
local lastData,lastVitals,revision=0,0,0
local nativeClicks,nativeHovers,nativeQueries=0,0,0
local feedback='Dein Besitz. Deine Entscheidungen.'
local build,refresh,configure
local function callback(fn) return async:callback(fn) end
local function canvas(name)
    local index=ui.layers.indexOf(name)
    return index and ui.layers[index].size or nil
end
local function measures()
    local size=canvas(layerName) or canvas('Windows') or ui.screenSize()
    local screen=ui.screenSize()
    local w,h=math.floor(size.x),math.floor(size.y)
    -- Physical viewport drives reading size; layer ratio bridges native GUI scaling.
    local layerScale=screen.y/h
    local physicalUnit=math.max(.82,math.min(1.8,math.sqrt(screen.x*screen.y/(1920*1080))))
    local unit=physicalUnit/layerScale
    local font=math.max(12,math.floor(17*unit+.5))
    local gap=math.max(8,math.floor(font*.8))
    local margin=math.max(12,math.floor(font*1.6))
    local header=math.floor(font*4.8)
    local rail=math.floor(font*3.1)
    local footer=math.floor(font*4.8)
    local detailW=math.floor(math.min(w*.29,font*25))
    local mainW=w-2*margin-detailW-gap
    local gridY=margin+header+rail+gap
    local gridH=h-gridY-margin-footer
    local target=math.floor(font*11.2)
    local cols=math.max(1,math.floor((mainW+gap)/(target+gap)))
    local cardW=math.floor((mainW-(cols-1)*gap)/cols)
    local cardH=math.floor(font*8.6)
    local rows=math.max(1,math.floor((gridH+gap)/(cardH+gap)))
    return {w=w,h=h,viewportW=screen.x,viewportH=screen.y,layerScale=layerScale,font=font,gap=gap,margin=margin,
        headerH=header,railH=rail,footerH=footer,mainW=mainW,detailW=detailW,detailX=margin+mainW+gap,
        gridY=gridY,gridH=gridH,cols=cols,rows=rows,pageSize=cols*rows,cardW=cardW,cardH=cardH,
        bodyY=margin+header,bodyH=h-2*margin-header,icon=math.floor(font*4.5)}
end
local function image(name,x,y,w,h,tint,alpha,resource)
    return {name=name,type=ui.TYPE.Image,props={position=V(x,y),size=V(w,h),resource=resource or white,
        color=tint or color.white,alpha=alpha or 1,propagateEvents=true}}
end
local function text(name,value,x,y,w,h,size,tint)
    return {name=name,type=ui.TYPE.Text,props={position=V(x,y),size=V(w,h),autoSize=false,
        text=tostring(value or ''),textSize=size,textColor=tint or color.ink,multiline=true,wordWrap=true,propagateEvents=true}}
end
local function button(name,label,x,y,w,h,fn,active)
    local f=geometry.font
    handlers[name]=fn
    return {name=name,type=ui.TYPE.Widget,props={position=V(x,y),size=V(w,h),propagateEvents=false},
        events={mouseClick=callback(function() nativeClicks=nativeClicks+1;fn() end)},
        content=ui.content{image(name..'_face',0,0,w,h,active and color.selected or color.tile),
            image(name..'_rule',0,h-2,w,2,active and color.copper or color.pane),
            text(name..'_label',label,f*.65,(h-f*1.3)/2,w-f*1.3,f*1.5,f,active and color.copper or color.ink)}}
end
local function icon(entry)
    if entry.kind=='spell' then return nil end
    local source=ownIcons[entry.recordId] or entry.record.icon
    if not source or source=='' then return nil end
    source=source:gsub('\\','/')
    if source:sub(1,6):lower()~='icons/' then source='Icons/'..source end
    if icons[source]==nil then icons[source]=vfs.fileExists(source) and ui.texture{path=source} or false end
    return icons[source] or nil
end
local function find(id)
    for _,entry in ipairs(filtered) do if entry.id==id then return entry end end
end
local function filter()
    filtered={}
    for _,entry in ipairs(entries) do
        if (tab~='inventory' or category=='all' or entry.kind==category) and
            (query=='' or entry.name:lower():find(query:lower(),1,true)) then filtered[#filtered+1]=entry end
    end
    table.sort(filtered,function(a,b)
        if tab=='inventory' and sort=='value' and a.value~=b.value then return a.value>b.value end
        if tab=='inventory' and sort=='weight' and a.weight~=b.weight then return a.weight<b.weight end
        if a.name:lower()~=b.name:lower() then return a.name:lower()<b.name:lower() end
        return tostring(a.id)<tostring(b.id)
    end)
    local count=geometry and geometry.pageSize or 1
    page=math.max(0,math.min(page,math.max(0,math.ceil(#filtered/count)-1)))
    local selectedOnPage,hoverOnPage=false,false
    for i=page*count+1,math.min(#filtered,(page+1)*count) do
        if filtered[i].id==selected then selectedOnPage=true end
        if filtered[i].id==hovered then hoverOnPage=true end
    end
    if not selectedOnPage then selected=filtered[page*count+1] and filtered[page*count+1].id or nil end
    if not hoverOnPage then hovered=nil end
end
local function read() entries=data.collect(tab);lastData=core.getRealTime() end
local function destroy()
    if root then root:destroy() end
    root,layout=nil,nil;nodes,cards,handlers={},{},{}
end
local function close() I.UI.removeMode(I.UI.MODE.Interface) end
local function switch(nextTab)
    if nextTab~='inventory' and nextTab~='magic' and nextTab~='character' then return false end
    tab,query,page,selected,hovered=nextTab,'',0,nil,nil
    feedback=nextTab=='character' and 'Werte aus deinem Spielstand.' or nextTab=='magic' and 'Zauber und Kräfte aus deinem Spielstand.' or 'Dein Besitz. Deine Entscheidungen.'
    read();if visible then build();refresh() end
    return true
end
local function setCategory(id)
    local found=false
    for _,group in ipairs(categories) do if id==group[1] then found=true end end
    if not found or tab~='inventory' then return false end
    category,page,selected,hovered=id,0,nil,nil;build();refresh();return true
end
local function setQuery(value)
    if type(value)~='string' or #value>256 then return false end
    query,page,selected,hovered=value,0,nil,nil
    if nodes.search then nodes.search.props.text=value end
    refresh();return true
end
local function choose(id)
    for index,entry in ipairs(filtered) do
        if entry.id==id then page=math.floor((index-1)/geometry.pageSize);selected=id;hovered=nil;refresh();return true end
    end
    return false
end
local function preview(id)
    if not visible or tab=='character' then return false end
    if id~=nil then
        local onPage=false
        for index=page*geometry.pageSize+1,math.min(#filtered,(page+1)*geometry.pageSize) do if filtered[index].id==id then onPage=true end end
        if not onPage then return false end
    end
    hovered=id;refresh();return true
end
local function activate()
    local entry=find(selected)
    if not visible or I.UI.getMode()~=I.UI.MODE.Interface or tab=='character' then return false end
    if data.act(entry) then feedback=data.actionLabel(entry)..': '..entry.name;read();refresh();return true end
    return false
end
build=function()
    if not canvas(layerName) then pending=true;return end
    destroy();geometry=measures();local g=geometry;local f,p,gap=g.font,g.margin,g.gap
    white=white or ui.texture{path='Textures/rezero/white.png'}
    local content={image('membrane',0,0,g.w,g.h,color.canvas,.94),
        image('header_line',p,p+g.headerH-1,g.w-2*p,1,color.copper,.65),
        text('wordmark','M O R R O W I N D',p,p,g.w*.25,f*2.6,f*1.65,color.ink),
        text('chapter','REISE / BESITZ / MAGIE',p,p+f*2.5,g.w*.25,f*1.2,f*.72,color.muted)}
    local navX,navW,navH=p+math.floor(g.w*.29),math.floor(f*7.6),math.floor(f*2.45)
    for i,item in ipairs{{'inventory','Besitz'},{'magic','Magie'},{'character','Figur'}} do
        local id=item[1]
        content[#content+1]=button('tab_'..id,item[2],navX+(i-1)*(navW+gap),p,navW,navH,function()switch(id)end,tab==id)
    end
    local utilityW=math.floor(f*6.8)
    content[#content+1]=button('close','Zurück',g.w-p-utilityW,p,utilityW,navH,close)
    content[#content+1]=button('map','Karte',g.w-p-2*utilityW-gap,p,utilityW,navH,function()
        I.UI.setMode(I.UI.MODE.Interface,{windows={I.UI.WINDOW.Map}})
    end)
    content[#content+1]=image('detail_surface',g.detailX,g.bodyY,g.detailW,g.bodyH,color.pane,.96)
    content[#content+1]=image('detail_accent',g.detailX,g.bodyY,3,g.bodyH,color.copper,.75)
    if tab~='character' then
        local searchH,searchW=math.floor(f*2.45),math.floor(g.mainW*.48)
        content[#content+1]=image('search_surface',p,g.bodyY+gap,searchW,searchH,color.pane)
        content[#content+1]=text('search_label','Suche',p+f*.65,g.bodyY+gap+f*.5,f*3.5,f*1.4,f*.86,color.muted)
        nodes.search={name='query',type=ui.TYPE.TextEdit,props={position=V(p+f*4.3,g.bodyY+gap+f*.4),size=V(searchW-f*5,searchH-f*.5),
            text=query,textSize=f,textColor=color.ink,multiline=false,autoSize=false},events={textChanged=callback(function(value)nativeQueries=nativeQueries+1;setQuery(value)end)}}
        content[#content+1]=nodes.search
        if tab=='inventory' then
            local label=sort=='name' and 'Name A–Z' or sort=='value' and 'Wert ↓' or 'Gewicht ↑'
            content[#content+1]=button('sort',label,p+searchW+gap,g.bodyY+gap,math.floor(f*8),searchH,function()
                sort=sort=='name' and 'value' or sort=='value' and 'weight' or 'name';build();refresh()
            end)
            local railY=g.gridY
            local categoryCols=math.max(1,math.min(8,math.floor((g.mainW+gap)/(f*7+gap))))
            local categoryRows=math.ceil(#categories/categoryCols)
            local categoryW=math.floor((g.mainW-(categoryCols-1)*gap)/categoryCols)
            for i,group in ipairs(categories) do
                local id=group[1]
                content[#content+1]=button('category_'..id,group[2],p+((i-1)%categoryCols)*(categoryW+gap),railY+math.floor((i-1)/categoryCols)*(searchH+gap),categoryW,searchH,function()setCategory(id)end,category==id)
            end
            -- Search and category rail occupy separate rows in the new geometry.
            g.gridY=g.gridY+categoryRows*(searchH+gap)
            g.gridH=g.gridH-categoryRows*(searchH+gap)
            g.rows=math.max(1,math.floor((g.gridH+gap)/(g.cardH+gap)));g.pageSize=g.cols*g.rows
        end
        for index=1,g.pageSize do
            local i,x,y=index,p+((index-1)%g.cols)*(g.cardW+gap),g.gridY+math.floor((index-1)/g.cols)*(g.cardH+gap)
            local face=image('face_'..i,0,0,g.cardW,g.cardH,color.tile)
            local artSize=math.min(g.icon*1.25,g.cardH*.63)
            local artwork=image('art_'..i,(g.cardW-artSize)/2,f*.35,artSize,artSize,color.white)
            local title=text('name_'..i,'',f*.55,g.cardH-f*2.8,g.cardW-f*1.1,f*2.65,f,color.ink)
            local marker=image('selected_'..i,0,g.cardH-3,g.cardW,3,color.copper)
            local worn=text('equipped_'..i,'',f*.5,f*.25,g.cardW-f,f*1.2,f*.64,color.fatigue)
            local count=text('count_'..i,'',g.cardW-f*3.4,f*.3,f*3,f*1.3,f*.8,color.copper)
            local badge=text('badge_'..i,'',f*.55,f,g.cardW-f*1.1,f*1.5,f*.8,color.fatigue)
            local node={name='item_'..i,type=ui.TYPE.Widget,props={position=V(x,y),size=V(g.cardW,g.cardH),propagateEvents=false},
                events={mouseClick=callback(function()nativeClicks=nativeClicks+1;local entry=filtered[page*g.pageSize+i];if entry then choose(entry.id) end end),
                    mouseMove=callback(function()nativeHovers=nativeHovers+1;local entry=filtered[page*g.pageSize+i];if entry and hovered~=entry.id then preview(entry.id) end end)},
                content=ui.content{face,artwork,title,marker,worn,count,badge}}
            cards[i]={node=node,face=face,art=artwork,title=title,marker=marker,worn=worn,count=count,badge=badge}
            content[#content+1]=node
        end
        local pageY=g.h-p-g.footerH+gap
        content[#content+1]=button('previous','←',p,pageY,f*2.8,f*2.2,function()if page>0 then page=page-1;hovered=nil;refresh() end end)
        content[#content+1]=button('next','→',p+f*3.3,pageY,f*2.8,f*2.2,function()if (page+1)*g.pageSize<#filtered then page=page+1;hovered=nil;refresh() end end)
        nodes.page=text('page_status','',p+f*7,pageY+f*.4,g.mainW-f*7,f*1.4,f*.83,color.muted);content[#content+1]=nodes.page
    else
        content[#content+1]=text('character_heading','DEIN REISENDER',p,g.bodyY+gap,g.mainW,f*3,f*1.6,color.ink)
        local values,cellW,height=data.attributes(),math.floor((g.mainW-gap)/2),math.floor(f*4.3)
        nodes.attributes={}
        for i,stat in ipairs(values) do
            local x,y=p+((i-1)%2)*(cellW+gap),g.bodyY+f*4+math.floor((i-1)/2)*(height+gap)
            content[#content+1]=image('attribute_face_'..i,x,y,cellW,height,color.pane)
            content[#content+1]=text('attribute_name_'..i,stat.name,x+f,y+f*.7,cellW-f*2,f*1.6,f,color.muted)
            local valueNode=text('attribute_value_'..i,string.format('%.0f',stat.value),x+f,y+f*2,cellW-f*2,f*2,f*1.65,color.copper)
            nodes.attributes[i]=valueNode;content[#content+1]=valueNode
        end
    end
    local dx,detailInner,heroY=g.detailX+f,g.detailW-2*f,g.bodyY+f*5
    nodes.previewLabel=text('preview_label','',dx,g.bodyY+f,detailInner,f*1.3,f*.73,color.muted)
    nodes.title=text('detail_title','',dx,g.bodyY+f*2.2,detailInner,f*2.5,f*1.28,color.ink)
    nodes.hero=image('detail_art',g.detailX+(g.detailW-f*9)/2,heroY,f*9,f*9,color.white)
    local bodyTop=heroY+f*9.8
    if tab=='magic' or tab=='character' then bodyTop=g.bodyY+f*6;nodes.hero.props.visible=false end
    local actionY=g.h-p-f*5
    nodes.body=text('detail_text','',dx,bodyTop,detailInner,math.max(f*3,actionY-bodyTop-f*3),f*.86,color.ink)
    nodes.choice=text('choice','',dx,actionY-f*2.5,detailInner,f*2,f*.72,color.muted)
    nodes.action=button('action','',dx,actionY,detailInner,f*2.8,activate,true)
    nodes.actionLabel=nodes.action.content[3]
    for _,node in ipairs{nodes.previewLabel,nodes.title,nodes.hero,nodes.body,nodes.choice,nodes.action} do content[#content+1]=node end
    nodes.status=text('feedback','',p,g.h-p-f*1.1,g.w-2*p,f*1.3,f*.72,color.muted);content[#content+1]=nodes.status
    layout={name='RezeroRoot',type=ui.TYPE.Widget,layer=layerName,props={size=V(g.w,g.h),propagateEvents=false},
        content=ui.content(content),events={mouseMove=callback(function()if hovered then hovered=nil;refresh() end end)}}
    root=ui.create(layout);pending=false;revision=revision+1
end
refresh=function()
    if not root then return end
    filter();local g=geometry
    for index,card in ipairs(cards) do
        local entry=filtered[page*g.pageSize+index]
        card.node.props.visible=entry~=nil
        if entry then
            card.face.props.color=entry.id==hovered and color.hover or entry.id==selected and color.selected or color.tile
            card.title.props.text=entry.name
            card.marker.props.visible=entry.id==selected
            card.worn.props.text=entry.equipped and 'AUSGERÜSTET' or ''
            card.count.props.text=entry.count>1 and '×'..entry.count or ''
            local resource=icon(entry);card.art.props.visible=resource~=nil
            if resource then card.art.props.resource=resource end
            card.badge.props.text=entry.kind=='spell' and data.spellType(entry) or ''
        end
    end
    local selectedEntry,entry=find(selected),find(hovered) or find(selected)
    nodes.previewLabel.props.text=tab=='character' and 'SPIELSTAND / LIVE' or hovered and 'VORSCHAU' or 'AUSWAHL'
    nodes.title.props.text=tab=='character' and 'Dein Zustand' or entry and entry.name or 'Keine Treffer'
    if tab=='character' then
        local lines={}
        for i,stat in ipairs(data.attributes()) do nodes.attributes[i].props.text=string.format('%.0f',stat.value) end
        for _,stat in ipairs(data.vitals()) do lines[#lines+1]=stat.name..'\n'..string.format('%.0f / %.0f',stat.current,stat.maximum) end
        local used,max=data.capacity();lines[#lines+1]=string.format('TRAGLAST\n%.0f / %.0f',used,max)
        nodes.body.props.text=table.concat(lines,'\n\n')
    else nodes.body.props.text=data.description(entry) end
    local resource=entry and icon(entry)
    nodes.hero.props.visible=resource~=nil and tab=='inventory'
    if resource then nodes.hero.props.resource=resource end
    nodes.choice.props.text=tab=='character' and 'Werte stammen aus dem laufenden Spiel.' or selectedEntry and 'Aktionsziel: '..selectedEntry.name or ''
    local canAct=tab~='character' and selectedEntry and (selectedEntry.kind~='spell' or selectedEntry.castable)
    nodes.actionLabel.props.text=tab=='character' and 'Zustand' or data.actionLabel(selectedEntry)
    nodes.actionLabel.props.textColor=canAct and color.copper or color.muted
    nodes.action.content[1].props.color=canAct and color.selected or color.pane
    if nodes.page then nodes.page.props.text=string.format('%d %s   ·   Seite %d / %d',#filtered,tab=='magic' and 'Zauber und Effekte' or 'Einträge',page+1,math.max(1,math.ceil(#filtered/g.pageSize))) end
    nodes.status.props.text=feedback;root:update()
end
local function buildHud()
    if not canvas(hudLayer) then return end
    if hud then hud:destroy() end
    local g,f=measures(),geometry and geometry.font or measures().font
    white=white or ui.texture{path='Textures/rezero/white.png'}
    local p,width,height=math.floor(f*1.6),math.floor(f*17),math.floor(f*6.2)
    local content={image('vitals_surface',p,g.h-p-height,width,height,color.canvas,.80)};hudNodes={}
    for i,stat in ipairs(data.vitals()) do
        local y,barW=g.h-p-height+f*(.6+(i-1)*1.75),width-f*2
        local label=text('vital_label_'..i,stat.name,p+f,y,barW,f*1.2,f*.72,color.muted)
        local value=text('vital_value_'..i,'',p+width-f*6,y,f*5,f*1.2,f*.72,color.ink)
        local track=image('vital_track_'..i,p+f,y+f*1.1,barW,f*.22,color.tile)
        local fill=image('vital_fill_'..i,p+f,y+f*1.1,barW,f*.22,color[stat.id])
        hudNodes[i]={value=value,fill=fill,width=barW}
        for _,node in ipairs{label,value,track,fill} do content[#content+1]=node end
    end
    content[#content+1]=image('aim',g.w/2-1,g.h/2-1,2,2,color.ink,.8)
    hudLayout={name='RezeroHud',type=ui.TYPE.Widget,layer=hudLayer,props={size=V(g.w,g.h)},content=ui.content(content)}
    hud=ui.create(hudLayout)
end
local function refreshHud()
    if not hud then return end
    hudLayout.props.visible=I.UI.getMode()==nil
    for i,stat in ipairs(data.vitals()) do
        hudNodes[i].value.props.text=string.format('%.0f / %.0f',stat.current,stat.maximum)
        hudNodes[i].fill.props.size=V(hudNodes[i].width*math.max(0,math.min(1,stat.maximum>0 and stat.current/stat.maximum or 0)),hudNodes[i].fill.props.size.y)
    end
    hud:update()
end
local function hide() visible,pending=false,false;hovered=nil;destroy() end
local function show()
    if I.UI.getMode()~=I.UI.MODE.Interface then ui._setWindowDisabled(I.UI.WINDOW.Inventory,false);hide();return end
    ui._setWindowDisabled(I.UI.WINDOW.Inventory,true)
    visible,pending=true,true;read()
    if canvas(layerName) then build();refresh() end
end
configure=function()
    assert(I.UI.version==3,'REZERO requires bound OpenMW UI interface 3')
    hide();I.UI.registerWindow(I.UI.WINDOW.Inventory,show,hide)
    I.UI.setPauseOnMode(I.UI.MODE.Interface,false)
    if not layerRequested then ui.layers.insertAfter('Windows',layerName,{interactive=true});layerRequested=true end
    if not hudRequested then ui.layers.insertAfter('HUD',hudLayer,{interactive=false});hudRequested=true end
    I.UI.setHudVisibility(false)
end
local function state()
    local items={}
    for _,entry in ipairs(filtered) do items[#items+1]={id=entry.id,recordId=entry.recordId,name=entry.name,kind=entry.kind,count=entry.count,equipped=entry.equipped} end
    local previewEntry=find(hovered) or find(selected)
    return {version='0.1.0',visible=visible,tab=tab,category=category,query=query,page=page,selected=selected,previewId=hovered,
        previewRecordId=previewEntry and previewEntry.recordId or nil,previewDescription=previewEntry and data.description(previewEntry) or nil,
        entryCount=#entries,filteredCount=#filtered,items=items,geometry=geometry,revision=revision,
        nativeClickEvents=nativeClicks,hoverEvents=nativeHovers,nativeSearchEvents=nativeQueries,nativeStockInventoryVisible=ui._isWindowVisible(I.UI.WINDOW.Inventory),
        hudSource='ACTOR_DYNAMIC_STATS',hudScope='VITALS_AND_RETICLE',mode=I.UI.getMode()}
end
return {interfaceName='RezeroUI',interface={version='0.1.0',getState=state,configure=configure,selectTab=switch,setCategory=setCategory,
    setQuery=setQuery,select=choose,preview=preview,previewItem=preview,activateSelected=activate,refresh=function()read();refresh()end,
    dispatchClick=function(name)if visible and handlers[name] then handlers[name]();return true end;return false end},
    engineHandlers={onInit=configure,onLoad=configure,onFrame=function()
        local now=core.getRealTime()
        if not hud and canvas(hudLayer) then buildHud() end
        if visible and pending and canvas(layerName) then build();refresh() end
        if root then
            local size=canvas(layerName)
            if size and (math.floor(size.x)~=geometry.w or math.floor(size.y)~=geometry.h) then build();refresh();buildHud() end
            if now-lastData>.5 then read();refresh() end
        end
        if now-lastVitals>.12 then lastVitals=now;refreshHud() end
    end}}
