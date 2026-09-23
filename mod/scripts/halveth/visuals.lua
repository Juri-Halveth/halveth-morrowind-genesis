-- Native visual choices inside the running OpenMW game via HALVETHVisuals.
-- This script only owns halveth_atmosphere; other shaders and game data stay as configured.
local postprocessing = require('openmw.postprocessing')
local ui = require('openmw.ui')
local core = require('openmw.core')
local self = require('openmw.self')

local SHADER = 'halveth_atmosphere'
local ORDER = {'scarlet', 'dawn', 'living', 'nocturne', 'original'}
local PRESETS = {
    original = {title='Original'},
    scarlet = {title='Scharlachlicht', strength=0.48, temperature=0.78,
        saturation=1.04, vignette=0.10, contrast=1.00},
    dawn = {title='Morgenrot', strength=0.72, temperature=0.92,
        saturation=1.14, vignette=0.08, contrast=1.12},
    living = {title='Lebendige Welt'},
    nocturne = {title='Nachtglas', strength=0.45, temperature=-0.68,
        saturation=1.02, vignette=0.12, contrast=1.05},
}

local mode = 'scarlet'
local shader, failure, retainedInvalidSave, invalidSavePresent
local environment = {source='unavailable', sun=nil, storm=false}
local refreshSeconds = 0

local function clamp(value)
    return math.max(0, math.min(1, value))
end

local function sampleEnvironment()
    local cell = self.cell
    if not cell then
        environment = {source='unavailable', sun=nil, storm=false}
        return
    end
    local okSun, sun = pcall(core.weather.getCurrentSunPercentage, cell)
    local okWeather, weather = pcall(core.weather.getCurrent, cell)
    if okSun and type(sun) == 'number' then
        environment = {source='weather', sun=clamp(sun),
            storm=okWeather and weather ~= nil and weather.isStorm == true or false}
    else
        -- Interior cells do not have weather. Keep a predictable, subtle grade.
        environment = {source='interior', sun=nil, storm=false}
    end
end

local function livingPreset()
    sampleEnvironment()
    if environment.sun == nil then
        return {strength=0.30, temperature=0.16, saturation=1.04,
            vignette=0.06, contrast=1.03}
    end
    local sun = environment.sun
    local storm = environment.storm
    return {strength=0.40 + 0.13 * sun,
        temperature=-0.42 + 1.14 * sun - (storm and 0.12 or 0),
        saturation=1.00 + 0.08 * sun - (storm and 0.04 or 0),
        vignette=0.09 - 0.03 * sun,
        contrast=1.04 + 0.04 * sun}
end

local function ensureShader()
    if shader then return true end
    local ok, result = pcall(postprocessing.load, SHADER)
    if not ok or not result then
        failure = tostring(result or 'OpenMW konnte den Shader nicht laden')
        print('HALVETH_VISUALS_LOAD_ERROR '..failure)
        return false
    end
    shader, failure = result, nil
    return true
end

local function apply()
    if mode == 'original' then
        if shader then
            local ok, err = pcall(function() shader:disable() end)
            if not ok then failure = tostring(err);return false end
        end
        return true
    end
    if not ensureShader() then return false end
    local preset = mode == 'living' and livingPreset() or PRESETS[mode]
    local ok, err = pcall(function()
        shader:setFloat('uStrength', preset.strength)
        shader:setFloat('uTemperature', preset.temperature)
        shader:setFloat('uSaturation', preset.saturation)
        shader:setFloat('uVignette', preset.vignette)
        shader:setFloat('uContrast', preset.contrast)
        if not shader:isEnabled() then shader:enable() end
    end)
    if not ok then
        failure = tostring(err)
        print('HALVETH_VISUALS_APPLY_ERROR '..failure)
        return false
    end
    failure = nil
    return true
end

local function state()
    local enabled = shader and shader:isEnabled() or false
    return {version=1, mode=mode, title=PRESETS[mode].title,
        shader=SHADER, enabled=enabled, error=failure,
        environment=mode == 'living' and environment or nil}
end

local function setMode(nextMode, notify)
    if not PRESETS[nextMode] then return false end
    mode = nextMode
    refreshSeconds = 0
    retainedInvalidSave = nil
    invalidSavePresent = false
    local ok = apply()
    if notify then
        ui.showMessage(ok and ('HALVETH Licht: '..PRESETS[mode].title)
            or 'HALVETH Licht ist hier nicht verfuegbar.', {showInDialogue=false})
    end
    return ok
end

local function cycle()
    for index, name in ipairs(ORDER) do
        if name == mode then return setMode(ORDER[index % #ORDER + 1], true) end
    end
    return setMode('scarlet', true)
end

local function onLoad(data)
    mode, retainedInvalidSave, invalidSavePresent, failure = 'scarlet', nil, false, nil
    refreshSeconds = 0
    if data ~= nil then
        if type(data) ~= 'table' or data.version ~= 1 or not PRESETS[data.mode] then
            retainedInvalidSave = data
            invalidSavePresent = true
            mode = 'original'
        else
            mode = data.mode
        end
    end
    apply()
end

return {
    interfaceName='HALVETHVisuals',
    interface={version=1, modes=ORDER, getState=state, setMode=setMode, cycle=cycle},
    engineHandlers={
        onInit=function() apply() end,
        onLoad=onLoad,
        onFrame=function(dt)
            if mode ~= 'living' or not shader then return end
            refreshSeconds = refreshSeconds + dt
            if refreshSeconds < 2 then return end
            refreshSeconds = 0
            apply()
        end,
        onSave=function()
            if invalidSavePresent then return retainedInvalidSave end
            return {version=1, mode=mode}
        end,
    },
}
