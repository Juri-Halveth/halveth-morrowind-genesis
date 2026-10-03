-- SPDX-License-Identifier: MIT
-- One explicit owner for our interactive panels. Gameplay does not run here.
local I=require('openmw.interfaces')
local owners={
    'VeyraFieldworkPlayer','VeyraPortalPlayer','VeyraConstructionPlayer',
    'HALVETHFieldcraft','HALVETHWorldlife','HALVETHKnowledge',
    'HALVETHUniverse','HALVETHPaths','HALVETH',
}
local allowed={};for _,name in ipairs(owners)do allowed[name]=true end
local owner,ownsMode,revision=nil,false,0
local function release(name)
    if owner~=name then return false end
    owner=nil;revision=revision+1
    if ownsMode then ownsMode=false;I.UI.removeMode('Interface')end
    return true
end
local function acquire(name)
    assert(allowed[name],'Unknown panel owner')
    -- Close functions release only their own ownership; never a new owner.
    for _,other in ipairs(owners)do
        local panel=I[other]
        if other~=name and panel and type(panel.close)=='function'then panel.close()end
    end
    if owner and owner~=name then release(owner)end
    owner=name;revision=revision+1
    if not I.UI.getMode()then
        I.UI.addMode('Interface',{windows={}});ownsMode=true
    end
    return I.UI.getMode()or'Interface'
end
local function reset()
    if owner then
        local panel=I[owner]
        if panel and type(panel.close)=='function'then panel.close()else release(owner)end
    end
    owner=nil;ownsMode=false
end
return {interfaceName='VeyraPanelCoordinator',interface={version='0.1.0',
    acquire=acquire,release=release,getState=function()
        local stack={};for n,mode in ipairs(I.UI.modes)do stack[n]=mode end
        return {owner=owner,ownsMode=ownsMode,revision=revision,mode=I.UI.getMode(),modeStack=stack}
    end},engineHandlers={onLoad=reset}}
