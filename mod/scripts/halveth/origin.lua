-- Compatibility reader for saves made with the retired Pulsar origin scene.
-- Character creation is entirely Morrowind's own sequence; no modal or choice
-- is shown and no legacy story state is used to steer the companion.
local legacyState

local function state()
    return {version=2,enabled=false,armed=false,completed=true,panelOpen=false}
end

return {interfaceName='HALVETHOrigin',
    interface={version=2,getState=state,select=function() return false end},
    engineHandlers={
        onLoad=function(data)
            if type(data)=='table' then legacyState=data else legacyState=nil end
        end,
        onSave=function() return legacyState or state() end,
    },
}
