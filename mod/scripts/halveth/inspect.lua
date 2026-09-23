-- Native, read-only descriptions. Values come from the active load order.
local core=require('openmw.core')
local types=require('openmw.types')
local C=require('scripts.halveth.common')
local M={}
local function number(n) return string.format('%.1f',n or 0):gsub('%.0$','') end
local function recordName(records,id)
    local r=id and records[id]
    return r and r.name or id or '?'
end
local skillLabels={block='Blocken',armorer='Schmiedekunst',mediumarmor='Mittlere Ruestung',heavyarmor='Schwere Ruestung',
    bluntweapon='Stumpfe Waffen',longblade='Langwaffen',axe='Axt',spear='Speer',athletics='Athletik',enchant='Verzauberung',
    destruction='Zerstoerung',alteration='Veraenderung',illusion='Illusion',conjuration='Beschwoerung',mysticism='Mystik',
    restoration='Wiederherstellung',alchemy='Alchemie',unarmored='Ohne Ruestung',security='Sicherheit',sneak='Schleichen',
    acrobatics='Akrobatik',lightarmor='Leichte Ruestung',shortblade='Kurzwaffen',marksman='Schuetze',mercantile='Handel',
    speechcraft='Wortgewandtheit',handtohand='Nahkampf'}
local attributeLabels={strength='Staerke',intelligence='Intelligenz',willpower='Willenskraft',agility='Geschicklichkeit',
    speed='Schnelligkeit',endurance='Konstitution',personality='Charisma',luck='Glueck'}
local serviceLabels={Barter='Handel',Spells='Zauber',Spellmaking='Zauber erstellen',Enchanting='Verzaubern',
    Training='Training',Repair='Reparieren',Travel='Reisen'}
local families={{'Weapon','Waffe'},{'Armor','Ruestung'},{'Clothing','Kleidung'},{'Book','Text'},
    {'Ingredient','Zutat'},{'Potion','Trank'},{'Apparatus','Alchemiegeraet'},{'Light','Licht'},
    {'Lockpick','Dietrich'},{'Probe','Sonde'},{'Repair','Werkzeug'},{'Miscellaneous','Gegenstand'}}
function M.kind(object)
    for _,family in ipairs(families) do if types[family[1]].objectIsInstance(object) then return family[2],family[1] end end
    return 'Gegenstand','Item'
end
function M.actor(object,player)
    local r=object.type.record(object)
    local info={id=object.id,recordId=object.recordId,name=r.name or object.recordId,
        kind=types.NPC.objectIsInstance(object) and 'npc' or 'creature',
        cell=object.cell and object.cell.name or '',isDead=types.Actor.isDead(object)}
    for _,key in ipairs({'health','magicka','fatigue'}) do
        local s=types.Actor.stats.dynamic[key](object)
        info[key]={current=s.current,max=s.base+s.modifier}
    end
    if info.kind=='npc' then
        info.race,info.class=r.race,r.class
        local class=types.NPC.classes.records[r.class]
        info.raceName=recordName(types.NPC.races.records,r.race)
        info.className=class and class.name or r.class
        info.classDescription=class and C.head(class.description or '',700) or ''
        info.factions=C.array()
        for _,id in ipairs(types.NPC.getFactions(object)) do info.factions[#info.factions+1]=id end
        info.services=C.array()
        for key in pairs(serviceLabels) do if r.servicesOffered[key] then info.services[#info.services+1]=key end end
        table.sort(info.services)
        if player and object.id~=player.id then info.disposition=types.NPC.getDisposition(object,player) end
    end
    return info
end
function M.actorText(object,player)
    local info=M.actor(object,player)
    local out={info.name,string.format('%s | %s',info.raceName or 'Wesen',info.className or 'Kreatur'),info.cell}
    if info.isDead then out[#out+1]='Lebenszustand: verstorben.' end
    for _,pair in ipairs({{'health','Leben'},{'magicka','Magicka'},{'fatigue','Ausdauer'}}) do
        local s=info[pair[1]];out[#out+1]=pair[2]..': '..number(s.current)..' / '..number(s.max)
    end
    if info.disposition then out[#out+1]='Disposition zu dir: '..number(info.disposition)..' / 100' end
    if info.factions and #info.factions>0 then out[#out+1]='Zugehoerigkeit: '..table.concat(info.factions,', ') end
    if info.services and #info.services>0 then
        local names={};for _,key in ipairs(info.services) do names[#names+1]=serviceLabels[key] end
        out[#out+1]='Angebote: '..table.concat(names,', ')
    end
    if info.classDescription and #info.classDescription>0 then out[#out+1]='Beruf im Spiel:\n'..info.classDescription end
    if object.id==player.id then
        local attributes={}
        for _,id in ipairs({'strength','intelligence','willpower','agility','speed','endurance','personality','luck'}) do
            local s=types.Actor.stats.attributes[id](object)
            attributes[#attributes+1]=attributeLabels[id]..': '..number(s.modified)
        end
        out[#out+1]='ATTRIBUTE\n'..table.concat(attributes,'\n')
        out[#out+1]='Volle Ausdauer hilft bei Angriffen und Zaubern. Passende Fertigkeiten, Zustand und Effekte wirken zusaetzlich.'
    end
    return table.concat(out,'\n\n'),info
end
function M.skills(object)
    local out={}
    local class=types.NPC.classes.records[types.NPC.record(object).class]
    local ranks={}
    if class then
        for _,id in ipairs(class.majorSkills) do ranks[id]='Hauptfertigkeit' end
        for _,id in ipairs(class.minorSkills) do ranks[id]='Nebenfertigkeit' end
    end
    for id,label in pairs(skillLabels) do
        local s=types.NPC.stats.skills[id](object)
        out[#out+1]={id=id,title=label,value=s.modified,base=s.base,rank=ranks[id] or 'Sonstige Fertigkeit',progress=s.progress}
    end
    table.sort(out,function(a,b) return a.title<b.title end)
    return out
end
function M.effects(effects)
    local out={}
    for _,effect in ipairs(effects or {}) do
        local r=effect.effect
        local line=(r and r.name or effect.id or 'Effekt')
        if effect.affectedSkill and effect.affectedSkill~='' then line=line..' ('..(skillLabels[effect.affectedSkill] or effect.affectedSkill)..')' end
        if effect.affectedAttribute and effect.affectedAttribute~='' then line=line..' ('..(attributeLabels[effect.affectedAttribute] or effect.affectedAttribute)..')' end
        if not r or r.hasMagnitude then line=line..' | Staerke '..number(effect.magnitudeMin)..'–'..number(effect.magnitudeMax) end
        if r and r.hasDuration then line=line..' | '..number(effect.duration)..' s' end
        local range=effect.range==core.magic.RANGE.Self and 'Selbst' or effect.range==core.magic.RANGE.Touch and 'Beruehrung' or 'Ziel'
        line=line..' | '..range
        if effect.area and effect.area>0 then line=line..' | Flaeche '..number(effect.area) end
        if r then
            line=line..'\n'..(skillLabels[r.school] or r.school or '')..(r.harmful and ' · schaedlich' or ' · unterstuetzend')
            if r.description and #r.description>0 then line=line..'\n'..r.description end
        end
        out[#out+1]=line
    end
    return table.concat(out,'\n\n')
end
function M.spell(record)
    local kind=record.type==core.magic.SPELL_TYPE.Spell and 'Zauber' or record.type==core.magic.SPELL_TYPE.Power and 'Kraft' or 'Dauerwirkung / Zustand'
    return table.concat({record.name,kind,'Basiskosten: '..number(record.cost)..' Magicka'..(record.isAutocalc and ' (automatische Engine-Berechnung)' or ''),
        M.effects(record.effects),'Wirkung am Ziel kann durch Widerstand, Absorption und Reflexion veraendert werden.\nAuswahl bereitet den Zauber vor; gezaubert wird mit deiner normalen Spielsteuerung.'},'\n\n')
end
function M.item(object,player)
    local r=object.type.record(object)
    local label,kind=M.kind(object)
    local out={r.name or object.recordId,label..' | Anzahl: '..tostring(object.count),
        'Gewicht je Stueck: '..number(r.weight)..' | Basiswert: '..number(r.value)..' Gold'}
    if r.weight and r.weight>0 then out[#out+1]='Wert / Gewicht: '..number((r.value or 0)/r.weight) end
    local d=types.Item.itemData(object)
    if r.health and r.health>0 and d.condition then out[#out+1]='Zustand: '..number(d.condition)..' / '..number(r.health) end
    if kind=='Weapon' then
        out[#out+1]=string.format('Hieb: %s–%s\nSchlag: %s–%s\nStoss: %s–%s\nTempo: %s | Reichweite: %s',
            number(r.chopMinDamage),number(r.chopMaxDamage),number(r.slashMinDamage),number(r.slashMaxDamage),
            number(r.thrustMinDamage),number(r.thrustMaxDamage),number(r.speed),number(r.reach))
        out[#out+1]='Die Spanne haengt vom Aufladen des Angriffs ab. Trefferchance und tatsaechlicher Schaden beruecksichtigen Fertigkeit, Ausdauer, Waffenstand und die Abwehr des Ziels.'
    elseif kind=='Armor' then
        out[#out+1]='Basis-Ruestungswert: '..number(r.baseArmor)..'\nDeine passende Ruestungsfertigkeit und der Zustand bestimmen den wirksamen Schutz.'
    elseif kind=='Ingredient' then
        local level=types.NPC.stats.skills.alchemy(player).modified
        local step=core.getGMST('fWortChanceValue')
        local known={}
        for index,effect in ipairs(r.effects) do
            local required=(effect.index+1)*step
            if level>=required then known[#known+1]=(effect.effect and effect.effect.name or effect.id)
            else known[#known+1]='Unbekannter Effekt – Alchemie '..number(required)..' erforderlich' end
        end
        out[#out+1]='ERKENNBARE EFFEKTE\n'..table.concat(known,'\n')
        out[#out+1]='Zwei Zutaten mit gleichem Effekt koennen einen Trank ergeben. Mit dem Moerser oeffnest du die normale Alchemie.'
    elseif kind=='Potion' then out[#out+1]=M.effects(r.effects)
    elseif kind=='Book' then out[#out+1]=r.isScroll and 'Schriftrolle: im Originalfenster lesen oder eine Verzauberung im normalen Inventar benutzen.' or 'Lesen oeffnet das Originalbuch. Das Wissensjournal merkt deine Entdeckung.'
    elseif kind=='Apparatus' then out[#out+1]='Qualitaet: '..number(r.quality)..'\nAlchemiegeraete wirken im normalen Alchemiefenster.' end
    if r.enchant and r.enchant~='' then
        local ench=core.magic.enchantments.records[r.enchant]
        if ench then out[#out+1]='VERZAUBERUNG\n'..M.effects(ench.effects) end
        if d.enchantmentCharge then out[#out+1]='Aktuelle Ladung: '..number(d.enchantmentCharge) end
    end
    if d.soul and d.soul~='' then out[#out+1]='Gebundene Seele: '..recordName(types.Creature.records,d.soul) end
    out[#out+1]='Basiswerte stammen aus deinem geladenen Spiel. Handelspreise sind davon verschieden.'
    return table.concat(out,'\n\n')
end
return M
