-- SPDX-License-Identifier: MIT
-- Deliberate ordinary Lua model. No engine, input, save serialization or AI claim.
local root=assert(arg[1], 'Pass the Wildlife unit directory')..'/'
local C=assert(loadfile(root..'mod/scripts/veyra_wildlife/config.lua'))()
local checks=0
local function check(v,name)assert(v,name);checks=checks+1 end
local sent={};local clock=10
local actor={id='owned-reference',recordId='owned-record',contentFile=nil}
function actor:isValid()return true end
function actor:sendEvent(name,data)sent[#sent+1]={name=name,data=data}end
local player={id='real-player',cell={},position={}}
function player:isValid()return true end
function player:sendEvent(name,data)sent[#sent+1]={name=name,data=data}end
local types={Creature={objectIsInstance=function(o)return o==actor end},Player={objectIsInstance=function(o)return o==player end},Actor={isDead=function()return false end}}
local I={};local world={activeActors={actor},getSimulationTime=function()return clock end}
world.createObject=function()error('No new actor permitted by this re-enable oracle')end
package.loaded['openmw.world']=world;package.loaded['openmw.types']=types
package.loaded['openmw.util']={};package.loaded['openmw.interfaces']=I
package.loaded['scripts.veyra_wildlife.config']=C
local global=assert(loadfile(root..'mod/scripts/veyra_wildlife/global.lua'))()
I.VeyraWildlife=global.interface;global.engineHandlers.onPlayerAdded(player)
check(global.interface.getState().enabled==false,'default disabled')
global.engineHandlers.onLoad({schema=1,created=true,actor=actor,actorId=actor.id,recordId=actor.recordId})
check(global.interface.getState().actor==actor and not global.interface.getState().enabled,'compatible existing reference load OFF')
global.eventHandlers.VEYRA_WildUserSet({player=player,enabled=true,requestId=1})
check(global.interface.getState().enabled,'actual player bridge calls published setter')
global.engineHandlers.onUpdate()
check(sent[#sent].name=='VEYRA_WildPing','first enable requests actor handshake')
global.eventHandlers.VEYRA_WildReport({actor=actor,phase='READY'})
global.engineHandlers.onUpdate()
check(global.interface.getState().goalIssued,'first goal issued')
global.eventHandlers.VEYRA_WildUserSet({player=player,enabled=false,requestId=2})
check(not global.interface.getState().enabled and global.interface.getState().actor==actor,'OFF preserves reference')
global.eventHandlers.VEYRA_WildUserSet({player=player,enabled=true,requestId=3})
check(not global.interface.getState().ready and not global.interface.getState().goalIssued,'reenable resets same actor handshake and goal')
global.engineHandlers.onUpdate()
check(sent[#sent].name=='VEYRA_WildPing','reenable requests ping')
global.eventHandlers.VEYRA_WildReport({actor=actor,phase='READY'});global.engineHandlers.onUpdate()
check(global.interface.getState().goalIssued and global.interface.getState().actor==actor,'fresh goal same actor without allocation')
global.eventHandlers.VEYRA_WildUserSet({player=player,enabled='true',requestId=4})
check(global.interface.getState().enabled,'explicit invalid input rejected')
local fake={id='other'};function fake:isValid()return true end
global.eventHandlers.VEYRA_WildUserSet({player=fake,enabled=false,requestId=5})
check(global.interface.getState().enabled,'other object is not owner player')
global.engineHandlers.onLoad(global.engineHandlers.onSave())
check(not global.interface.getState().enabled and global.interface.getState().actor==actor,'reload state default OFF without replacement')
global.engineHandlers.onLoad({schema=1,created=true,phase='CREATE_HOLD',actorId=actor.id,recordId=actor.recordId})
check(global.interface.setEnabled(true)==false,'allocation failure remains held')
local events,messages={},{};local mode,paused=nil,false
package.loaded['openmw.core']={sendGlobalEvent=function(n,d)events[#events+1]={name=n,data=d}end,getRealTime=function()return clock end,isWorldPaused=function()return paused end}
package.loaded['openmw.self']={object=player,cell=player.cell}
package.loaded['openmw.input']={KEY={U=24}}
package.loaded['openmw.ui']={showMessage=function(s)messages[#messages+1]=s end}
I.UI={getMode=function()return mode end}
local localmod=assert(loadfile(root..'mod/scripts/veyra_wildlife/player.lua'))()
check(localmod.interface.setEnabled(true)==false,'connecting state is not silently enabled')
localmod.eventHandlers.VEYRA_WildUserStatus({version=C.version,enabled=false,phase='DISABLED',kind='STATUS'})
check(messages[#messages]:find('%[U%]') and localmod.interface.getState().enabled==false,'normal hint explicit U and OFF')
mode='Interface';localmod.engineHandlers.onKeyPress({code=24});check(#events==0,'U ignored in modal UI')
mode=nil;paused=true;localmod.engineHandlers.onKeyPress({code=24});check(#events==0,'U ignored while world paused')
paused=false;localmod.engineHandlers.onKeyPress({code=24})
check(#events==1 and events[1].data.player==player and events[1].data.enabled==true,'U routes through real player event bridge')
localmod.engineHandlers.onKeyPress({code=24});check(#events==1,'pending command prevents repeated toggle')
localmod.eventHandlers.VEYRA_WildUserStatus({version=C.version,enabled=true,phase='WAIT_FRONTIER',kind='STATUS'})
check(localmod.interface.getState().pending,'background status is not command acknowledgement')
localmod.eventHandlers.VEYRA_WildUserStatus({version=C.version,enabled=true,phase='WAIT_FRONTIER',kind='USER_RESULT',requestId=1,accepted=true})
check(not localmod.interface.getState().pending and localmod.interface.getState().enabled,'matching result acknowledges normal operation')
localmod.interface.toggle();check(events[#events].data.enabled==false,'next toggle requests explicit OFF')
localmod.engineHandlers.onLoad();check(localmod.interface.getState().phase=='CONNECTING' and not localmod.interface.getState().pending,'player load cache reconnected')
print('WILDLIFE011_LOCAL_MODEL_PASS '..checks..' assertions; physical key and native movement NOT OBSERVED')
