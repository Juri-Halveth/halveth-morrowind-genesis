-- SPDX-License-Identifier: MIT
-- Native local travel prompt. Primary entry is real object activation.
local core=require('openmw.core')
local self=require('openmw.self')
local ui=require('openmw.ui')
local util=require('openmw.util')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local window,prompt,addedMode=nil,nil,false
local cached={phase='CONNECTING',trips=0,gateCount=0}
local function close(cancel)
    if window then window:destroy();window=nil end
    if cancel~=false then core.sendGlobalEvent('VEYRA_PortalCancel',{player=self.object})end
    prompt=nil
    if I.VeyraPanelCoordinator then I.VeyraPanelCoordinator.release('VeyraPortalPlayer') end
    addedMode=false
end
local function confirm()
    if not prompt then return false end
    core.sendGlobalEvent('VEYRA_PortalConfirm',{player=self.object,gateId=prompt.gateId,branch=prompt.branch})
    close(false);return true
end
local function button(label,x,y,w,callback)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,34),text=label,textSize=19},
        events={mouseClick=async:callback(callback)}}
end
local function open(data)
    if type(data)~='table'or type(data.gateId)~='string'
        or (data.branch~='OUTBOUND'and data.branch~='RETURN')or type(data.target)~='string'then return end
    close(false)
    for _,name in ipairs({'VeyraFieldworkPlayer','HALVETHFieldcraft','HALVETHWorldlife','HALVETHKnowledge','HALVETHUniverse','HALVETHPaths'})do
        if I[name]and I[name].close then I[name].close()end
    end
    prompt={gateId=data.gateId,branch=data.branch}
    assert(I.VeyraPanelCoordinator,'Panel coordinator is required').acquire('VeyraPortalPlayer')
    local screen=ui.screenSize();local w,h=math.min(660,screen.x-40),330
    local detail=data.branch=='OUTBOUND'
        and 'Der Seelenstein oeffnet einen Weg zur Frontier.\nDein Standort bleibt als Rueckkehrpunkt erhalten.\n\nZiel: '..data.target
        or 'Der Seelenstein fuehrt dich zu deinem gespeicherten Rueckkehrpunkt.\n\nZiel: '..data.target
    local content={{type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,
        props={position=util.vector2(24,20),text='LEVIATH-SEELENSTEIN',textSize=25}},
        {type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
            props={position=util.vector2(24,72),size=util.vector2(w-48,165),readOnly=true,multiline=true,wordWrap=true,text=detail,textSize=19}},
        button(data.branch=='OUTBOUND'and '[Zur Frontier reisen]'or '[Zurueckreisen]',24,265,320,confirm),
        button('[Schliessen]',w-195,265,175,function()close(true)end)}
    window=ui.create({type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},content=ui.content(content)})
    print('VEYRA_PORTAL|kind=PROMPT_VISIBLE|branch='..data.branch)
end
return {interfaceName='VeyraPortalPlayer',interface={version=1,close=function()close(true)end,
        confirm=confirm,getState=function()return {status=cached,promptOpen=window~=nil,branch=prompt and prompt.branch or nil}end},
    engineHandlers={onLoad=function()close(false);cached={phase='CONNECTING',trips=0,gateCount=0}end},
    eventHandlers={VEYRA_PortalOpen=open,VEYRA_PortalStatus=function(data)cached=data end,
        VEYRA_PortalNotice=function(data)if data and data.message then ui.showMessage(data.message)end end}}
