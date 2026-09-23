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
local window,inputLayout,transcriptLayout,statusLayout,windowMode
local inputText,transcript='','HALVETH ist da. F8 oeffnet dein Begleiterfenster.\nFreie Gespraeche laufen ueber den lokalen Begleiter.'
local dialogueTarget,lastBook,hasAddedMode=nil,nil,false
local entityMode='jarvis'
local pendingChat=nil

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
    return {worldId=worldId,player=player,npc=npc,selectionMethod=method,nearby=actors,quests=quests,
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
local function submit()
    local text=inputText:match('^%s*(.-)%s*$')
    if #text==0 or not ready then return end
    if companionOffline() then append('Der lokale Gespraechsbegleiter ist gerade offline. Wissen, Buecher und alle direkten Spielwerkzeuge bleiben nutzbar.');return end
    if pendingChat then append('Deine vorige Antwort entsteht noch.');return end
    if #text>16000 or (utf8.len(text) or #text)>4000 then append('Bitte maximal 4000 Zeichen pro Nachricht.');return end
    counter=counter+1
    local ok,c=pcall(context)
    if not ok then append('Weltkontext wird gerade geladen.');return end
    if entityMode=='npc' and not c.npc then append('Im aktuellen Kontext ist kein Wesen ausgewaehlt.');return end
    local requestId='chat-'..sessionId..'-'..counter
    pendingChat={id=requestId,startedAt=core.getRealTime()}
    C.emit({type='chat',sessionId=sessionId,requestId=requestId,entityMode=entityMode,text=text,context=c})
    self:sendEvent('HALVETH_ChatSubmitted',{sessionId=sessionId,requestId=requestId,text=text,contextJson=C.json(c)})
    if entityMode=='npc' and dialogueTarget and I.HALVETHPaths then I.HALVETHPaths.noteNpc(dialogueTarget) end
    append('DU: '..text)
    inputText='';inputLayout.props.text='';window:update()
end
local function close()
    if window then window:destroy();window=nil end
    inputLayout=nil;transcriptLayout=nil;statusLayout=nil
    if hasAddedMode then I.UI.removeMode('Interface');hasAddedMode=false end
    windowMode=nil
end
local function button(label,x,y,width,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(width,30),text=label,textSize=17},
        events={mouseClick=async:callback(fn)}}
end
local function chooseMode(mode)
    entityMode=mode
    if statusLayout then
        local c=context()
        statusLayout.props.text=mode=='jarvis' and 'Gespraech: JARVIS · lokaler Weltbegleiter' or ('Gespraech: '..(c.npc and c.npc.name or 'kein Wesen in der Naehe'))
        if window then window:update() end
    end
end
local function open()
    if window then close();return end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    windowMode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});hasAddedMode=true end
    local size=ui.screenSize()
    local width=math.min(1000,size.x-40)
    local height=math.min(580,size.y-40)
    -- Optional, locally installed artwork. A missing pack keeps the full chat.
    local banner
    local artPath='textures/halveth/scarlet-love-banner.png'
    local ok,resource=pcall(function()
        if not vfs.fileExists(artPath) then return nil end
        return ui.texture{path=artPath}
    end)
    if ok and resource and width>=860 and height>=510 then banner=resource end
    local artWidth=banner and math.min(160,(height-232)/2) or 0
    local transcriptWidth=width-40-(banner and artWidth+44 or 0)
    transcriptLayout={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(20,75),size=util.vector2(transcriptWidth,height-266),text=transcript,
            textSize=17,readOnly=true,multiline=true,wordWrap=true}}
    inputLayout={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditLine,
        props={position=util.vector2(8,7),size=util.vector2(width-170,28),autoSize=false,text=inputText,textSize=18},
        events={textChanged=async:callback(function(text) inputText=text end),
            keyPress=async:callback(function(key) if key.code==input.KEY.Enter then submit() end end)}}
    statusLayout={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(20,45),size=util.vector2(width-40,25),text=entityMode=='jarvis' and 'Gespraech: JARVIS · lokaler Weltbegleiter' or 'Gespraech: NPC/Wesen · Dialogziel, Fadenkreuz oder naechstes Wesen',textSize=15}}
    local contents={
            {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,props={position=util.vector2(20,15),text='HALVETH / MORROWIND GENESIS',textSize=21}},
            button('[JARVIS]',width-210,15,108,function() chooseMode('jarvis') end),
            button('[NPC]',width-95,15,85,function() chooseMode('npc') end),
            statusLayout,transcriptLayout,
            button('[Wissen / F7]',20,height-182,185,function()
                close()
                if I.HALVETHKnowledge then I.HALVETHKnowledge.open() end
            end),
            button('[Figur / Inventar / Magie · F6]',220,height-182,380,function()
                close()
                if I.HALVETHUniverse then I.HALVETHUniverse.open() end
            end),
            {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
                props={position=util.vector2(20,height-144),size=util.vector2(width-150,22),text='Deine Nachricht',textSize=15}},
            {type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,
                props={position=util.vector2(20,height-117),size=util.vector2(width-150,42)},
                content=ui.content{inputLayout}},
            button('[Senden]',width-108,height-108,94,submit),
            button('[Heilen]',20,height-57,106,function() requestAction('heal_player',{}) end),
            button('[+250 Gold]',136,height-57,137,function() requestAction('give_gold',{amount=250}) end),
            button('[Startpunkt]',280,height-57,150,function() requestAction('teleport_anchor',{anchor='session_start'}) end),
            button('[Zurueck]',437,height-57,127,function() requestAction('return_anchor',{}) end),
            button('[Schliessen]',width-155,height-57,145,close),
        }
    if banner then
        contents[#contents+1]={type=ui.TYPE.Image,name='scarletLoveBanner',
            props={position=util.vector2(width-40-artWidth,75),size=util.vector2(artWidth,artWidth*2),resource=banner}}
    end
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(width,height)},
        content=ui.content(contents)}
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
    interface={version=2,open=open,close=close,isOpen=function()return window~=nil end,requestAction=requestAction,getSessionId=function() return sessionId end,
        getContext=context,
        talkTo=function(actor)
            if not actor or not actor:isValid() or not types.Actor.objectIsInstance(actor)
                or types.Actor.isDead(actor) or (actor.position-self.position):length()>3000 then return false end
            dialogueTarget=actor
            if not window then open() end
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
