-- Small in-world atmospheric moments derived only from the loaded exterior.
-- No original record, actor, quest or save state is changed by this script.
local core = require('openmw.core')
local self = require('openmw.self')
local ui = require('openmw.ui')

local SAMPLE_SECONDS = 5
local MIN_CUE_SECONDS = 75
local enabled, nextSampleAt, firstSeenAt, lastCueAt = true, 0, nil, -100000
local current, lastAnnouncedKey, cueCount = nil, nil, 0

local TEXT = {
    storm = {
        'Der Sturm zeichnet neue Linien in die Luft.',
        'Wind und Wetter geben diesem Weg heute eine andere Gestalt.',
        'Der Sturm zieht sichtbar durch die Landschaft.',
    },
    dim = {
        'Im schwachen Licht treten die Konturen der Welt anders hervor.',
        'Das gedämpfte Licht lässt selbst vertraute Wege neu erscheinen.',
        'Zwischen Schatten und Gelände liegt ein stiller Augenblick.',
    },
    bright = {
        'Helles Licht öffnet den Blick über das Land.',
        'Die Landschaft zeigt im klaren Licht andere Farben.',
        'Licht wandert über die sichtbaren Wege und Steine.',
    },
    soft = {
        'Das Licht verändert die Farben dieser Landschaft.',
        'Ein neuer Blick auf den Weg: Licht liegt zwischen den Formen.',
        'Die Welt wirkt in diesem Licht für einen Moment anders.',
    },
}

local function cellKey(cell)
    return tostring(cell.worldSpaceId or cell.id or '') .. ':' ..
        tostring(cell.gridX or '') .. ':' .. tostring(cell.gridY or '')
end

local function textIndex(key, count)
    local sum = 0
    for i = 1, #key do sum = (sum * 33 + key:byte(i)) % 2147483647 end
    return sum % count + 1
end

local function sample()
    local cell = self.cell
    if not cell or not cell.isExterior then return nil end
    local okSun, sun = pcall(core.weather.getCurrentSunPercentage, cell)
    local okWeather, weather = pcall(core.weather.getCurrent, cell)
    if not okSun or type(sun) ~= 'number' or sun ~= sun then return nil end
    sun = math.max(0, math.min(1, sun))
    local storm = okWeather and weather ~= nil and weather.isStorm == true or false
    local light = sun < 0.20 and 'dim' or sun > 0.70 and 'bright' or 'soft'
    return {source='loaded_exterior_weather', cell=cellKey(cell),
        light=light, sun=sun, storm=storm, mood=storm and 'storm' or light}
end

local function getState()
    local observed = current and {source=current.source,cell=current.cell,
        light=current.light,sun=current.sun,storm=current.storm,mood=current.mood} or nil
    return {version=1,enabled=enabled,observed=observed,cueCount=cueCount,
        lastAnnouncedKey=lastAnnouncedKey}
end

local function setEnabled(value)
    if type(value) ~= 'boolean' then return false end
    enabled = value
    -- A fresh opt-in may announce the next observed state; opt-out is silent.
    if value then lastAnnouncedKey = nil;firstSeenAt = core.getRealTime() end
    return true
end

local function tick()
    local now = core.getRealTime()
    if now < nextSampleAt then return end
    nextSampleAt = now + SAMPLE_SECONDS
    current = sample()
    if not current or not enabled then return end
    if not firstSeenAt then firstSeenAt = now;return end
    if now - firstSeenAt < 3 or now - lastCueAt < MIN_CUE_SECONDS then return end
    local key = current.cell .. ':' .. current.mood
    if key == lastAnnouncedKey then return end
    local candidates = TEXT[current.mood]
    local cue = candidates[textIndex(key, #candidates)]
    local ok = pcall(ui.showMessage, cue, {showInDialogue=false})
    if ok then
        lastCueAt, lastAnnouncedKey = now, key
        cueCount = cueCount + 1
    end
end

return {interfaceName='HALVETHWorldMoments',
    interface={version=1,getState=getState,setEnabled=setEnabled},
    engineHandlers={onFrame=tick,onLoad=function()
        enabled, nextSampleAt, firstSeenAt, lastCueAt = true, 0, nil, -100000
        current, lastAnnouncedKey, cueCount = nil, nil, 0
    end},
}
