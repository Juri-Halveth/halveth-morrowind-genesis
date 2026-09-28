-- Attached only to new study actors inside the isolated visual-field profile.
-- Native AI performs locomotion and collision; no frame-by-frame teleportation.
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local core=require('openmw.core')
local destination,home,walking
local nextCheck=0
local function travel(target)
 I.AI.startPackage({type='Travel',destPosition=target,cancelOther=true})
end
return {eventHandlers={HALVETH_FieldWalk=function(data)
 if not self.cell or self.cell.name~='HALVETH Visual Field' then return end
 destination,home,walking=data.destination,data.returnPosition,data.enabled
 types.Actor.stats.ai.fight(self).base=0
 types.Actor.stats.ai.alarm(self).base=0
 if walking then travel(destination) end
end},engineHandlers={onUpdate=function()
 if not walking or not self.cell or self.cell.name~='HALVETH Visual Field' then return end
 local now=core.getRealTime()
 if now<nextCheck then return end
 nextCheck=now+1
 if (self.position-destination):length()<100 then
  destination,home=home,destination;travel(destination)
 end
end}}
