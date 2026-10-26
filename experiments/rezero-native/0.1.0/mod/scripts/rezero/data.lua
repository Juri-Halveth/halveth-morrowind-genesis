-- REZERO 0.1.0: source-bound game data and ordinary engine item actions.
local core=require('openmw.core')
local types=require('openmw.types')
local self=require('openmw.self')
local M={}
local labels={weapon='Waffe',armor='Rüstung',clothing='Kleidung',potion='Trank',ingredient='Zutat',book='Schrift',other='Gegenstand'}
local function valid(n) return type(n)=='number' and n==n and math.abs(n)<1e12 end
local function num(n) return valid(n) and n or 0 end
local function fmt(n,pattern) return valid(n) and string.format(pattern or '%.0f',n) or '—' end
function M.kind(object)
    for _,name in ipairs{'Weapon','Armor','Clothing','Potion','Ingredient','Book'} do
        if types[name].objectIsInstance(object) then return name:lower() end
    end
    return 'other'
end
function M.collect(tab)
    local entries,equipped={},{}
    for _,object in pairs(types.Actor.getEquipment(self)) do equipped[object.id]=true end
    if tab=='magic' then
        for _,spell in pairs(types.Actor.spells(self)) do
            entries[#entries+1]={id=spell.id,recordId=spell.id,name=spell.name or spell.id,kind='spell',spell=spell,
                count=1,value=0,weight=0,castable=spell.type==core.magic.SPELL_TYPE.Spell or spell.type==core.magic.SPELL_TYPE.Power}
        end
    else
        for _,object in ipairs(types.Actor.inventory(self):getAll()) do
            if object:isValid() and object.count>0 then
                local record=object.type.record(object)
                entries[#entries+1]={id=object.id,recordId=object.recordId,name=record.name or object.recordId,
                    kind=M.kind(object),object=object,record=record,count=object.count,
                    weight=num(record.weight),value=num(record.value),equipped=equipped[object.id] or false}
            end
        end
    end
    return entries
end
function M.spellType(entry)
    return entry.spell.type==core.magic.SPELL_TYPE.Power and 'KRAFT' or entry.castable and 'ZAUBER' or 'PASSIV'
end
function M.effects(parameters,ingredient)
    local lines={}
    for _,parameter in ipairs(parameters or {}) do
        local effect=parameter.effect
        local line=tostring(effect and effect.name or parameter.id or 'Effekt')
        if not ingredient and effect and effect.hasMagnitude then line=line..' · '..fmt(parameter.magnitudeMin)..'–'..fmt(parameter.magnitudeMax) end
        if not ingredient and effect and effect.hasDuration then line=line..' · '..fmt(parameter.duration)..' s' end
        if num(parameter.area)>0 then line=line..' · Fläche '..fmt(parameter.area) end
        lines[#lines+1]=line
    end
    return table.concat(lines,'\n')
end
function M.description(entry)
    if not entry then return 'Wähle einen Gegenstand oder gleite für die Vorschau darüber.' end
    if entry.kind=='spell' then
        local spell=entry.spell
        local lines={M.spellType(entry)}
        if not entry.castable then lines[#lines+1]='Dieser Effekt ist automatisch aktiv.'
        elseif spell.type==core.magic.SPELL_TYPE.Power then lines[#lines+1]='Einmal pro Tag'
        elseif spell.isAutocalc then lines[#lines+1]='Magiekosten werden vom Spiel berechnet.'
        else lines[#lines+1]='Grundkosten '..fmt(spell.cost)..' Magie' end
        lines[#lines+1]='\n'..M.effects(spell.effects)
        local first=spell.effects and spell.effects[1]
        if first and first.effect and first.effect.description then lines[#lines+1]='\n'..first.effect.description end
        return table.concat(lines,'\n')
    end
    local r=entry.record
    local lines={(labels[entry.kind] or labels.other):upper(),
        'Gewicht '..fmt(r.weight,'%.2f')..'  ·  Wert '..fmt(r.value),
        'Anzahl '..fmt(entry.count)..(entry.equipped and '  ·  Ausgerüstet' or '')}
    if entry.kind=='weapon' then
        lines[#lines+1]='\nHieb '..fmt(r.chopMinDamage)..'–'..fmt(r.chopMaxDamage)..'  ·  Schlag '..fmt(r.slashMinDamage)..'–'..fmt(r.slashMaxDamage)
        lines[#lines+1]='Stich '..fmt(r.thrustMinDamage)..'–'..fmt(r.thrustMaxDamage)
        lines[#lines+1]='Tempo '..fmt(r.speed,'%.2f')..'  ·  Reichweite '..fmt(r.reach,'%.2f')
    elseif entry.kind=='armor' then lines[#lines+1]='\nGrundrüstung '..fmt(r.baseArmor)
    elseif entry.kind=='ingredient' then lines[#lines+1]='\nZUTATENEFFEKTE\n'..M.effects(r.effects,true)..'\nStärke und Dauer entstehen bei der Alchemie.'
    elseif entry.kind=='potion' then lines[#lines+1]='\n'..M.effects(r.effects)
    elseif entry.kind=='book' then
        local excerpt=(r.text or ''):gsub('<[^>]*>',' '):gsub('%s+',' ')
        if #excerpt>320 then
            local cut=317
            while cut>0 and excerpt:byte(cut+1)>=128 and excerpt:byte(cut+1)<192 do cut=cut-1 end
            excerpt=excerpt:sub(1,cut)..'…'
        end
        lines[#lines+1]='\n'..excerpt
    end
    local itemData=types.Item.itemData(entry.object)
    if r.health then lines[#lines+1]='Zustand '..fmt(itemData.condition or r.health)..' / '..fmt(r.health) end
    if r.enchant and r.enchant~='' then
        local enchantment=core.magic.enchantments.records[r.enchant]
        if enchantment then lines[#lines+1]='\nVERZAUBERUNG\nLadung '..fmt(itemData.enchantmentCharge or enchantment.charge)..' / '..fmt(enchantment.charge)..'\n'..M.effects(enchantment.effects) end
    end
    return table.concat(lines,'\n')
end
function M.actionLabel(entry)
    if not entry then return 'Auswahl fehlt' end
    if entry.kind=='spell' then return entry.castable and 'Zauber auswählen' or 'Passiver Effekt' end
    if entry.equipped then return 'Ablegen' end
    if entry.kind=='weapon' or entry.kind=='armor' or entry.kind=='clothing' then return 'Ausrüsten' end
    return entry.kind=='book' and 'Lesen' or 'Benutzen'
end
function M.act(entry)
    if not entry then return false end
    if entry.kind=='spell' then
        if not entry.castable then return false end
        types.Actor.setSelectedSpell(self,entry.spell)
    elseif entry.object and entry.object:isValid() and entry.object.count>0 then
        if entry.equipped then
            local equipment={}
            for slot,object in pairs(types.Actor.getEquipment(self)) do if object.id~=entry.id then equipment[slot]=object end end
            types.Actor.setEquipment(self,equipment)
        else core.sendGlobalEvent('UseItem',{actor=self.object,object=entry.object}) end
    else return false end
    return true
end
function M.vitals()
    local list={}
    for _,pair in ipairs{{'health','LEBEN'},{'magicka','MAGIE'},{'fatigue','AUSDAUER'}} do
        local stat=types.Actor.stats.dynamic[pair[1]](self)
        list[#list+1]={id=pair[1],name=pair[2],current=stat.current,maximum=stat.base+stat.modifier}
    end
    return list
end
function M.attributes()
    local values={}
    for _,pair in ipairs{{'strength','Stärke'},{'intelligence','Intelligenz'},{'willpower','Willenskraft'},{'agility','Geschick'},{'speed','Tempo'},{'endurance','Konstitution'},{'personality','Charisma'},{'luck','Glück'}} do
        local stat=types.Actor.stats.attributes[pair[1]](self)
        values[#values+1]={id=pair[1],name=pair[2],value=stat.modified}
    end
    return values
end
function M.capacity() return types.Actor.getEncumbrance(self),types.Actor.getCapacity(self) end
return M
