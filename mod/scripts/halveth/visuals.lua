-- Native visual choices inside the running OpenMW game via HALVETHVisuals.
-- This script only owns halveth_atmosphere; other shaders and game data stay as configured.
local postprocessing = require('openmw.postprocessing')
local ui = require('openmw.ui')

local SHADER = 'halveth_atmosphere'
local ORDER = {'scarlet', 'nocturne', 'original'}
local PRESETS = {
    original = {title='Original'},
    scarlet = {title='Scharlachlicht', strength=0.48, temperature=0.78,
        saturation=1.04, vignette=0.10},
    nocturne = {title='Nachtglas', strength=0.45, temperature=-0.68,
        saturation=1.02, vignette=0.12},
}

local mode = 'scarlet'
local shader, failure, retainedInvalidSave, invalidSavePresent

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
    local preset = PRESETS[mode]
    local ok, err = pcall(function()
        shader:setFloat('uStrength', preset.strength)
        shader:setFloat('uTemperature', preset.temperature)
        shader:setFloat('uSaturation', preset.saturation)
        shader:setFloat('uVignette', preset.vignette)
        shader:enable()
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
        shader=SHADER, enabled=enabled, error=failure}
end

local function setMode(nextMode, notify)
    if not PRESETS[nextMode] then return false end
    mode = nextMode
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
        onSave=function()
            if invalidSavePresent then return retainedInvalidSave end
            return {version=1, mode=mode}
        end,
    },
}
