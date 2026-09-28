-- Explicit in-game consent gate for local German speech-to-text.
-- This Lua module never opens an audio device. The companion does so only
-- after receiving an explicit current-session Yes event from /mikrofon.
local core = require('openmw.core')
local self = require('openmw.self')
local ui = require('openmw.ui')
local util = require('openmw.util')
local async = require('openmw.async')
local I = require('openmw.interfaces')
local input = require('openmw.input')
local vfs = require('openmw.vfs')
local markup = require('openmw.markup')
local C = require('scripts.halveth.common')

local panel, addedMode, priorMode = nil, false, nil
local state, session, lastHeartbeat, lastStatusPoll = 'undecided', nil, -100, -100

local function currentSession()
    local id = I.HALVETH and I.HALVETH.getSessionId and I.HALVETH.getSessionId() or nil
    return C.validId(id) and id or nil
end

local function emit(enabled)
    local id = currentSession()
    if not id then return false end
    if enabled then
        -- Establish this exact session before the consent event. A click in
        -- the first seconds cannot be accidentally applied to a prior world.
        local ok, context = pcall(I.HALVETH.getContext)
        if not ok or type(context) ~= 'table' then return false end
        C.emit({type='context', sessionId=id, context=context})
    end
    C.emit({type='microphone', sessionId=id, enabled=enabled})
    session = id
    return true
end

local function close()
    if panel then panel:destroy();panel=nil end
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    priorMode=nil
end

local function button(label,x,y,w,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,40),autoSize=false,text=label,textSize=20},
        events={mouseClick=async:callback(fn)}}
end

local function decline()
    if state=='starting' or state=='listening' then emit(false) end
    state='declined'
    close()
    ui.showMessage('Mikrofon aus. Du kannst weiterhin alles schreiben.')
end

local function accept()
    if not emit(true) then
        ui.showMessage('Der Spielkontext wird vorbereitet. Bitte gleich erneut versuchen.')
        return
    end
    state='starting'
    lastHeartbeat=-100
    close()
    ui.showMessage('Lokale Spracherkennung angefordert. /mikrofon zeigt den Zustand.')
end

local function open()
    if panel then close();return end
    priorMode=I.UI.getMode()
    if not priorMode then I.UI.addMode('Interface',{windows={}});addedMode=true end
    local screen=ui.screenSize()
    local w=math.min(900,screen.x-40)
    local h=math.min(430,screen.y-40)
    local live=state=='starting' or state=='listening'
    local description = live and
        'Mikrofon für diese Sitzung freigegeben. Gesprochenes erscheint als Text in F8.' or
        'Darf HALVETH für diese Spielsitzung das Systemmikrofon lokal nutzen?'
    local detail='Erkanntes Deutsch wird lokal als Text gespeichert.\n'
        ..'Pfad: .local/microphone im Spielprofil.\n'
        ..'Es entsteht keine Audiodatei. Keine Cloud-Übertragung.\n'
        ..'Fragen an Jarvis oder Halveth erhalten Textantworten.\n'
        ..'Ohne Ja bleibt das Mikrofon geschlossen.\n'
        ..'Bei jedem Spielstart ist die Freigabe aus; /mikrofon fragt bei Bedarf.'
    local content={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
            props={position=util.vector2(24,22),size=util.vector2(w-48,42),autoSize=false,
                text='HALVETH · MIKROFON',textSize=28}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(24,78),size=util.vector2(w-48,50),autoSize=false,
                wordWrap=true,text=description,textSize=21}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
            props={position=util.vector2(24,140),size=util.vector2(w-48,h-230),autoSize=false,
                wordWrap=true,text=detail,textSize=19}},
        button(live and '[Mikrofon stoppen]' or '[Ja, lokal mithören]',24,h-65,280,live and decline or accept),
        button(live and '[Schliessen]' or '[Nein, ohne Mikrofon]',w-310,h-65,280,live and close or decline),
    }
    panel=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},
        content=ui.content(content)}
end

local function reset()
    if session and (state=='starting' or state=='listening') then
        -- Loading another world revokes the previous consent immediately.
        -- Use the bound old session, which may differ from currentSession().
        C.emit({type='microphone',sessionId=session,enabled=false})
    end
    close()
    state, session = 'undecided', nil
    lastHeartbeat,lastStatusPoll=-100,-100
end

local function pollStatus()
    local id=currentSession()
    if not id or (session and id~=session) then return end
    local ok,result=pcall(function()
        local f=vfs.open('bridge/microphone-status.json')
        if not f then return nil end
        local bytes=f:read(513);f:close()
        if not bytes or #bytes>512 then return nil end
        return markup.decodeYaml(bytes)
    end)
    if not ok or type(result)~='table' or result.sessionId~=id then return end
    if result.state=='listening' and state=='starting' then
        state='listening';ui.showMessage('Mikrofon hört jetzt lokal zu. /mikrofon stoppt es.')
    elseif result.state=='unavailable' and (state=='starting' or state=='listening') then
        state='unavailable';ui.showMessage('Deutsche Spracherkennung oder Mikrofon ist nicht verfügbar. Schreiben bleibt möglich.')
    elseif result.state=='disabled' and state=='listening' then
        state='declined';ui.showMessage('Mikrofon ausgeschaltet. Mit /mikrofon erneut entscheiden.')
    end
end

local function frame()
    if not self.cell then return end
    local now=core.getRealTime()
    local id=currentSession()
    if session and id and id~=session then reset() end
    if state=='starting' or state=='listening' then
        if id and now-lastHeartbeat>=2 then
            C.emit({type='microphone_heartbeat',sessionId=id})
            lastHeartbeat=now
        end
    end
    if now-lastStatusPoll>=.5 then lastStatusPoll=now;pollStatus() end
    if panel and I.UI.getMode()~=priorMode and not addedMode then close() end
end

return {interfaceName='HALVETHMicrophone',
    interface={version=1,open=open,close=close,decline=decline,
        getState=function() return state end,isOpen=function() return panel~=nil end},
    engineHandlers={onInit=reset,onLoad=reset,onFrame=frame,
        onKeyPress=function(key) if panel and key.code==input.KEY.Escape then decline() end end},
}
