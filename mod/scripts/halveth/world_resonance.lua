-- Native, intentionally discovered through the existing writing console.
local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local camera=require('openmw.camera')
local util=require('openmw.util')
local ui=require('openmw.ui')
local I=require('openmw.interfaces')
local R=require('scripts.halveth.resonance_rules')
local focus,lastResult,pending=nil,nil,nil
local entryCount,sequence=0,0
local blocked=false
local inspected=false
local function trace()
    if not self.cell or not self.cell.isExterior then return nil end
    local from=camera.getPosition()
    local direction=camera.viewportToWorldVector(util.vector2(.5,.5)):normalize()
    local hit=nearby.castRenderingRay(from,from+direction*R.range,{ignore=self})
    local target=hit.hitObject
    if not target or not target:isValid() or not types.Static.objectIsInstance(target) or not hit.hitPos then return nil end
    local model,kind=R.model(types.Static.record(target).model)
    if not model or (hit.hitPos-self.position):length()>R.range then return nil end
    return {object=target,point=hit.hitPos,id=tostring(target.id),recordId=target.recordId,model=model,kind=kind}
end
local function sample()
    local ok,hit=pcall(trace)
    focus=ok and hit or nil
end
local function getState()
    local f=focus and {id=focus.id,recordId=focus.recordId,model=focus.model,kind=focus.kind,
        point={x=focus.point.x,y=focus.point.y,z=focus.point.z}} or nil
    local response=lastResult and {success=lastResult.success,status=lastResult.status,message=lastResult.message,
        entry=R.copy(lastResult.entry)} or nil
    return {version=1,focus=f,lastResult=response,entryCount=entryCount,blocked=blocked,pending=pending~=nil}
end
local function request(action)
    if action~='listen' and action~='answer' then return false,'Lauschen oder antworten?' end
    if pending then return false,'Deine vorige Antwort klingt noch nach.' end
    if blocked then return false,'Diese Erinnerung bleibt in ihrem bisherigen Stand erhalten.' end
    pending={action=action,queuedAt=core.getRealTime()}
    return true,'Du wendest dich dem Leuchten zu.'
end
local function statusText()
    if lastResult then return lastResult.message..' Gemerkte Orte: '..tostring(entryCount)..'.' end
    return 'Sieh draußen einen leuchtenden Kristall oder Baum an. /resonanz lauscht; /resonanz antworten gibt einen Gruß zurück.'
end
local function frame()
    if not inspected and self.cell then
        core.sendGlobalEvent('HALVETH_ResonanceInspect',{player=self.object});inspected=true
    end
    if pending and pending.sent and core.getRealTime()-pending.queuedAt>8 then
        pending=nil;ui.showMessage('Der Ort hat noch nicht geantwortet.',{showInDialogue=false})
    end
    if pending and not pending.sent then
        -- Rendering rays run on the main-thread onFrame handler, never in the UI callback.
        sample()
        if not focus then
            pending=nil
            ui.showMessage('Sieh draußen einen nahen leuchtenden Kristall oder Baum an.',{showInDialogue=false})
            return
        end
        local sun,storm=nil,false
        local ok,value=pcall(core.weather.getCurrentSunPercentage,self.cell)
        if ok and R.finite(value) then sun=math.max(0,math.min(1,value)) end
        local weatherOk,weather=pcall(core.weather.getCurrent,self.cell)
        if weatherOk and weather then storm=weather.isStorm==true end
        sequence=sequence+1;pending.requestId='resonance-'..tostring(sequence);pending.sent=true
        core.sendGlobalEvent('HALVETH_ResonanceRequest',{player=self.object,target=focus.object,
            point=focus.point,action=pending.action,sun=sun,storm=storm,requestId=pending.requestId})
        return
    end
    -- No idle scene raycasts: the player asks before we inspect rendered geometry.
end
return {interfaceName='HALVETHResonance',
    interface={version=1,getState=getState,request=request,statusText=statusText,
        getContext=function()
            if not lastResult or not lastResult.success then return nil end
            return {source='authored_plant_resonance',message=lastResult.message,
                place=R.copy(lastResult.entry),rememberedPlaces=entryCount}
        end},
    engineHandlers={onFrame=frame,onLoad=function()
        focus,lastResult,pending=nil,nil,nil;entryCount,sequence=0,0;blocked=false;inspected=false
    end},
    eventHandlers={HALVETH_ResonanceState=function(data)
        if type(data)=='table' and R.integer(data.entryCount,0,R.maxEntries) then
            entryCount=data.entryCount;blocked=data.blocked==true
        end
    end,HALVETH_ResonanceResult=function(data)
        if type(data)~='table' or type(data.success)~='boolean' or type(data.message)~='string' then return end
        -- Replies from the matching request populate the one existing console and the HUD.
        if pending and data.requestId~=pending.requestId then return end
        pending=nil;lastResult=data;entryCount=data.entryCount or entryCount;blocked=data.blocked==true
        if I.HALVETH and I.HALVETH.write then I.HALVETH.write(data.message) end
        ui.showMessage(data.message,{showInDialogue=false})
    end}}
