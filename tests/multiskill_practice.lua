-- Run from the repository root with Lua 5.1. The engine API is a fixture.
package.path = 'mod/?.lua;' .. package.path
for _, name in ipairs({'core', 'self', 'ui', 'util', 'async', 'input'}) do
    package.loaded['openmw.' .. name] = {}
end

local callback, level, werewolf
local skills = {'alchemy', 'enchant', 'armorer', 'speechcraft'}
local stats = {}
for _, skill in ipairs(skills) do
    stats[skill] = function() return {base = level} end
end
package.loaded['openmw.types'] = {NPC = {
    stats = {skills = stats},
    isWerewolf = function() return werewolf end,
}}
package.loaded['openmw.interfaces'] = {SkillProgression = {
    -- OpenMW 0.51.0 encodes each of these actions as zero within its skill.
    SKILL_USE_TYPES = {
        Alchemy_CreatePotion = 0, Enchant_Recharge = 0, Armorer_Repair = 0, Speechcraft_Success = 0,
    },
    addSkillUsedHandler = function(handler) callback = handler end,
}}
package.loaded['scripts.halveth.content_catalog'] = {books = {}}
local module = require('scripts.halveth.knowledge')
assert(type(callback) == 'function')

for _, skill in ipairs(skills) do
    local save = {version = 1, books = {}, practiceEvents = 0}
    for _, id in ipairs({'z', 'a'}) do
        save.books[id] = {title = id, skill = skill, isScroll = false, seconds = 48, studied = true, spent = false}
    end
    module.engineHandlers.onLoad(save)
    local event = {useType = 0, skillGain = 10}
    level, werewolf = 100, false
    callback(skill, event)
    level, werewolf = 10, true
    callback(skill, event)
    werewolf = false
    callback(skill, {useType = 1, skillGain = 10})
    callback(skill, {useType = 0, skillGain = 0})
    callback('sneak', event)
    callback(skill, nil)
    assert(module.engineHandlers.onSave().practiceEvents == 0)
    assert(event.skillGain == 10)

    assert(callback(skill, event) == nil)
    assert(math.abs(event.skillGain - 10.7) < 1e-9)
    local state = module.engineHandlers.onSave()
    assert(state.books.a.spent and not state.books.z.spent and state.practiceEvents == 1)
    module.engineHandlers.onLoad(state)
    local second = {useType = 0, skillGain = 20}
    callback(skill, second)
    assert(math.abs(second.skillGain - 21.4) < 1e-9)
    local third = {useType = 0, skillGain = 20}
    callback(skill, third)
    assert(third.skillGain == 20 and module.engineHandlers.onSave().practiceEvents == 3)
end
print('Four skill practice callbacks passed, including persistence and ineligible actions.')
