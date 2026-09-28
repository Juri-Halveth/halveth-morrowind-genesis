-- An optional romantic fiction arc driven by actual Morrowind reading and talk.
-- Sera is a character in an original letter, not an invented claim about an NPC.
local core=require('openmw.core')
local self=require('openmw.self')
local ui=require('openmw.ui')
local vfs=require('openmw.vfs')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')

local RESPONSES={come='Ich komme',question='Wer bist du?',keep='Ich bewahre das Licht'}
local phase,response,dialogueBaseline='sealed',nil,0
local window,body,addedMode,mode=nil,nil,false,nil
local pendingRequest,serial,retainedInvalidSave=nil,0,nil
local lastUpdate=0
local message='Ein versiegelter Brief wartet in dieser Welt.'
local open,refresh

local function dialogueCount()
    if not I.HALVETHWorldlife then return 0 end
    local ok,s=pcall(I.HALVETHWorldlife.getState)
    if not ok or type(s)~='table' or type(s.people)~='table' then return 0 end
    local count=0
    for _,person in ipairs(s.people) do
        if type(person.dialogues)=='number' and person.dialogues>0 then count=count+person.dialogues end
    end
    return count
end

local function bookCount()
    if not I.HALVETHKnowledge then return 0 end
    local ok,s=pcall(I.HALVETHKnowledge.getState)
    return ok and type(s)=='table' and type(s.bookCount)=='number' and s.bookCount or 0
end

local function snapshot()
    return {version=1,phase=phase,response=response,dialogueBaseline=dialogueBaseline,
        dialogueProgress=math.max(0,dialogueCount()-dialogueBaseline),
        bookCount=bookCount(),pending=pendingRequest~=nil,panelOpen=window~=nil,message=message}
end

local function close()
    if window then window:destroy();window=nil end
    body=nil
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    mode=nil
end

local function redraw()
    if window then close();open() end
end

local function begin(id)
    if retainedInvalidSave or phase~='sealed' or not RESPONSES[id] then return false end
    response=id;phase='searching';dialogueBaseline=dialogueCount()
    message='Deine Antwort steht im Brief. Sprich jetzt mit einer echten Figur und lies einen echten Text.'
    redraw()
    return true
end

local function advance()
    if retainedInvalidSave or phase~='searching' then return false end
    if dialogueCount()<=dialogueBaseline or bookCount()<1 then return false end
    phase='ready'
    message='Eine zweite Zeile erschien: Das Licht wird staerker, wenn du es teilst.'
    redraw()
    return true
end

local function claim()
    if retainedInvalidSave or phase~='ready' or pendingRequest then return false end
    serial=serial+1
    pendingRequest='heart-love-'..tostring(math.floor(core.getRealTime()*1000))..'-'..serial
    core.sendGlobalEvent('HALVETH_ContentRequest',{
        player=self.object,request='love',requestId=pendingRequest})
    message='Der Heilschein wird in dein echtes Morrowind-Zauberbuch eingetragen.'
    refresh()
    return true
end

local function contentResult(data)
    if not pendingRequest or type(data)~='table' or data.requestId~=pendingRequest then return end
    pendingRequest=nil
    if data.success and data.request=='love' then
        phase='completed'
        message='LOVE - Heilschein ist gelernt. Sera laesst ein Licht am Weg; deine naechste Begegnung bleibt deine Wahl.'
        pcall(ui.showMessage,'Herzbrief: LOVE - Heilschein gelernt. Im normalen Zaubermenue auswaehlen.')
    else
        message='Der Zauber konnte noch nicht eingetragen werden. Der Brief bleibt offen; versuche es erneut.'
    end
    redraw()
end

local function story()
    if retainedInvalidSave then return 'Ein alter Herzbrief-Stand ist inkompatibel. Seine Daten bleiben im Spielstand erhalten.' end
    if phase=='sealed' then
        return 'Im Regen liegt ein versiegelter Brief zwischen zwei Steinen. Die Schrift leuchtet nur, wenn du ihn aufhebst.\n\n'
            ..'"Ich kenne deinen Namen noch nicht. Trotzdem bleibt ein Platz am Feuer frei. Liebe ist kein Befehl; '
            ..'vielleicht kreuzen sich unsere Wege freiwillig. Wenn du dieses Licht findest, antworte mir."\n\n'
            ..'Sera, Hueterin der kleinen Lichter\n\nWelche Antwort schreibst du?'
    end
    local opening='Deine Antwort: "'..RESPONSES[response]..'"\n\n'
    if phase=='searching' then
        return opening..'Die Tinte wartet auf Spuren deiner Reise. Sprich mit einer wirklichen Figur in Morrowind '
            ..'und lies ein Buch oder eine Schriftrolle im normalen Fenster. Diese Begegnung und dieser Text '
            ..'formen die naechste Zeile.\n\nGespraeche seit deiner Antwort: '
            ..math.max(0,dialogueCount()-dialogueBaseline)..' / 1\nGelesene unterschiedliche Texte: '
            ..bookCount()..' / 1\n\nF7 zeigt die Buecher, Weltleben die beobachteten Figuren.'
    end
    if phase=='ready' then
        return opening..'Zwischen den Seiten erscheint eine zweite Zeile:\n\n'
            ..'"Du hast zugehoert, bevor du gezaubert hast. Behalte das Licht nicht fuer mich allein. '
            ..'Trage es dorthin, wo jemand Heilung braucht."\n\n'
            ..'Du kannst jetzt LOVE - Heilschein als normalen Morrowind-Zauber lernen.'
    end
    return opening..'Der Brief ist vollendet. LOVE - Heilschein liegt im normalen Zaubermenue. '
        ..'Du entscheidest selbst, wann du ihn wirkst und wem du auf deiner Reise begegnest.\n\n'
        ..'"Vielleicht sehen wir denselben Stern von zwei verschiedenen Wegen." - Sera'
end

local function button(label,x,y,w,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,32),text=label,textSize=17},
        events={mouseClick=async:callback(fn)}}
end

refresh=function()
    if body then body.props.text=story();window:update() end
end

open=function()
    if window then close();return true end
    if I.HALVETH then I.HALVETH.close() end
    if I.HALVETHKnowledge then I.HALVETHKnowledge.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHWorldlife then I.HALVETHWorldlife.close() end
    local screen=ui.screenSize()
    local w,h=math.min(880,screen.x-32),math.min(575,screen.y-32)
    if w<540 or h<390 then return false end
    mode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    local art
    local ok,resource=pcall(function()
        if vfs.fileExists('textures/halveth/love-astrolabe-0.7.png') then
            return ui.texture{path='textures/halveth/love-astrolabe-0.7.png'}
        end
    end)
    if ok then art=resource end
    body={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(22,80),size=util.vector2(w-(art and 245 or 44),h-205),
            text=story(),textSize=18,readOnly=true,multiline=true,wordWrap=true}}
    local contents={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
            props={position=util.vector2(22,16),text='HALVETH / DER HERZBRIEF',textSize=25}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(22,50),text=message,textSize=15}},
        body,
    }
    if art then
        contents[#contents+1]={type=ui.TYPE.Image,name='heartAstrolabe',
            props={position=util.vector2(w-218,89),size=util.vector2(190,330),resource=art}}
    end
    if phase=='sealed' then
        contents[#contents+1]=button('[Ich komme]',22,h-91,165,function()begin('come')end)
        contents[#contents+1]=button('[Wer bist du?]',195,h-91,180,function()begin('question')end)
        contents[#contents+1]=button('[Licht bewahren]',385,h-91,200,function()begin('keep')end)
    elseif phase=='searching' then
        contents[#contents+1]=button('[Fortschritt pruefen]',22,h-91,205,function()advance();refresh()end)
        contents[#contents+1]=button('[Weltleben]',237,h-91,150,function()close();I.HALVETHWorldlife.open()end)
        contents[#contents+1]=button('[Buecher / F7]',397,h-91,165,function()close();I.HALVETHKnowledge.open()end)
    elseif phase=='ready' then
        contents[#contents+1]=button('[LOVE lernen]',22,h-91,180,claim)
    else
        contents[#contents+1]=button('[Zauber zeigen]',22,h-91,190,function()close();I.HALVETHUniverse.open('magic')end)
    end
    contents[#contents+1]=button('[Schliessen]',w-165,h-49,145,close)
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},
        content=ui.content(contents)}
    return true
end

local function onLoad(data)
    close();phase='sealed';response=nil;dialogueBaseline=0;pendingRequest=nil;serial=0;retainedInvalidSave=nil
    message='Ein versiegelter Brief wartet in dieser Welt.'
    if data==nil then return end
    if type(data)~='table' or data.version~=1 or
        not ({sealed=true,searching=true,ready=true,completed=true})[data.phase] or
        (data.phase~='sealed' and not RESPONSES[data.response]) or
        type(data.dialogueBaseline)~='number' or data.dialogueBaseline<0 or
        data.dialogueBaseline%1~=0 or data.dialogueBaseline>1000000 then
        retainedInvalidSave=data;return
    end
    phase=data.phase;response=data.response;dialogueBaseline=data.dialogueBaseline
    message=phase=='completed' and 'Der Herzbrief ist vollendet.' or 'Der Herzbrief begleitet deine Reise.'
end

return {interfaceName='HALVETHHeart',interface={version=1,open=open,close=close,
    isOpen=function()return window~=nil end,getState=snapshot,begin=begin,advance=advance,claim=claim},
    engineHandlers={onLoad=onLoad,onSave=function()
        return retainedInvalidSave or {version=1,phase=phase,response=response,dialogueBaseline=dialogueBaseline}
    end,onFrame=function()
        if window and I.UI.getMode()~=mode then close() end
        if phase=='searching' and core.getRealTime()-lastUpdate>.5 then
            lastUpdate=core.getRealTime();advance();refresh()
        end
    end},eventHandlers={HALVETH_ContentResult=contentResult}}
