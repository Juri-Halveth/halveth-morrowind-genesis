-- The real player mailbox callback reads from a synthetic OpenMW session.
package.path='mod/?.lua;'..package.path
local clock, packet, event, transcript = 0, nil, nil, ''
for _,name in ipairs({'ui','async','interfaces','input','camera','util'}) do
    package.loaded['openmw.'..name]={}
end
local actor={cell=true,position={x=0,y=0,z=0}}
function actor:sendEvent(name,value)
    if name=='HALVETH_ReplyReceived' then event=value end
end
package.loaded['openmw.self']=actor
package.loaded['openmw.core']={getRealTime=function() return clock end,getGameTime=function() return 0 end}
package.loaded['openmw.nearby']={actors={}}
local function stat() return {current=1,base=1,modifier=0} end
package.loaded['openmw.types']={Player={quests=function()return {} end}, Actor={
    stats={dynamic={health=stat,magicka=stat,fatigue=stat}},
    inventory=function()return {countOf=function()return 0 end} end,
}}
package.loaded['scripts.halveth.inspect']={actor=function()return {} end}
package.loaded['openmw.vfs']={open=function(path)
    assert(path=='bridge/inbox.json')
    return {read=function()return 'fixture' end, close=function()end}
end}
package.loaded['openmw.markup']={decodeYaml=function()return packet end}
local common=require('scripts.halveth.common')
common.emit=function()end
local originalTail=common.tail
common.tail=function(text,limit) transcript=originalTail(text,limit); return transcript end

local player=require('scripts.halveth.player')
player.engineHandlers.onInit()
local session=player.interface.getSessionId()
player.eventHandlers.HALVETH_Ready({sessionId=session,worldId='test-world'})
local function deliver(mode, sequence, targetSession)
    packet={sessionId=targetSession or session,sequence=sequence,speaker='JARVIS',responseMode=mode,reply='Testtext'}
    event=nil
    clock=clock+1
    player.engineHandlers.onFrame()
    return event
end
local cases={{'MODEL_LIVE','Lokales Modell'},{'OFFLINE','Offline-Hinweis'},
    {'MODEL_UNAVAILABLE','Modell nicht erreichbar'},{'ERROR','Verarbeitungsfehler'}}
for index,case in ipairs(cases) do
    local receipt=assert(deliver(case[1],index))
    assert(receipt.responseMode==case[1] and receipt.reply=='Testtext')
    assert(transcript:find('JARVIS · '..case[2]..': Testtext',1,true))
end
local legacy=assert(deliver(nil,5))
assert(legacy.responseMode==nil and transcript:sub(-#'JARVIS: Testtext')=='JARVIS: Testtext')
assert(not deliver('ERROR',5))
assert(not deliver('ERROR',6,'previous-session'))
print('Game mailbox passed four reply modes, a legacy packet and two ignored deliveries.')
