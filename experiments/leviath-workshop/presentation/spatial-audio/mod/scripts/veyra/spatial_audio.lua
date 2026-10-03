-- SPDX-License-Identifier: MIT
-- Veyra Spatial Audio 0.1.0. Read-only courier coupling, OpenMW 0.51/API129.
local core = require('openmw.core')
local world = require('openmw.world')
local I = require('openmw.interfaces')

local VERSION = '0.1.0'
local FILE = 'Sound/veyra/courier_bell_mono.wav'
local PERIOD = 0.25
local elapsed, lastPlayedCourierId = PERIOD, nil
local state = {version=VERSION, status='WAITING', requestCount=0, playing=false}
local lastError, loadFault

local function copy(value)
    if type(value) ~= 'table' then return value end
    local result = {}
    for key, child in pairs(value) do result[key] = copy(child) end
    return result
end

local function findActor(id)
    for _, actor in ipairs(world.activeActors) do
        if actor:isValid() and actor.enabled and actor.id == id then return actor end
    end
end

local function update()
    if loadFault then state.status='LOAD_HOLD';state.error=loadFault;return end
    if core.isWorldPaused() then state.status='PAUSED';return end
    state.lastReadAtGameTime = core.getGameTime()
    state.playing = false
    local courier = I.VeyraCourier
    if not courier or type(courier.status) ~= 'function' then
        state.status='NO_COURIER_INTERFACE';return
    end
    local status = courier.status()
    if type(status) ~= 'table' then state.status='NO_COURIER_STATUS';return end
    state.courierPhase = status.phase
    state.courierId = status.courierId
    if status.phase ~= 'ARRIVED' or status.courierValid ~= true
        or type(status.courierId) ~= 'string' or status.courierId == '' then
        state.status='WAITING_FOR_ARRIVAL';return
    end
    local actor = findActor(status.courierId)
    if not actor then state.status='WAITING_FOR_ACTIVE_ACTOR';return end
    state.soundEnabled = core.sound.isEnabled()
    if not state.soundEnabled then state.status='SOUND_DISABLED';return end
    state.playing = core.sound.isSoundFilePlaying(FILE, actor)
    if lastPlayedCourierId == status.courierId then
        state.status=state.playing and 'PLAYING' or 'ALREADY_REQUESTED';return
    end
    -- Global scripts may attach sound to another actor; local scripts cannot.
    core.sound.playSoundFile3d(FILE, actor, {volume=0.30, pitch=1.0, loop=false})
    lastPlayedCourierId = status.courierId
    state.lastPlayedCourierId = lastPlayedCourierId
    state.requestCount = state.requestCount + 1
    state.requestedAtGameTime = core.getGameTime()
    state.status = 'PLAY_REQUESTED'
    print('VEYRA_AUDIO|kind=PLAY_REQUESTED|version='..VERSION..'|courierId='..
        status.courierId..'|file='..FILE..'|mono=true|loop=false')
end

local function onUpdate(dt)
    elapsed = elapsed + dt
    if elapsed < PERIOD then return end
    elapsed = 0
    local ok, err = pcall(update)
    if not ok then
        state.status='ERROR';state.error=tostring(err)
        if state.error ~= lastError then print('VEYRA_AUDIO|kind=ERROR|'..state.error) end
        lastError=state.error
    else if not loadFault then state.error=nil end;lastError=nil end
end

local function onLoad(saved)
    lastPlayedCourierId, loadFault = nil, nil
    if type(saved) == 'table' and saved.version == 1 and saved.hold ~= nil then
        loadFault='INVALID_SAVED_STATE'
    elseif type(saved) == 'table' and saved.version == 1
        and (saved.lastPlayedCourierId == nil or (type(saved.lastPlayedCourierId) == 'string'
            and saved.lastPlayedCourierId ~= '')) then
        lastPlayedCourierId = saved.lastPlayedCourierId
    elseif saved ~= nil then
        loadFault='INVALID_SAVED_STATE'
    end
    state = {version=VERSION, status='LOADED', requestCount=0, playing=false,
        lastPlayedCourierId=lastPlayedCourierId}
    elapsed = PERIOD
end

return {
    interfaceName='VeyraSpatialAudio',
    interface={version=VERSION, getState=function() return copy(state) end},
    engineHandlers={onUpdate=onUpdate, onLoad=onLoad,
        onSave=function()
            if loadFault then return {version=1,hold=loadFault} end
            return {version=1,lastPlayedCourierId=lastPlayedCourierId}
        end},
}
