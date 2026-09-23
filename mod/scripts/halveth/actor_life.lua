-- Native player-side controls and status for the opt-in HALVETH ambient actor.
local core=require('openmw.core')
local self=require('openmw.self')
local I=require('openmw.interfaces')
local sequence,lastPoll=0,-100
local state={actorId=nil,recordId=nil,loaded=false,position=nil,message='Noch kein Wanderer gerufen.'}
local function request(command)
    if not ({spawn=true,pause=true,resume=true,dismiss=true,status=true})[command] then return false end
    sequence=sequence+1
    core.sendGlobalEvent('HALVETH_AmbientRequest',{player=self.object,
        requestId='ambient-'..sequence,command=command})
    return true
end
local function result(data)
    if type(data)~='table' then return end
    state={actorId=data.actorId,recordId=data.recordId,loaded=data.loaded,
        position=data.position,message=data.message,success=data.success}
end
return {interfaceName='HALVETHAmbient',interface={version=1,
        spawn=function()return request('spawn')end,
        pause=function()return request('pause')end,
        resume=function()return request('resume')end,
        dismiss=function()return request('dismiss')end,
        refresh=function()return request('status')end,
        getState=function()return state end},
    engineHandlers={onLoad=function(data)
        sequence=0;lastPoll=-100
        state=type(data)=='table' and data.version==1 and data.state
            or {actorId=nil,recordId=nil,loaded=false,position=nil,message='Noch kein Wanderer gerufen.'}
    end,onSave=function()return {version=1,state=state}end,
        onFrame=function()
            if self.cell and core.getRealTime()-lastPoll>2 then lastPoll=core.getRealTime();request('status') end
        end},
    eventHandlers={HALVETH_AmbientResult=result}}
