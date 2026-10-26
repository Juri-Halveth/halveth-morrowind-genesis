-- Veyra Presentation 0.1.4, MIT. OpenMW 0.51.0 player script.
-- Owns only a supplementary, noninteractive HUD layer. Reads engine state.
local core = require('openmw.core')
local self = require('openmw.self')
local types = require('openmw.types')
local ui = require('openmw.ui')
local util = require('openmw.util')
local I = require('openmw.interfaces')

local VERSION = '0.1.4'
local LAYER = 'VeyraPresentation'
local WIDTH, HEIGHT = 326, 180
local PERIOD = 0.10
local enabled, elapsed, element, layout = true, PERIOD, nil, nil
local labels, fills, trackWidths = {}, {}, {}
local location, clock, burden
local panel, accent, courierNotice, courierHint
local screenX, screenY, lastState = nil, nil, nil
local readyPrinted, failurePrinted = false, false
local lastMode, lastHudVisibility
local texture
local ink = util.color.rgb(0.96, 0.95, 0.91)
local muted = util.color.rgb(0.74, 0.78, 0.80)
local gold = util.color.rgb(0.90, 0.77, 0.48)
local colors = {
    health = util.color.rgb(0.89, 0.38, 0.39),
    magicka = util.color.rgb(0.39, 0.65, 0.94),
    fatigue = util.color.rgb(0.55, 0.80, 0.58),
}

local function finite(value)
    return type(value) == 'number' and value == value
        and value ~= math.huge and value ~= -math.huge
end

local function copy(value)
    if type(value) ~= 'table' then return value end
    local result = {}
    for key, child in pairs(value) do result[key] = copy(child) end
    return result
end

local function courierArrived()
    local courier = I.VeyraCourierPlayer
    if not courier or type(courier.getState) ~= 'function' then return false end
    local ok, value = pcall(courier.getState)
    return ok and type(value) == 'table' and value.phase == 'ARRIVED' or false
end

local function readStat(key)
    local stat = types.Actor.stats.dynamic[key](self)
    local maximum = stat.base + stat.modifier
    if not finite(stat.current) or not finite(maximum) then
        error('non-finite engine stat: '..key)
    end
    -- Fatigue can legitimately be negative; the number preserves that state.
    local ratio = maximum > 0 and math.max(0, math.min(1, stat.current / maximum)) or 0
    return {current=stat.current, maximum=maximum, ratio=ratio}
end

local function text(name, value, x, y, size, color, width)
    return {name=name, type=ui.TYPE.Text, props={
        position=util.vector2(x, y), size=util.vector2(width or WIDTH-32, size+6),
        autoSize=false, text=value, textSize=size, textColor=color or ink,
        textShadow=true, textShadowColor=util.color.rgb(0, 0, 0),
    }}
end

local function image(name, x, y, width, height, color, alpha)
    return {name=name, type=ui.TYPE.Image, props={
        position=util.vector2(x, y), size=util.vector2(width, height),
        resource=texture, color=color, alpha=alpha or 1,
    }}
end

local function destroy()
    if element then element:destroy() end
    element, layout = nil, nil
    labels, fills, trackWidths = {}, {}, {}
end

local function build()
    destroy()
    local screen = ui.screenSize()
    screenX, screenY = screen.x, screen.y
    -- Width is constant for readability; keep the panel inside small windows.
    local margin = math.max(8, math.min(28, math.floor(screen.x * 0.016)))
    if not ui.layers.indexOf(LAYER) then
        ui.layers.insertAfter('HUD', LAYER, {interactive=false})
    end
    texture = texture or ui.texture{path='Textures/veyra/white.png'}
    location = text('location', '', 16, 34, 16, ink)
    clock = text('clock', '', WIDTH-88, 12, 14, gold, 72)
    burden = text('burden', '', 16, 151, 13, muted)
    panel = image('panel', 0, 0, WIDTH, HEIGHT, util.color.rgb(0.035, 0.048, 0.064), 0.77)
    accent = image('accent', 0, 0, 3, HEIGHT, gold, 0.85)
    courierNotice = text('courier_notice', 'ELYRA IST DA / WELTENPOST', 16, 175, 13, gold)
    courierHint = text('courier_hint', '[K] Sendung annehmen', 16, 195, 13, ink)
    courierNotice.props.visible, courierHint.props.visible = false, false
    local content = {
        panel, accent,
        text('title', 'VEYRA  /  MORROWIND', 16, 12, 14, gold, WIDTH-110),
        location, clock, burden, courierNotice, courierHint,
        image('rule', 16, 60, WIDTH-32, 1, gold, 0.28),
    }
    for index, pair in ipairs({{'health','LEBEN'}, {'magicka','MAGIE'}, {'fatigue','AUSDAUER'}}) do
        local key, title = pair[1], pair[2]
        local y = 72 + (index-1)*25
        labels[key] = text(key..'_value', title, 16, y-3, 13, ink, 164)
        local trackX, trackWidth = 170, WIDTH-186
        fills[key] = image(key..'_fill', trackX, y+2, 0, 8, colors[key])
        trackWidths[key] = trackWidth
        content[#content+1] = labels[key]
        content[#content+1] = image(key..'_track', trackX, y+2, trackWidth, 8,
            util.color.rgb(0.29, 0.32, 0.35), 0.65)
        content[#content+1] = fills[key]
    end
    layout = {name='VeyraHUD', type=ui.TYPE.Widget, layer=LAYER,
        props={position=util.vector2(margin, margin), size=util.vector2(WIDTH, HEIGHT), visible=false},
        content=ui.content(content)}
    element = ui.create(layout)
end

local function locationLabel(cell)
    -- Cell.region is an identity, RegionRecord.name is the engine display label.
    local regionId = cell and cell.region
    if type(regionId) ~= 'string' or regionId == '' then regionId = nil end
    local display = cell and cell.displayName
    if type(display) == 'string' and display ~= '' then
        return display, 'CELL_DISPLAY_NAME', regionId
    end
    local name = cell and cell.name
    if type(name) == 'string' and name ~= '' then
        return name, 'CELL_NAME', regionId
    end
    if regionId then
        local ok, regionName = pcall(function()
            local record = core.regions.records[regionId]
            return record and record.name
        end)
        if ok and type(regionName) == 'string' and regionName ~= '' then
            return regionName, 'REGION_RECORD_NAME', regionId
        end
        return regionId, 'REGION_ID', regionId
    end
    return 'Vvardenfell', 'FALLBACK', nil
end

local function sample()
    local gameTime = core.getGameTime()
    if not finite(gameTime) then error('non-finite game time') end
    local cell = self.cell
    local name, labelSource, regionId = locationLabel(cell)
    local hour = math.floor(gameTime / 3600) % 24
    local minute = math.floor(gameTime / 60) % 60
    local encumbrance = types.Actor.getEncumbrance(self)
    local capacity = types.Actor.getCapacity(self)
    if not finite(encumbrance) or not finite(capacity) then error('non-finite carry weight') end
    return {version=VERSION, cell=name, labelSource=labelSource, regionId=regionId,
        clock=string.format('%02d:%02d', hour, minute),
        lastReadAtGameTime=gameTime, courierArrived=courierArrived(),
        health=readStat('health'), magicka=readStat('magicka'), fatigue=readStat('fatigue'),
        encumbrance=encumbrance, capacity=capacity}
end

local function refresh()
    local screen = ui.screenSize()
    if not element or screen.x ~= screenX or screen.y ~= screenY then build() end
    local visible = enabled and I.UI.isHudVisible() and I.UI.getMode() == nil
        and self.cell ~= nil
    layout.props.visible = visible
    if visible then
        lastState = sample()
        local height = lastState.courierArrived and 224 or HEIGHT
        layout.props.size = util.vector2(WIDTH, height)
        panel.props.size, accent.props.size = util.vector2(WIDTH, height), util.vector2(3, height)
        courierNotice.props.visible, courierHint.props.visible = lastState.courierArrived, lastState.courierArrived
        location.props.text = lastState.cell
        clock.props.text = lastState.clock
        burden.props.text = string.format('TRAGLAST  %.0f / %.0f', lastState.encumbrance, lastState.capacity)
        for key, title in pairs({health='LEBEN', magicka='MAGIE', fatigue='AUSDAUER'}) do
            local stat = lastState[key]
            labels[key].props.text = string.format('%s  %.0f / %.0f', title, stat.current, stat.maximum)
            fills[key].props.size = util.vector2(trackWidths[key]*stat.ratio, 8)
        end
        if not readyPrinted then
            print('VEYRA_HUD_READY version='..VERSION..' engineStats=health,magicka,fatigue')
            readyPrinted = true
        end
    end
    element:update()
end

local function onFrame(dt)
    -- Paused frames can carry dt=0. Visibility follows UI transitions immediately.
    local okGate, mode, hud = pcall(function() return I.UI.getMode(), I.UI.isHudVisible() end)
    local gateChanged = okGate and (mode ~= lastMode or hud ~= lastHudVisibility)
    if okGate then lastMode, lastHudVisibility = mode, hud end
    elapsed = elapsed + dt
    if elapsed < PERIOD and not gateChanged then return end
    elapsed = 0
    local ok, err = pcall(refresh)
    if not ok then
        -- Hide only our panel. Existing native HUD and all gameplay remain usable.
        if layout then layout.props.visible = false end
        if element then pcall(function() element:update() end) end
        if not failurePrinted then print('VEYRA_HUD_ERROR '..tostring(err));failurePrinted=true end
    else
        failurePrinted = false
    end
end

return {
    interfaceName='VeyraPresentation',
    interface={version=VERSION, getState=function()
            if not lastState then return nil end
            local result = copy(lastState)
            result.visible = layout and layout.props.visible == true or false
            result.screen = {width=screenX, height=screenY}
            return result
        end,
        setEnabled=function(value)
            if type(value) ~= 'boolean' then return false end
            enabled=value;elapsed=PERIOD;return true
        end},
    engineHandlers={onFrame=onFrame, onLoad=function()
        destroy();elapsed=PERIOD;lastState=nil;readyPrinted=false
        lastMode, lastHudVisibility = nil, nil
    end},
}
