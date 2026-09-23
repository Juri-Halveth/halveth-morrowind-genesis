-- Native TES III/OpenMW records. Loaded as a GLOBAL script.
-- Own books and spell designs; models/icons/effects resolve from the user's game.
local core = require('openmw.core')
local world = require('openmw.world')
local types = require('openmw.types')
local Catalog = require('scripts.halveth.content_catalog')

local bookIds, spellIds, pending = {}, {}, {}

local function escape(text)
    return text:gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;')
end

local function bookText(book)
    local parts = {'<DIV ALIGN="CENTER"><FONT COLOR="703c36">', escape(book.title),
        '</FONT><BR>', escape(book.author), '</DIV><BR><BR>'}
    for index, page in ipairs(book.pages) do
        parts[#parts + 1] = '<FONT COLOR="703c36">' .. tostring(index) .. '</FONT><BR>'
        parts[#parts + 1] = escape(page.text) .. '<BR><BR>'
    end
    parts[#parts + 1] = '<DIV ALIGN="CENTER">HALVETH - Aufzeichnungen des Gartens</DIV>'
    return table.concat(parts)
end

local function findModel(isScroll)
    -- Copy paths only, never another author's text, enchantment, quest or script.
    for _, record in pairs(types.Book.records) do
        if record.isScroll == isScroll and record.model ~= '' and record.icon ~= '' then
            return record.model, record.icon
        end
    end
    error('Kein passendes Buchmodell in den geladenen Morrowind-Daten vorhanden.')
end

local function ensureBook(book)
    local text = bookText(book)
    local saved = bookIds[book.key] and types.Book.records[bookIds[book.key]]
    if saved and saved.name == book.title and saved.text == text then return saved end
    -- A Lua hot reload may reset the script cache while the world retains records.
    for _, record in pairs(types.Book.records) do
        if record.name == book.title and record.text == text then
            bookIds[book.key] = record.id
            return record
        end
    end
    local model, icon = findModel(book.isScroll)
    local record = world.createRecord(types.Book.createRecordDraft({
        name = book.title, model = model, icon = icon, text = text,
        weight = book.isScroll and 0.1 or 0.5, value = 0,
        isScroll = book.isScroll, enchantCapacity = 0,
        skill = '', enchant = '', mwscript = '',
    }))
    bookIds[book.key] = record.id
    return record
end

local function spellMatches(record, spell)
    if not record or record.name ~= spell.title or record.cost ~= spell.cost or
        record.type ~= core.magic.SPELL_TYPE.Spell or #record.effects ~= #spell.effects or
        not record.alwaysSucceedFlag then return false end
    for index, effect in ipairs(spell.effects) do
        local actual = record.effects[index]
        if actual.id ~= effect.id or actual.range ~= core.magic.RANGE[effect.range] or
            actual.area ~= effect.area or actual.duration ~= effect.duration or
            actual.magnitudeMin ~= effect.magnitudeMin or actual.magnitudeMax ~= effect.magnitudeMax then
            return false
        end
    end
    return true
end

local function ensureSpell(spell)
    local saved = spellIds[spell.key] and core.magic.spells.records[spellIds[spell.key]]
    if spellMatches(saved, spell) then return saved end
    for _, record in pairs(core.magic.spells.records) do
        if spellMatches(record, spell) then
            spellIds[spell.key] = record.id
            return record
        end
    end
    local effects = {}
    for _, effect in ipairs(spell.effects) do
        assert(core.magic.effects.records[effect.id], 'Fehlender Morrowind-Magieeffekt: ' .. effect.id)
        effects[#effects + 1] = {
            id = effect.id, range = core.magic.RANGE[effect.range], area = effect.area,
            magnitudeMin = effect.magnitudeMin, magnitudeMax = effect.magnitudeMax,
            duration = effect.duration,
        }
    end
    local record = world.createRecord(core.magic.spells.createRecordDraft({
        name = spell.title, type = core.magic.SPELL_TYPE.Spell, cost = spell.cost,
        effects = effects, alwaysSucceedFlag = true, starterSpellFlag = false, isAutocalc = false,
    }))
    spellIds[spell.key] = record.id
    return record
end

local function inspect(player)
    local result = {books = {}, spells = {}, bookCount = 0, spellCount = 0, inventoryBooks = 0, knownSpells = 0}
    local inventory, learned = types.Actor.inventory(player), types.Actor.spells(player)
    for _, book in ipairs(Catalog.books) do
        local id = bookIds[book.key]
        if id and types.Book.records[id] then
            local count = inventory:countOf(id)
            result.books[#result.books + 1] = {key = book.key, recordId = id,
                title = book.title, skill = book.skill, count = count}
            result.bookCount = result.bookCount + 1
            result.inventoryBooks = result.inventoryBooks + count
        end
    end
    for _, spell in ipairs(Catalog.spells) do
        local id = spellIds[spell.key]
        if id and core.magic.spells.records[id] then
            local known = learned[id] ~= nil
            result.spells[#result.spells + 1] = {key = spell.key, recordId = id,
                title = spell.title, known = known, cost = spell.cost}
            result.spellCount = result.spellCount + 1
            if known then result.knownSpells = result.knownSpells + 1 end
        end
    end
    return result
end

local function reply(player, requestId, success, message, request)
    local result = inspect(player)
    result.requestId, result.success, result.message, result.request = requestId, success, message, request
    player:sendEvent('HALVETH_ContentResult', result)
end

local function request(data)
    if type(data) ~= 'table' then return end
    local player = data.player
    if not player or not player:isValid() or not types.Player.objectIsInstance(player) then return end
    if type(data.requestId) ~= 'string' or #data.requestId > 160 then return end
    if data.request ~= 'library' and data.request ~= 'spells' and data.request ~= 'both' and data.request ~= 'inspect' then
        reply(player, data.requestId, false, 'Unbekannter Inhaltswunsch.', data.request)
        return
    end
    if pending[player.id] then
        reply(player, data.requestId, false, 'Die angeforderten Inhalte werden gerade ins Spiel eingefuegt.', data.request)
        return
    end
    if data.request == 'inspect' then
        reply(player, data.requestId, true, 'Aktueller Bestand der HALVETH-Inhalte.', data.request)
        return
    end
    pending[player.id] = {player = player, requestId = data.requestId, request = data.request, frames = 0}
    local ok, err = pcall(function()
        if data.request == 'library' or data.request == 'both' then
            local inventory = types.Actor.inventory(player)
            for _, book in ipairs(Catalog.books) do
                local record = ensureBook(book)
                if inventory:countOf(record.id) == 0 then world.createObject(record.id, 1):moveInto(inventory) end
            end
        end
        if data.request == 'spells' or data.request == 'both' then
            local learned = types.Actor.spells(player)
            for _, spell in ipairs(Catalog.spells) do
                local record = ensureSpell(spell)
                if not learned[record.id] then learned:add(record.id) end
            end
        end
    end)
    if not ok then pending[player.id].error = tostring(err) end
end

local function update()
    for id, item in pairs(pending) do
        item.frames = item.frames + 1
        if item.frames >= 5 then
            pending[id] = nil
            if item.player:isValid() then
                local current = inspect(item.player)
                local booksOK = item.request == 'spells' or current.inventoryBooks >= #Catalog.books
                local spellsOK = item.request == 'library' or current.knownSpells == #Catalog.spells
                local success = not item.error and booksOK and spellsOK
                local message
                if not success then
                    message = 'Inhalte konnten nicht vollstaendig eingefuegt werden: ' .. (item.error or 'Spielbestand noch unvollstaendig.')
                elseif item.request == 'library' then
                    message = 'Sechs eigene Buecher liegen im Inventar. Oeffne sie im normalen Morrowind-Buchfenster.'
                elseif item.request == 'spells' then
                    message = 'LOVE, SPARK und AEGIS stehen im normalen Zaubermenue. Auswaehlen und wie gewohnt zaubern.'
                else
                    message = 'Sechs Buecher im Inventar; LOVE, SPARK und AEGIS im Zaubermenue.'
                end
                reply(item.player, item.requestId, success, message, item.request)
            end
        end
    end
end

return {
    engineHandlers = {
        onUpdate = update,
        onSave = function() return {version = 1, bookIds = bookIds, spellIds = spellIds} end,
        onLoad = function(data)
            pending = {}
            bookIds = data and type(data.bookIds) == 'table' and data.bookIds or {}
            spellIds = data and type(data.spellIds) == 'table' and data.spellIds or {}
        end,
        onNewGame = function() bookIds = {}; spellIds = {}; pending = {} end,
    },
    eventHandlers = {HALVETH_ContentRequest = request},
}
