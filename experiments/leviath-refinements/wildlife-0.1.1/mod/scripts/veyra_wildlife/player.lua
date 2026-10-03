-- SPDX-License-Identifier: MIT
-- Optional owner control, nonmodal messages only. This script creates no actor.
local core=require('openmw.core')
local self=require('openmw.self')
local input=require('openmw.input')
local ui=require('openmw.ui')
local I=require('openmw.interfaces')
local cached,lastStatus,sequence,pending,hint,lastNotice={phase='CONNECTING'},-100,0,nil,true,nil
local function notice(message)
    lastNotice=message;ui.showMessage(message)
end
local function help()
    if cached.enabled then
        if cached.phase=='WAIT_FRONTIER'then
            notice('Hirschbewegung AN: wartet im eigenen Frontier-Wald. [U] ausschalten.')
        else notice('Hirschbewegung AN. [U] ausschalten; der gespeicherte Hirsch bleibt erhalten.')end
    else notice('Hirschbewegung AUS. [U] einschalten. Ein gespeicherter Hirsch bleibt erhalten.')end
end
local function setEnabled(value)
    if type(value)~='boolean' or cached.phase=='CONNECTING' or pending then return false end
    if I.UI.getMode()~=nil or core.isWorldPaused()then return false end
    sequence=sequence+1;pending={id=sequence,at=core.getRealTime()}
    core.sendGlobalEvent('VEYRA_WildUserSet',{player=self.object,enabled=value,requestId=sequence})
    return true
end
local function toggle()return setEnabled(not cached.enabled)end
local function reset()cached={phase='CONNECTING'};lastStatus=-100;pending=nil;hint=true;lastNotice=nil end
return {interfaceName='VeyraWildlifePlayer',interface={version='0.1.1',toggle=toggle,
    setEnabled=setEnabled,showHelp=help,getState=function()
        local copy={};for k,v in pairs(cached)do copy[k]=v end
        copy.pending=pending~=nil;copy.lastNotice=lastNotice;return copy
    end},engineHandlers={onInit=reset,onLoad=reset,onFrame=function()
        if not self.cell then return end
        local now=core.getRealTime()
        if pending and now-pending.at>5 then pending=nil;notice('Hirsch-Anfrage ohne Antwort. Zustand wird erneut gelesen.')end
        if now-lastStatus>1 then lastStatus=now;core.sendGlobalEvent('VEYRA_WildUserStatusRequest',{player=self.object})end
    end,onKeyPress=function(key)
        if key.code==input.KEY.U and I.UI.getMode()==nil then toggle()end
    end},eventHandlers={VEYRA_WildUserStatus=function(data)
        if type(data)~='table' or data.version~='0.1.1' or type(data.enabled)~='boolean'then return end
        -- A background status reply does not acknowledge an in-flight command.
        cached=data
        if data.kind=='USER_RESULT' and pending and data.requestId==pending.id then
            pending=nil
            if data.accepted then help()else notice('Hirsch-Zustand angehalten: '..tostring(data.phase)..'. Referenz bleibt erhalten.')end
        elseif hint then hint=false;help()end
    end}}
