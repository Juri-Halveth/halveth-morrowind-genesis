-- Player-side control and sparse text moments for HALVETH-owned citizens.
local core=require('openmw.core')
local self=require('openmw.self')
local ui=require('openmw.ui')
local I=require('openmw.interfaces')

local sequence,lastPoll,lastMomentAt=0,-100,-100000
local state={people={},retiredCount=0,pending=false,message='Noch keine eigenen Buerger gerufen.'}

local function request(command)
    if not ({spawn=true,dismiss=true,status=true})[command] then return false end
    sequence=sequence+1
    core.sendGlobalEvent('HALVETH_CitizensRequest',{player=self.object,
        requestId='citizens-'..sequence,command=command})
    return true
end

local function result(data)
    if type(data)~='table' or type(data.people)~='table' or #data.people>2 then return end
    state={people=data.people,retiredCount=data.retiredCount or 0,
        pending=data.pending==true,message=data.message or '',success=data.success==true}
    if I.HALVETHWorldlife and I.HALVETHWorldlife.isOpen() then
        I.HALVETHWorldlife.refresh()
    end
end

local function moment(data)
    if type(data)~='table' or type(data.actorId)~='string'
        or type(data.name)~='string' or type(data.line)~='string' then return end
    local known=false
    for _,person in ipairs(state.people) do
        if person.actorId==data.actorId and person.loaded then known=true;break end
    end
    if not known or #data.name>80 or #data.line>180 then return end
    if I.UI and I.UI.getMode() and I.UI.getMode()~='Interface' then return end
    local now=core.getRealTime()
    if now-lastMomentAt<80 then return end
    lastMomentAt=now
    pcall(ui.showMessage,data.name..': '..data.line,{showInDialogue=false})
end

return {interfaceName='HALVETHCitizens',interface={version=1,
        spawn=function()return request('spawn')end,
        dismiss=function()return request('dismiss')end,
        refresh=function()return request('status')end,
        getState=function()return state end},
    engineHandlers={onLoad=function()
        sequence,lastPoll,lastMomentAt=0,-100,-100000
        state={people={},retiredCount=0,pending=false,message='Eigene Buerger werden im Spielstand geprueft.'}
    end,onFrame=function()
        if self.cell and core.getRealTime()-lastPoll>2 then
            lastPoll=core.getRealTime();request('status')
        end
    end},eventHandlers={HALVETH_CitizensResult=result,HALVETH_CitizensMoment=moment}}
