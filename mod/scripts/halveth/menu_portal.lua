-- Original portal artwork and a clean native OpenMW main-menu surface.
-- The familiar save picker and options remain available through "Mehr".
local ui = require('openmw.ui')
local util = require('openmw.util')
local menu = require('openmw.menu')
local async = require('openmw.async')
local vfs = require('openmw.vfs')

local ART = 'textures/halveth/portal-menu-2100.png'
local LAYER = 'HALVETHPortalMenu'
local VERSION = 'HALVETH NEW MORROWIND 2026 REBORN  ·  VERSION X'
local elements = {}
local resource, lastWidth, lastHeight
local revealed = false
local errorReported = false

local function clear()
    for _,element in ipairs(elements) do element:destroy() end
    elements = {}
end

local function add(layout)
    local element = ui.create(layout)
    elements[#elements+1] = element
end

local function label(text, x, y, width, height, textSize, color, action)
    local layout = {type=ui.TYPE.Text, layer=LAYER,
        props={position=util.vector2(x,y), size=util.vector2(width,height),
            autoSize=false, text=text, textSize=textSize, textColor=color}}
    if action then layout.events={mouseClick=async:callback(function()
        print('HALVETH_MENU_CLICK '..text)
        action()
    end)} end
    add(layout)
end

local function revealClassic()
    clear()
    revealed = true
    print('HALVETH_MENU_CLASSIC_REVEALED')
end

local function continueGame()
    local newestDir, newestSlot, newestTime
    for directory,saves in pairs(menu.getAllSaves()) do
        for slot,info in pairs(saves) do
            local time = tonumber(info.creationTime) or 0
            if not newestTime or time > newestTime then
                newestDir, newestSlot, newestTime = directory, slot, time
            end
        end
    end
    if newestSlot then
        menu.loadGame(newestDir, newestSlot)
    else
        ui.showMessage('Noch kein Spielstand. Beginne eine neue Reise.')
    end
end

local function draw()
    if menu.getState() ~= menu.STATE.NoGame then
        clear()
        return
    end
    if revealed then return end
    if not vfs.fileExists(ART) or not ui.layers.indexOf('MainMenu') then return end
    if not ui.layers.indexOf(LAYER) then
        ui.layers.insertAfter('MainMenu', LAYER, {interactive=true})
    end
    local size = ui.screenSize()
    if #elements > 0 and size.x == lastWidth and size.y == lastHeight then return end
    clear()
    resource = resource or ui.texture{path=ART}
    add{type=ui.TYPE.Image, layer=LAYER,
        props={position=util.vector2(0,0), size=size, resource=resource},
        events={mouseClick=async:callback(function() end)}}

    local left = math.floor(size.x * 0.615)
    local width = math.floor(size.x * 0.35)
    local ivory = util.color.rgb(1.0,0.88,0.72)
    local pale = util.color.rgb(0.91,0.84,0.80)
    label('HALVETH', left, math.floor(size.y*0.13), width, 78, 51, ivory)
    label('MORROWIND  ·  REBORN', left, math.floor(size.y*0.13)+70, width, 42, 24, pale)

    local start = math.floor(size.y*0.47)
    local gap = math.max(48, math.floor(size.y*0.066))
    label('FORTSETZEN', left, start, width, 45, 30, ivory, continueGame)
    label('NEUE REISE', left, start+gap, width, 45, 30, ivory, menu.newGame)
    label('SPIELSTAENDE / OPTIONEN', left, start+2*gap, width, 40, 21, pale, revealClassic)
    label('VERLASSEN', left, start+3*gap, width, 40, 21, pale, menu.quit)

    local versionWidth = math.floor(size.x*0.34)
    label(VERSION, size.x-versionWidth-18, size.y-29, versionWidth, 21, 11,
          util.color.rgb(0.76,0.70,0.72))
    lastWidth, lastHeight = size.x, size.y
    print('HALVETH_MENU_PORTAL_READY '..tostring(size.x)..'x'..tostring(size.y))
end

return {engineHandlers={onFrame=function()
    local ok,err=pcall(draw)
    if not ok and not errorReported then
        errorReported=true
        print('HALVETH_MENU_PORTAL_ERROR '..tostring(err))
        clear()
    end
end}}
