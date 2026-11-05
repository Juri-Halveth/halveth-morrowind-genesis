-- Lua 5.1 regression harness. The engine packages below are declared doubles.
-- This checks edge behaviour, not native rendering or engine API integration.
local input = arg[1] or 'mod/scripts/veyra/hud.lua'
local mode, nativeHud, gameTime = nil, true, 9*3600+17*60
local screen = {x=2560, y=1440}
local stats = {
    health={current=43, base=100, modifier=10},
    magicka={current=25, base=50, modifier=0},
    fatigue={current=80, base=100, modifier=0},
}
local self = {cell={name='Seyda Neen'}}
local ui = {TYPE={Widget='Widget', Image='Image', Text='Text'}, elements={},
    layers={names={HUD=1},
        indexOf=function(name) return name=='HUD' and 1 or name=='VeyraPresentation' and 2 or nil end,
        insertAfter=function(after, name, options)
            assert(after=='HUD' and name=='VeyraPresentation' and options.interactive==false)
        end}}
ui.texture = function(options) assert(options.path=='Textures/veyra/white.png');return options end
ui.content = function(value) return value end
ui.screenSize = function() return screen end
ui.create = function(layout)
    local e = {layout=layout, updates=0, destroyed=false}
    function e:update() self.updates=self.updates+1 end
    function e:destroy() self.destroyed=true end
    ui.elements[#ui.elements+1]=e
    return e
end
local core = {getGameTime=function() return gameTime end}
local types = {Actor={stats={dynamic={}}, getEncumbrance=function() return 42 end,
    getCapacity=function() return 120 end}}
for _, key in ipairs({'health', 'magicka', 'fatigue'}) do
    local boundKey=key
    types.Actor.stats.dynamic[key]=function(object) assert(object==self);return stats[boundKey] end
end
local util = {vector2=function(x,y) return {x=x,y=y} end,
    color={rgb=function(r,g,b) return {r=r,g=g,b=b} end}}
local interfaces = {UI={getMode=function() return mode end,
    isHudVisible=function() return nativeHud end}}
for name, value in pairs({core=core, self=self, types=types, ui=ui, util=util, interfaces=interfaces}) do
    package.loaded['openmw.'..name]=value
end
local module = assert(loadfile(input))()
local function frame() module.engineHandlers.onFrame(0.11) end
local function visible() return ui.elements[#ui.elements].layout.props.visible end
local tests=0
local function check(name, fn) fn();tests=tests+1;print('PASS '..name) end

check('bound engine values including modifier', function()
    frame();local s=module.interface.getState()
    assert(visible() and s.health.current==43 and s.health.maximum==110)
    assert(s.health.ratio==43/110 and s.cell=='Seyda Neen' and s.clock=='09:17')
    assert(s.encumbrance==42 and s.capacity==120)
end)
check('negative fatigue retained while bar bounded', function()
    stats.fatigue.current=-10;frame()
    local s=module.interface.getState();assert(s.fatigue.current==-10 and s.fatigue.ratio==0)
end)
check('zero and overflow maximums avoid invalid geometry', function()
    stats.magicka.base=0;stats.magicka.current=0;stats.health.current=1000;frame()
    local s=module.interface.getState();assert(s.magicka.ratio==0 and s.health.ratio==1)
    stats.magicka.base=50;stats.health.current=43
end)
check('menus and native HUD visibility respected', function()
    mode='Dialogue';frame();assert(not visible())
    mode=nil;nativeHud=false;frame();assert(not visible())
    nativeHud=true;frame();assert(visible())
end)
check('enabled input strictly boolean and reversible', function()
    assert(module.interface.setEnabled('false')==false)
    assert(module.interface.setEnabled(false)==true);frame();assert(not visible())
    assert(module.interface.setEnabled(true)==true);frame();assert(visible())
end)
check('game clock wraps midnight and location follows player', function()
    gameTime=25*3600+3*60;self.cell.name='Balmora';frame()
    local s=module.interface.getState();assert(s.clock=='01:03' and s.cell=='Balmora')
end)
check('window resize and load clean up owned widgets', function()
    local before=ui.elements[#ui.elements];screen={x=1280,y=720};frame()
    assert(before.destroyed and visible())
    before=ui.elements[#ui.elements];module.engineHandlers.onLoad()
    assert(before.destroyed and module.interface.getState()==nil);frame();assert(visible())
end)
check('invalid observation hides panel without changing engine state', function()
    stats.health.current=0/0;frame();assert(not visible() and nativeHud)
    stats.health.current=43;frame();assert(visible())
end)
check('unloaded player cell defers display', function()
    self.cell=nil;frame();assert(not visible())
    self.cell={name='Seyda Neen'};frame();assert(visible())
end)
check('courier hint only ARRIVED and read-only optional dependency', function()
    assert(module.interface.getState().courierArrived==false)
    interfaces.VeyraCourierPlayer={getState=function() return {phase='APPROACH'} end}
    frame();assert(module.interface.getState().courierArrived==false)
    interfaces.VeyraCourierPlayer={getState=function() return {phase='ARRIVED'} end}
    frame();assert(module.interface.getState().courierArrived==true)
    local content=ui.elements[#ui.elements].layout.content
    local notice=false
    for _, row in ipairs(content) do
        if row.name=='courier_hint' then
            notice=true;assert(row.props.visible and row.props.text=='[F10] Sendung annehmen')
        end
    end
    assert(notice)
    interfaces.VeyraCourierPlayer={getState=function() return {phase='CLAIMED'} end}
    frame();assert(module.interface.getState().courierArrived==false)
end)
check('optional courier failure leaves main panel usable', function()
    interfaces.VeyraCourierPlayer={getState=function() error('optional module unavailable') end}
    frame();assert(visible() and module.interface.getState().courierArrived==false)
    interfaces.VeyraCourierPlayer=nil
end)
check('snapshot exposes render declaration time screen without mutable aliases', function()
    frame();local state=module.interface.getState()
    assert(state.visible and state.screen.width==1280 and state.screen.height==720)
    assert(state.lastReadAtGameTime==gameTime)
    state.health.current=-999;state.screen.width=0
    assert(module.interface.getState().health.current==43 and module.interface.getState().screen.width==1280)
    mode='Dialogue';frame();assert(not module.interface.getState().visible);mode=nil
end)
check('paused dt zero UI transitions refresh visibility immediately with stable-frame throttle', function()
    frame();assert(visible())
    local element=ui.elements[#ui.elements]
    local before=element.updates
    mode='Interface';module.engineHandlers.onFrame(0)
    assert(not visible() and not module.interface.getState().visible and element.updates==before+1)
    module.engineHandlers.onFrame(0);assert(element.updates==before+1)
    mode=nil;module.engineHandlers.onFrame(0);assert(visible())
    nativeHud=false;module.engineHandlers.onFrame(0);assert(not visible())
    nativeHud=true;module.engineHandlers.onFrame(0);assert(visible())
end)
print('HUD_MODEL_PASS tests='..tests..' engine=DECLARED_DOUBLES native=NOT_TESTED')
