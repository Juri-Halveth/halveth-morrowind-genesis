local core = require('openmw.core')
local world = require('openmw.world')
local types = require('openmw.types')
local C = require('scripts.halveth.common')

local sessions, pending = {}, {}
local originPlayer, originPending, originFrames = nil, false, 0
local function newWorldId()
    return string.format('world-%d-%d-%d',os.time(),math.random(100000,999999),math.random(100000,999999))
end
local worldId=newWorldId()
local function snapshot(player)
    local health = types.Actor.stats.dynamic.health(player)
    return {gold=types.Actor.inventory(player):countOf('gold_001'), health=health.current,
        magicka=types.Actor.stats.dynamic.magicka(player).current,
        fatigue=types.Actor.stats.dynamic.fatigue(player).current,
        cell=player.cell and player.cell.name or '', position=C.position(player.position)}
end
local function anchor(player)
    return {cell=player.cell, position=player.position, rotation=player.rotation}
end
local function result(player, data)
    player:sendEvent('HALVETH_Result', data)
end
local function register(data)
    local player = data.player
    if not player or not player:isValid() or not types.Player.objectIsInstance(player) or not C.validId(data.sessionId) then return end
    -- Register can be retried; it must not clear the idempotence ledger.
    if sessions[player.id] and sessions[player.id].id == data.sessionId then return end
    sessions[player.id] = {id=data.sessionId, seen={}, start=anchor(player), back=nil}
    player:sendEvent('HALVETH_Ready', {sessionId=data.sessionId,worldId=worldId})
end
local function apply(data)
    local player, action = data.player, data.action
    if not player or not player:isValid() or type(action)~='table' or not C.validId(action.id) then return end
    local s=sessions[player.id]
    if not s or s.id~=data.sessionId then return end
    if s.seen[action.id] then
        if type(s.seen[action.id])=='table' then result(player,s.seen[action.id]) end
        return
    end
    s.seen[action.id]=true -- reservation before applying any effect
    local receipt={type='result', sessionId=s.id, actionId=action.id, kind=action.kind,
        success=false, before=snapshot(player)}
    local ok, err = pcall(function()
        local p=action.params or {}
        assert(type(p)=='table','Action parameters must be an object')
        if action.kind=='give_gold' then
            local amount=p.amount
            assert(C.finite(amount) and amount%1==0 and amount>=1 and amount<=1000000,'Gold amount must be an integer from 1 to 1000000')
            world.createObject('gold_001',amount):moveInto(types.Actor.inventory(player))
            receipt.message=tostring(amount)..' Gold erschaffen.'
            receipt.expectedGold=receipt.before.gold+amount
        elseif action.kind=='heal_player' then
            -- Stat writes belong to the actor's local script; the result is observed later.
            player:sendEvent('HALVETH_Heal', {sessionId=s.id, actionId=action.id})
            receipt.message='Gesundheit, Magicka und Ausdauer wiederhergestellt.'
            receipt.expectedStats={}
            for _,name in ipairs({'health','magicka','fatigue'}) do
                local stat=types.Actor.stats.dynamic[name](player)
                receipt.expectedStats[name]=math.max(0,stat.base+stat.modifier)
            end
        elseif action.kind=='teleport_anchor' then
            assert(p.anchor=='session_start','Unknown anchor; supported: session_start')
            s.back=anchor(player)
            player:teleport(s.start.cell,s.start.position,{rotation=s.start.rotation})
            receipt.expectedPosition=C.position(s.start.position)
            receipt.expectedCell=s.start.cell.name
            receipt.message='Zum Startpunkt dieser Spielsitzung gereist.'
        elseif action.kind=='return_anchor' then
            assert(s.back,'No return point has been recorded yet')
            local dest=s.back
            s.back=anchor(player)
            player:teleport(dest.cell,dest.position,{rotation=dest.rotation})
            receipt.expectedPosition=C.position(dest.position)
            receipt.expectedCell=dest.cell.name
            receipt.message='Zum vorherigen Reiseort zurueckgekehrt.'
        else error('Unsupported action: '..tostring(action.kind)) end
    end)
    if not ok then
        receipt.message=tostring(err)
        receipt.after=snapshot(player)
        s.seen[action.id]=receipt
        result(player,receipt)
        return
    end
    pending[#pending+1]={player=player,session=s,receipt=receipt,frames=0}
end
local function update()
    if originPending and originPlayer and originPlayer:isValid() then
        originFrames=originFrames+1
        if originFrames>=5 then
            originPlayer:sendEvent('HALVETH_OriginNewGame',{})
            originPending=false
        end
    end
    for i=#pending,1,-1 do
        local p=pending[i]
        p.frames=p.frames+1
        if p.frames>=5 then
            if p.player:isValid() and sessions[p.player.id]==p.session then
                p.receipt.after=snapshot(p.player)
                p.receipt.success=not p.receipt.expectedGold or p.receipt.after.gold>=p.receipt.expectedGold
                if p.receipt.expectedStats then
                    for name,expected in pairs(p.receipt.expectedStats) do
                        if p.receipt.after[name]<expected-.01 then p.receipt.success=false end
                    end
                end
                if p.receipt.expectedPosition then
                    local a,b=p.receipt.after.position,p.receipt.expectedPosition
                    local distance=math.sqrt((a.x-b.x)^2+(a.y-b.y)^2+(a.z-b.z)^2)
                    if distance>128 or p.receipt.after.cell~=p.receipt.expectedCell then p.receipt.success=false end
                end
                p.receipt.expectedGold=nil
                p.receipt.expectedStats=nil;p.receipt.expectedPosition=nil;p.receipt.expectedCell=nil
                if not p.receipt.success then p.receipt.message='Der erwartete Nachzustand wurde nicht vollstaendig beobachtet; bitte aktuellen Weltzustand pruefen.' end
                p.session.seen[p.receipt.actionId]=p.receipt
                result(p.player,p.receipt)
            end
            table.remove(pending,i)
        end
    end
end
return {
    engineHandlers={onUpdate=update,
        onSave=function() return {version=2,worldId=worldId,originPending=originPending} end,
        onLoad=function(data)
            sessions={};pending={}
            originPlayer=nil;originFrames=0
            originPending=type(data)=='table' and data.version==2 and data.originPending==true or false
            worldId=(data and C.validId(data.worldId)) and data.worldId or newWorldId()
        end,
        onNewGame=function()
            sessions={};pending={};worldId=newWorldId()
            originPending=true;originFrames=0
        end,
        onPlayerAdded=function(player) originPlayer=player end},
    eventHandlers={HALVETH_Register=register, HALVETH_Action=apply},
}
