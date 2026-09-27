local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local vfs=require('openmw.vfs')
local markup=require('openmw.markup')
local input=require('openmw.input')
local camera=require('openmw.camera')
local C=require('scripts.halveth.common')
local inspect=require('scripts.halveth.inspect')

local sessionId, worldId, ready, counter = nil,nil,false,0
local lastSequence,lastPoll,lastContext,lastRegister=0,-100,-100,-100
local seen, received, healed={}, {}, {}
local window,inputLayout,transcriptLayout,statusLayout,itemLayout,filterLayout,windowMode,artworkPath
local inputText,transcript='','HALVETH ist da. Die Welt hoert zu.\n\nStelle eine Frage zur Welt, zu einer Figur oder zu deinem Weg.\nWaehle unten einen Gegenstand oder ein Buch und fuege es deiner Frage bei.\nMit /hilfe siehst du die direkten Spielbefehle.'
local dialogueTarget,lastBook,hasAddedMode=nil,nil,false
local entityMode='jarvis'
local pendingChat=nil
local chooseMode
local close
local inventoryItems,inventoryIndex,inventoryFilter,attachedItemId,attachedReference={},1,'all',nil,nil
local ink=util.color.rgb(.96,.94,.86)
local pearl=util.color.rgb(.78,.91,.98)
local gold=util.color.rgb(1,.79,.45)
local rose=util.color.rgb(1,.58,.77)
local violet=util.color.rgb(.76,.68,1)
local cyan=util.color.rgb(.47,.92,.98)
local mint=util.color.rgb(.57,1,.75)

local function companionOffline()
    local ok,status=pcall(function()
        local f=vfs.open('bridge/companion-status.json')
        if not f then return nil end
        local bytes=f:read(257);f:close()
        if not bytes or #bytes>256 then return nil end
        local data=markup.decodeYaml(bytes)
        return type(data)=='table' and data.status or nil
    end)
    return ok and status=='offline'
end

local function append(text)
    transcript=C.tail(transcript..'\n\n'..text,18000)
    if transcriptLayout then transcriptLayout.props.text=transcript end
    if window then window:update() end
end

local function refreshInventory()
    local selected=inventoryItems[inventoryIndex] and inventoryItems[inventoryIndex].id
    local list,seen={},{}
    for _,object in ipairs(types.Actor.inventory(self):getAll()) do
        local id=object.recordId
        if type(id)=='string' and not seen[id] and (inventoryFilter=='all' or types.Book.objectIsInstance(object)) then
            local ok,record=pcall(function() return object.type.record(object) end)
            if ok and record then
                seen[id]=true
                local kind=inspect.kind(object)
                list[#list+1]={id=id,name=record.name or id,kind=kind}
            end
        end
    end
    table.sort(list,function(a,b)
        if a.name==b.name then return a.id<b.id end
        return a.name<b.name
    end)
    inventoryItems=list
    inventoryIndex=1
    for index,item in ipairs(list) do if item.id==selected then inventoryIndex=index;break end end
end

local function refreshItemLabel()
    if itemLayout then
        local item=inventoryItems[inventoryIndex]
        itemLayout.props.text=item and (tostring(inventoryIndex)..'/'..#inventoryItems..'  '..C.head(item.name,90)..' · '..item.kind)
            or 'Kein passender Gegenstand im Inventar'
    end
    if filterLayout then filterLayout.props.text=inventoryFilter=='all' and '[Alle]' or '[Buecher]' end
    if window then window:update() end
end

local function cycleItem(step)
    refreshInventory()
    if #inventoryItems>0 then inventoryIndex=(inventoryIndex-1+step)%#inventoryItems+1 end
    refreshItemLabel()
end

local function selectInventoryItem(id)
    if type(id)~='string' then return false end
    refreshInventory()
    for index,item in ipairs(inventoryItems) do
        if item.id==id then inventoryIndex=index;refreshItemLabel();return true end
    end
    refreshItemLabel()
    return false
end

local function insertItem()
    refreshInventory()
    local item=inventoryItems[inventoryIndex]
    if not item then append('Im Inventar ist gerade kein passender Gegenstand.');return false end
    attachedItemId=item.id
    local reference='[Inventar: '..C.head(item.name:gsub('[%z\1-\31]',' '),96)..']'
    if attachedReference then
        local at=inputText:find(attachedReference,1,true)
        if at then inputText=inputText:sub(1,at-1)..inputText:sub(at+#attachedReference) end
    end
    attachedReference=reference
    if inputText:match('^%s*$') then
        inputText='Was ist das und wie kann ich es in Morrowind verwenden? '..reference
    elseif not inputText:find(reference,1,true) then
        inputText=C.head(inputText,3700)..' '..reference
    end
    if inputLayout then inputLayout.props.text=inputText end
    append('EINGEFUEGT: '..item.name..' · echte Inventardaten werden der Frage beigefuegt.')
    return true
end

local function insertNamedItem(query,booksOnly)
    if type(query)~='string' or #query>120 or query:match('^%s*$') then
        append('Bitte einen kurzen Gegenstandsnamen eingeben. Beispiel: /gegenstand Glasblatt')
        return false
    end
    inventoryFilter=booksOnly and 'books' or 'all'
    refreshInventory()
    local needle=query:lower()
    for index,item in ipairs(inventoryItems) do
        if item.name:lower():find(needle,1,true) or item.id:lower():find(needle,1,true) then
            inventoryIndex=index
            refreshItemLabel()
            return insertItem()
        end
    end
    refreshItemLabel()
    append('Kein passender '..(booksOnly and 'Text' or 'Gegenstand')..' im aktuellen Inventar: '..C.head(query,120))
    return false
end

local function selectedItemContext()
    if not attachedItemId then return nil end
    local inventory=types.Actor.inventory(self)
    local object=inventory:find(attachedItemId)
    if not object or not object:isValid() then return nil end
    local record=object.type.record(object)
    local kind=inspect.kind(object)
    local details={id=object.recordId,name=C.head(record.name or object.recordId,256),kind=kind,
        count=inventory:countOf(object.recordId),description=C.head(inspect.item(object,self),2400)}
    if types.Book.objectIsInstance(object) then
        local book=types.Book.record(object)
        details.book={title=C.head(book.name or object.recordId,256),
            text=C.head(book.text or '',5000),truncated=#(book.text or '')>5000}
    end
    return details
end
local function state(actor)
    local out=inspect.actor(actor,self)
    out.worldId=worldId
    out.position=C.position(actor.position)
    return out
end
local function context()
    local player=state(self)
    player.kind='player'
    for _,key in ipairs({'health','magicka','fatigue'}) do
        local stat=types.Actor.stats.dynamic[key](self)
        player[key]={current=stat.current,max=stat.base+stat.modifier}
    end
    player.gold=types.Actor.inventory(self):countOf('gold_001')
    local actors=C.array()
    for _,actor in ipairs(nearby.actors) do
        if actor.id~=self.id and actor:isValid() then
            local ok,s=pcall(state,actor)
            if ok then s.distance=(actor.position-self.position):length();actors[#actors+1]=s end
        end
    end
    table.sort(actors,function(a,b) return a.distance<b.distance end)
    while #actors>12 do table.remove(actors) end
    local npc,method=nil,'nearest_actor'
    local rayOK,ray=pcall(function()
        local from=camera.getPosition()
        local direction=camera.viewportToWorldVector(util.vector2(.5,.5)):normalize()
        return nearby.castRay(from,from+direction*1500,{ignore=self})
    end)
    if rayOK and ray.hitObject and types.Actor.objectIsInstance(ray.hitObject) then
        local ok,s=pcall(state,ray.hitObject)
        if ok then npc=s;method='crosshair_actor' end
    end
    if dialogueTarget and dialogueTarget:isValid() and (dialogueTarget.position-self.position):length()<=3000 then
        local ok,s=pcall(state,dialogueTarget)
        if ok then npc=s;method='dialogue_target' end
    end
    npc=npc or actors[1]
    local quests=C.array()
    for id,q in pairs(types.Player.quests(self)) do
        quests[#quests+1]={id=id,stage=q.stage}
    end
    table.sort(quests,function(a,b) return a.id<b.id end)
    while #quests>100 do table.remove(quests) end
    local worldlife=I.HALVETHWorldlife and I.HALVETHWorldlife.getContext(npc and npc.kind=='npc' and npc.id or nil) or nil
    local origin=I.HALVETHOrigin and I.HALVETHOrigin.getState() or nil
    local heart=I.HALVETHHeart and I.HALVETHHeart.getState() or nil
    local viewpoint=I.HALVETHPerspective and I.HALVETHPerspective.getState() or nil
    return {worldId=worldId,player=player,npc=npc,selectionMethod=method,nearby=actors,quests=quests,
        worldlife=worldlife,origin=origin,heart=heart,viewpoint=viewpoint,
        book=lastBook,anchors={{id='session_start',label='Startpunkt dieser Sitzung'}},
        engine={apiRevision=core.API_REVISION},gameTime=core.getGameTime()}
end
local function emitContext()
    if not sessionId or not ready or not self.cell then return end
    local ok,c=pcall(context)
    if ok then C.emit({type='context',sessionId=sessionId,context=c})
    else print('HALVETH context error: '..tostring(c)) end
end
local function startSession()
    sessionId=string.format('omw-%d-%d-%d',os.time(),math.floor(core.getRealTime()*1000)%1000000000,math.random(100000,999999))
    ready=false;worldId=nil;counter=0;lastSequence=0;seen={};received={};healed={};pendingChat=nil
    lastPoll=-100;lastContext=-100;lastRegister=-100;dialogueTarget=nil;lastBook=nil
    attachedItemId=nil;attachedReference=nil;inventoryItems={};inventoryIndex=1;inventoryFilter='all'
end
local function requestAction(kind,params,id)
    if not ready then append('Die Weltverbindung wird vorbereitet. Bitte gleich erneut versuchen.');return false end
    counter=counter+1
    id=id or ('ui-'..sessionId..'-'..counter)
    if not C.validId(id) then return false end
    if seen[id] then
        if received[id] then C.emit(received[id]) end
        return false
    end
    seen[id]=true
    core.sendGlobalEvent('HALVETH_Action',{player=self.object,sessionId=sessionId,action={id=id,kind=kind,params=params or {}}})
    return true
end
local function clearInput()
    inputText=''
    attachedItemId=nil
    attachedReference=nil
    if inputLayout then inputLayout.props.text='' end
    if window then window:update() end
end

local citizenCommands={
    ['/buerger rufen']='spawn',['/bürger rufen']='spawn',
    ['/buerger entfernen']='dismiss',['/bürger entfernen']='dismiss',
    ['/buerger status']='status',['/bürger status']='status',
}

local function citizenCommand(kind)
    local citizens=I.HALVETHCitizens
    if not citizens then append('Die neuen Buerger sind in dieser Installation noch nicht vorhanden.');return end
    if kind=='status' then
        citizens.refresh()
        local state=citizens.getState()
        local people=type(state)=='table' and type(state.people)=='table' and state.people or {}
        local names={}
        for _,person in ipairs(people) do
            if type(person)=='table' and type(person.name)=='string' then
                names[#names+1]=C.head(person.name,80)
            end
        end
        append('BUERGER · letzter Weltstand: '..#people..' aktiv'
            ..(#names>0 and (' · '..table.concat(names,', ')) or '')
            ..'. Die Welt aktualisiert den Stand gleich erneut.')
        return
    end
    local accepted=kind=='spawn' and citizens.spawn() or citizens.dismiss()
    if accepted then
        append(kind=='spawn' and 'BUERGER · Ruf an die Welt gesendet. Draußen koennen zwei eigene Bewohner erscheinen; /buerger status zeigt ihren Stand.'
            or 'BUERGER · Entfernen angefordert. /buerger status zeigt den folgenden Weltstand.')
    else
        append('BUERGER · Der Weltauftrag konnte gerade nicht gesendet werden.')
    end
end

local function command(text)
    if text=='/hilfe' then
        append('KONSOLE: Frage frei nach Welt, Figur, Gegenstand oder Buch. '
            ..'Ein Inventarobjekt unten waehlen und mit [Einfuegen] beifuegen. '
            ..'Direkte Befehle: /heilen · /gold 250 · /startpunkt · /zurueck · '
            ..'/npc · /jarvis · /buch · /mikrofon. '
            ..'Eigene Bewohner: /buerger rufen · /buerger entfernen · /buerger status. '
            ..'Suchen: /gegenstand NAME oder /buch NAME. '
            ..'Nur diese geprueften Spielaktionen werden ausgefuehrt.')
    elseif text=='/heilen' then
        requestAction('heal_player',{})
    elseif text=='/gold' or text:match('^/gold %d+$') then
        local amount=tonumber(text:match('^/gold (%d+)$') or '250')
        if amount and amount>=1 and amount<=100000 then requestAction('give_gold',{amount=amount})
        else append('Goldbetrag: ganze Zahl von 1 bis 100000. Beispiel: /gold 250') end
    elseif text=='/startpunkt' then
        requestAction('teleport_anchor',{anchor='session_start'})
    elseif text=='/zurueck' then
        requestAction('return_anchor',{})
    elseif text=='/npc' then
        chooseMode('npc')
    elseif text=='/jarvis' then
        chooseMode('jarvis')
    elseif text=='/buch' then
        inventoryFilter=inventoryFilter=='all' and 'books' or 'all'
        refreshInventory();refreshItemLabel()
    elseif text=='/mikrofon' then
        if I.HALVETHMicrophone then close();I.HALVETHMicrophone.open()
        else append('Die Mikrofon-Einwilligung ist in dieser Installation noch nicht vorhanden.') end
    elseif citizenCommands[text] then
        citizenCommand(citizenCommands[text])
    else
        append('Unbekannter Befehl. /hilfe zeigt die verfuegbaren Aktionen. Freie Fragen ohne / gehen an den lokalen Begleiter.')
    end
end

local function submit()
    local text=inputText:match('^%s*(.-)%s*$')
    if #text==0 then return end
    if text=='/gegenstand' then clearInput();insertItem();return end
    local itemQuery=text:match('^/gegenstand%s+(.+)$')
    if itemQuery then clearInput();insertNamedItem(itemQuery,false);return end
    local bookQuery=text:match('^/buch%s+(.+)$')
    if bookQuery then clearInput();insertNamedItem(bookQuery,true);return end
    if text:sub(1,1)=='/' then command(text);clearInput();return end
    if not ready then append('Die Weltverbindung wird vorbereitet. Bitte gleich erneut versuchen.');return end
    if companionOffline() then append('Der lokale Gespraechsbegleiter ist gerade offline. Wissen, Buecher und alle direkten Spielwerkzeuge bleiben nutzbar.');return end
    if pendingChat then append('Deine vorige Antwort entsteht noch.');return end
    if #text>16000 or (utf8.len(text) or #text)>4000 then append('Bitte maximal 4000 Zeichen pro Nachricht.');return end
    counter=counter+1
    local ok,c=pcall(context)
    if not ok then append('Weltkontext wird gerade geladen.');return end
    if attachedItemId then
        local itemOK,item=pcall(selectedItemContext)
        if not itemOK or not item then
            attachedItemId=nil
            attachedReference=nil
            append('Der eingefuegte Gegenstand liegt nicht mehr in deinem Inventar. Waehle ihn erneut.')
            return
        end
        c.selectedInventoryItem=item
    end
    if entityMode=='npc' and not c.npc then append('Im aktuellen Kontext ist kein Wesen ausgewaehlt.');return end
    local requestId='chat-'..sessionId..'-'..counter
    pendingChat={id=requestId,startedAt=core.getRealTime()}
    C.emit({type='chat',sessionId=sessionId,requestId=requestId,entityMode=entityMode,text=text,context=c})
    self:sendEvent('HALVETH_ChatSubmitted',{sessionId=sessionId,requestId=requestId,text=text,contextJson=C.json(c)})
    if entityMode=='npc' and dialogueTarget and I.HALVETHPaths then I.HALVETHPaths.noteNpc(dialogueTarget) end
    append('DU: '..text)
    attachedItemId=nil
    attachedReference=nil
    clearInput()
end
close=function()
    if window then window:destroy();window=nil end
    inputLayout=nil;transcriptLayout=nil;statusLayout=nil;itemLayout=nil;filterLayout=nil
    if hasAddedMode then I.UI.removeMode('Interface');hasAddedMode=false end
    windowMode=nil;artworkPath=nil
end
local function button(label,x,y,width,fn,color)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(width,46),text=label,textSize=25,
            textColor=color or pearl},
        events={mouseClick=async:callback(fn)}}
end
chooseMode=function(mode)
    entityMode=mode
    if statusLayout then
        local ok,c=pcall(context)
        local name=ok and c.npc and c.npc.name or 'kein Wesen in der Naehe'
        statusLayout.props.text=mode=='jarvis' and 'JARVIS · dein lokaler Weltbegleiter' or ('WESEN · '..name)
        if window then window:update() end
    end
end
local function open()
    if window then close();return end
    if I.HALVETHMicrophone and I.HALVETHMicrophone.isOpen and I.HALVETHMicrophone.isOpen() then
        ui.showMessage('Bitte entscheide zuerst im Mikrofonfenster. Danach oeffnet F8 die Konsole.')
        return
    end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    windowMode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});hasAddedMode=true end
    local size=ui.screenSize()
    local width=math.min(1480,size.x-36)
    -- Keep the console clear of bottom-centred gameplay notifications at 720p.
    local height=math.min(940,math.max(680,math.floor(size.y*.69)))
    height=math.min(height,size.y-36)
    refreshInventory()
    -- This is one native OpenMW window. Artwork never replaces the readable transcript.
    local banner
    if width>=1100 and height>=760 then
        for _,artPath in ipairs({'textures/halveth/love-astrolabe-0.7.png',
                                  'textures/halveth/scarlet-love-banner.png'}) do
            local ok,resource=pcall(function()
                if not vfs.fileExists(artPath) then return nil end
                return ui.texture{path=artPath}
            end)
            if ok and resource then banner=resource;artworkPath=artPath;break end
        end
    end
    local cardWidth=width-40
    local cardHeight=height-431
    local artWidth=banner and math.min(170,(cardHeight-26)/2) or 0
    local transcriptWidth=cardWidth-28-(banner and artWidth+22 or 0)
    transcriptLayout={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(14,12),size=util.vector2(transcriptWidth,cardHeight-24),text=transcript,
            textSize=31,textColor=ink,readOnly=true,multiline=true,wordWrap=true}}
    inputLayout={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditLine,
        props={position=util.vector2(12,10),size=util.vector2(width-237,43),
            autoSize=false,text=inputText,textSize=31,textColor=ink},
        events={textChanged=async:callback(function(text) inputText=text end),
            keyPress=async:callback(function(key) if key.code==input.KEY.Enter then submit() end end)}}
    statusLayout={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(24,101),size=util.vector2(width-48,33),
            text=entityMode=='jarvis' and 'JARVIS · dein lokaler Weltbegleiter'
                or 'WESEN · Dialogziel, Fadenkreuz oder naechstes Wesen',
            textSize=26,textColor=pearl}}
    itemLayout={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(555,height-278),size=util.vector2(width-580,44),
            text='',textSize=26,textColor=ink}}
    filterLayout=button('',24,height-278,152,function()
        inventoryFilter=inventoryFilter=='all' and 'books' or 'all'
        refreshInventory();refreshItemLabel()
    end,violet)
    local conversation={transcriptLayout}
    if banner then
        conversation[#conversation+1]={type=ui.TYPE.Image,name='scarletLoveBanner',
            props={position=util.vector2(cardWidth-artWidth-14,13),
                size=util.vector2(artWidth,artWidth*2),resource=banner}}
    end
    local contents={
            {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
                props={position=util.vector2(24,18),text='VERACHEL / MORROWIND',textSize=36,textColor=gold}},
            button('[JARVIS]',width-392,20,150,function() chooseMode('jarvis') end,cyan),
            button('[WESEN]',width-220,20,130,function() chooseMode('npc') end,mint),
            button('[X]',width-70,20,48,close,rose),
            statusLayout,
            {type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,
                props={position=util.vector2(20,137),size=util.vector2(cardWidth,cardHeight)},
                content=ui.content(conversation)},
            filterLayout,
            button('[<]',190,height-278,62,function() cycleItem(-1) end,cyan),
            button('[>]',268,height-278,62,function() cycleItem(1) end,cyan),
            button('[Einfuegen]',346,height-278,190,insertItem,mint),
            itemLayout,
            {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
                props={position=util.vector2(24,height-210),size=util.vector2(width-48,34),
                    text='DEINE FRAGE ODER EIN SPIELBEFEHL  ·  /hilfe',textSize=25,textColor=gold}},
            {type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,
                props={position=util.vector2(24,height-172),size=util.vector2(width-205,64)},
                content=ui.content{inputLayout}},
            button('[ABSCHICKEN]',width-163,height-157,151,submit,gold),
            {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
                props={position=util.vector2(24,height-80),size=util.vector2(width-48,48),
                    text='F8 / Esc schliessen   ·   F6 Figur   ·   F7 Wissen   ·   /mikrofon fuer Einwilligung',
                    textSize=23,textColor=pearl}},
        }
    local stages={'SOURCE','RECEIVE','ACCEPT','RELATE','PRESERVE','UPDATE'}
    local shades={rose,gold,mint,cyan,violet,rose}
    local step=(width-48)/#stages
    for index,title in ipairs(stages) do
        contents[#contents+1]={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(24+(index-1)*step,67),size=util.vector2(step-6,27),
                text=title,textSize=20,textColor=shades[index]}}
    end
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.46),anchor=util.vector2(.5,.5),size=util.vector2(width,height)},
        content=ui.content(contents)}
    refreshItemLabel()
    if companionOffline() then append('Gespraechsbegleiter offline. Wissen mit F7 und direkte Spielwerkzeuge funktionieren weiter.') end
    emitContext()
end
local function poll()
    if not ready then return end
    local f=vfs.open('bridge/inbox.json')
    if not f then return end
    local bytes=f:read(65537);f:close()
    if not bytes or #bytes>65536 then return end
    local ok,data=pcall(markup.decodeYaml,bytes)
    if not ok or type(data)~='table' then return end
    if data.sessionId~=sessionId or not C.finite(data.sequence) or data.sequence%1~=0 or data.sequence<=lastSequence or data.sequence>2147483647 then return end
    lastSequence=data.sequence
    if type(data.reply)=='string' and #data.reply<=24000 then
        if not data.requestId or (pendingChat and data.requestId==pendingChat.id) then
            local speaker=(type(data.speaker)=='string' and #data.speaker<=160) and data.speaker or 'HALVETH'
            append(speaker..': '..data.reply)
            pendingChat=nil
            local receipt={type='reply_received',sessionId=sessionId,requestId=data.requestId,
                speaker=speaker,reply=data.reply,uiOpen=window~=nil}
            C.emit(receipt)
            self:sendEvent('HALVETH_ReplyReceived',receipt)
        end
    end
    if type(data.action)=='table' and C.validId(data.action.id) and type(data.action.kind)=='string' then
        requestAction(data.action.kind,data.action.params,data.action.id)
    end
end
local function frame()
    if not self.cell then return end
    if not sessionId then startSession() end
    local now=core.getRealTime()
    if not ready and now-lastRegister>1 then
        lastRegister=now
        core.sendGlobalEvent('HALVETH_Register',{player=self.object,sessionId=sessionId})
    end
    if now-lastPoll>.25 then
        lastPoll=now
        local ok,err=pcall(poll)
        if not ok then print('HALVETH mailbox error: '..tostring(err)) end
    end
    if now-lastContext>5 then lastContext=now;emitContext() end
    if pendingChat and now-pendingChat.startedAt>180 then
        pendingChat=nil;append('Die Antwortverbindung hat noch keine Antwort geliefert. Du kannst erneut schreiben.')
    end
    if window and I.UI.getMode()~=windowMode then close() end
end
local function handleResult(data)
    if data.sessionId~=sessionId or received[data.actionId] then return end
    received[data.actionId]=data
    C.emit(data)
    append((data.success and 'WELT: ' or 'HINWEIS: ')..tostring(data.message))
    emitContext()
end
local function heal(data)
    if data.sessionId~=sessionId or healed[data.actionId] then return end
    healed[data.actionId]=true
    for _,key in ipairs({'health','magicka','fatigue'}) do
        local stat=types.Actor.stats.dynamic[key](self)
        stat.current=math.max(0,stat.base+stat.modifier)
    end
end
return {
    interfaceName='HALVETH',
    interface={version=2,open=open,close=close,isOpen=function()return window~=nil end,
        getArtworkPath=function()return window and artworkPath or nil end,
        requestAction=requestAction,getSessionId=function() return sessionId end,
        getContext=context,
        getConsoleState=function()
            local item=inventoryItems[inventoryIndex]
            return {open=window~=nil,mode=entityMode,selectedItemId=item and item.id or nil,
                attachedItemId=attachedItemId,filter=inventoryFilter,inputText=inputText}
        end,
        attachItem=function(id)
            if not window then open() end
            if not window then return false end
            if not selectInventoryItem(id) then return false end
            return insertItem()
        end,
        talkTo=function(actor)
            if not actor or not actor:isValid() or not types.Actor.objectIsInstance(actor)
                or types.Actor.isDead(actor) or (actor.position-self.position):length()>3000 then return false end
            dialogueTarget=actor
            if not window then open() end
            if not window then return false end
            chooseMode('npc')
            return true
        end},
    engineHandlers={onFrame=frame,onInit=startSession,onLoad=function() close();startSession() end,
        onKeyPress=function(key)
            if key.code==input.KEY.F8 then open() end
            if window and key.code==input.KEY.Escape then close() end
        end},
    eventHandlers={HALVETH_Ready=function(data)
            if data.sessionId==sessionId and C.validId(data.worldId) then worldId=data.worldId;ready=true;emitContext() end
        end,
        HALVETH_Result=handleResult,HALVETH_Heal=heal,
        HALVETH_TestRequest=function(data) requestAction(data.kind,data.params,data.id) end,
        HALVETH_TestOpen=open,
        HALVETH_TestChat=function(data)
            if not window then open() end
            if not window then return end
            chooseMode(data.entityMode=='npc' and 'npc' or 'jarvis')
            inputText=type(data.text)=='string' and data.text or ''
            if inputLayout then inputLayout.props.text=inputText;window:update() end
            submit()
        end,
        UiModeChanged=function(data)
            if data.newMode=='Dialogue' and data.arg then dialogueTarget=data.arg end
            if data.newMode=='Book' and data.arg then
                local ok,b=pcall(types.Book.record,data.arg)
                if ok then lastBook={id=b.id,title=b.name,text=C.head(b.text,14000),truncated=#b.text>14000} end
            end
        end},
}
