-- HALVETH knowledge lives in the real OpenMW player and its ordinary savegame.
-- Source books and vanilla alchemy remain engine objects; this is an additive guide.
local core = require('openmw.core')
local self = require('openmw.self')
local types = require('openmw.types')
local ui = require('openmw.ui')
local util = require('openmw.util')
local async = require('openmw.async')
local input = require('openmw.input')
local I = require('openmw.interfaces')
local C = require('scripts.halveth.common')
local catalog = require('scripts.halveth.content_catalog')

local MAX_BOOKS, MAX_SECONDS = 4096, 120
local books, selectedId, activeId, activeObject = {}, nil, nil, nil
local practiceEvents, lastPractice = 0, nil
local plannedPair, recipeIndex, restoreRecipeSelection = nil, 1, false
local window, leftText, rightText, footerText, addedMode, panelMode
local page, lastRefresh, requestSerial = 0, 0, 0
local lastFrameTime
local message = 'Lies ein echtes Buch oder eine Schriftrolle. F7 sammelt dein Wissen im Spiel.'
local pendingContent = {}
local retainedInvalidSave
local refresh,close,open

local function finite(n) return C.finite(n) end
local function validId(s)
    return type(s) == 'string' and #s > 0 and #s <= 256 and not s:find('[%z\1-\31]')
end
local function countBooks()
    local n = 0
    for _ in pairs(books) do n = n + 1 end
    return n
end
local function sortedIds()
    local ids = {}
    for id in pairs(books) do ids[#ids+1] = id end
    table.sort(ids, function(a,b)
        if books[a].title == books[b].title then return a < b end
        return books[a].title < books[b].title
    end)
    return ids
end
local function ownEntry(title)
    for _, entry in ipairs(catalog.books) do
        if entry.title == title then return entry end
    end
end
local function feedback(text)
    message = text
    if footerText then footerText.props.text = text end
    if window then window:update() end
end
local function subjectName(skill)
    return ({alchemy='Alchemie',enchant='Verzauberung',armorer='Schmiedekunst',speechcraft='Wortgewandtheit'})[skill]
        or (skill ~= '' and skill or 'Weltwissen')
end
local function observeBook(object)
    local ok, record = pcall(types.Book.record, object)
    if not ok or not record or not validId(record.id) then return false end
    local entry = books[record.id]
    if not entry then
        if countBooks() >= MAX_BOOKS then feedback('Das Wissensjournal ist voll; vorhandene Notizen bleiben erhalten.'); return false end
        local own = ownEntry(record.name)
        local skill = own and own.skill or (type(record.skill) == 'string' and record.skill or '')
        entry = {title=C.head(record.name or record.id,512),skill=skill,isScroll=record.isScroll == true,
            seconds=0,studied=false,spent=false}
        books[record.id] = entry
        feedback('Entdeckt: '..entry.title..'. Im Wissensjournal kannst du die Notiz studieren.')
    end
    selectedId, activeId, activeObject = record.id, record.id, object
    return true
end
local function percent(entry)
    return 5 + math.min(5, math.floor(entry.seconds / 24))
end
local function nextCredit()
    -- A stable record-id order makes the next application reproducible.
    local ids = {}
    for id, entry in pairs(books) do
        if entry.skill == 'alchemy' and entry.studied and not entry.spent then ids[#ids+1] = id end
    end
    table.sort(ids)
    local id = ids[1]
    return id, id and percent(books[id]) or 0
end
local function study(id)
    id = id or selectedId
    local entry = id and books[id]
    if not entry then feedback('Oeffne zuerst ein originales Buch oder eine Schriftrolle.'); return false end
    if entry.studied then feedback('Diese Notiz wurde bereits studiert. Erneutes Lesen verdoppelt ihre Wirkung nicht.'); return false end
    entry.studied = true
    feedback(entry.skill == 'alchemy'
        and ('Notiz vermerkt: einmalig +'..percent(entry)..'% Praxis beim naechsten gebrauten Trank. Kein Warten erforderlich.')
        or 'Notiz vermerkt. Dein Wissen bleibt mit diesem Spielstand erhalten; keine zusaetzliche Skillbuch-Stufe.')
    if refresh then refresh() end
    return true
end
local function skillUsed(skill, options)
    if skill ~= 'alchemy' or type(options) ~= 'table'
        or options.useType ~= I.SkillProgression.SKILL_USE_TYPES.Alchemy_CreatePotion
        or not finite(options.skillGain) or options.skillGain <= 0 then return end
    -- Match vanilla's no-progression conditions before consuming the note.
    if types.NPC.isWerewolf(self) or types.NPC.stats.skills.alchemy(self).base >= 100 then return end
    practiceEvents = math.min(1000000000, practiceEvents + 1)
    local id, bonus = nextCredit()
    if not id then
        lastPractice = {base=options.skillGain,final=options.skillGain,percent=0}
        return
    end
    local before = options.skillGain
    local after = before * (1 + bonus / 100)
    if not finite(after) then return end
    options.skillGain = after
    books[id].spent = true
    lastPractice = {bookId=id,base=before,final=after,percent=bonus}
    feedback(string.format('Wissen angewandt: %s, +%d%% Alchemie-Praxis. Zutaten und Trank bleiben im Originalsystem.',books[id].title,bonus))
    print('HALVETH_KNOWLEDGE_PRACTICE '..C.json(lastPractice))
    -- Never return false: preserve the engine's normal skill progression.
end

local function exportState()
    local entries = {}
    for id, entry in pairs(books) do
        entries[id] = {title=entry.title,skill=entry.skill,isScroll=entry.isScroll,seconds=entry.seconds,
            studied=entry.studied,spent=entry.spent}
    end
    return {version=1,books=entries,practiceEvents=practiceEvents,selectedId=selectedId,
        plannedPair=plannedPair and {plannedPair[1],plannedPair[2]} or nil}
end
local function decodeState(data)
    if type(data) ~= 'table' or data.version ~= 1 or type(data.books) ~= 'table'
        or not finite(data.practiceEvents) or data.practiceEvents < 0 or data.practiceEvents > 1000000000
        or data.practiceEvents % 1 ~= 0 then return nil end
    local candidate, count = {}, 0
    for id, entry in pairs(data.books) do
        count = count + 1
        if count > MAX_BOOKS or not validId(id) or type(entry) ~= 'table'
            or type(entry.title) ~= 'string' or #entry.title > 512
            or type(entry.skill) ~= 'string' or #entry.skill > 64
            or type(entry.isScroll) ~= 'boolean' or type(entry.studied) ~= 'boolean'
            or type(entry.spent) ~= 'boolean' or (entry.spent and not entry.studied)
            or not finite(entry.seconds) or entry.seconds < 0 or entry.seconds > MAX_SECONDS then return nil end
        candidate[id] = {title=entry.title,skill=entry.skill,isScroll=entry.isScroll,seconds=entry.seconds,
            studied=entry.studied,spent=entry.spent}
    end
    if data.selectedId ~= nil and not candidate[data.selectedId] then return nil end
    local plan=data.plannedPair
    if plan ~= nil and (type(plan) ~= 'table' or not validId(plan[1]) or not validId(plan[2])
        or plan[1] >= plan[2] or plan[3] ~= nil) then return nil end
    return candidate,plan
end
local function snapshot()
    local result = exportState()
    local id, bonus = nextCredit()
    result.bookCount = countBooks()
    result.nextBookId, result.nextPracticePercent = id, bonus
    result.activeBookId, result.panelOpen = activeId, window ~= nil
    result.recipeIndex=recipeIndex
    if lastPractice then
        result.lastPractice = {}
        for key, value in pairs(lastPractice) do result.lastPractice[key] = value end
    end
    return result
end
local function ingredientRecipes()
    local items, seen, recipes = {}, {}, {}
    local inventory = types.Actor.inventory(self)
    local all = inventory:getAll(types.Ingredient)
    local level=types.NPC.stats.skills.alchemy(self).modified
    local step=core.getGMST('fWortChanceValue')
    assert(finite(level) and finite(step) and step>0,'Alchemy knowledge threshold unavailable')
    for _, object in ipairs(all) do
        if not seen[object.recordId] and #items < 256 then
            seen[object.recordId] = true
            local record = types.Ingredient.record(object)
            local effects = {}
            for _, effect in ipairs(record.effects) do
                -- The engine's ingredient tooltip reveals effect index 0 at
                -- fWortChanceValue, then one further effect per threshold.
                if level >= (effect.index+1)*step then
                    local key = tostring(effect.id)..':'..tostring(effect.affectedSkill or '')..':'..tostring(effect.affectedAttribute or '')
                    effects[key] = (effect.effect and effect.effect.name) or tostring(effect.id)
                end
            end
            items[#items+1] = {id=record.id,name=record.name,count=inventory:countOf(record.id),effects=effects}
        end
    end
    table.sort(items,function(a,b) if a.name == b.name then return a.id < b.id end; return a.name < b.name end)
    for a=1,#items do
        for b=a+1,#items do
            local shared = {}
            for key, name in pairs(items[a].effects) do if items[b].effects[key] then shared[#shared+1] = name end end
            table.sort(shared)
            if #shared > 0 then
                recipes[#recipes+1]={first=items[a],second=items[b],effects=shared}
            end
        end
    end
    return items,recipes,level,step
end
local function currentRecipe(recipes)
    if #recipes == 0 then recipeIndex=1;return nil end
    if restoreRecipeSelection and plannedPair then
        for index,recipe in ipairs(recipes) do
            if (recipe.first.id==plannedPair[1] and recipe.second.id==plannedPair[2])
                or (recipe.first.id==plannedPair[2] and recipe.second.id==plannedPair[1]) then
                recipeIndex=index;restoreRecipeSelection=false;break
            end
        end
    end
    recipeIndex=(recipeIndex-1)%#recipes+1
    return recipes[recipeIndex]
end
local function ingredientHelp()
    local items,recipes,level,step=ingredientRecipes()
    local lines={'ALCHEMIE MIT DEINEN ECHTEN ZUTATEN',
        string.format('%d Zutatenarten im Inventar (maximal 256 ausgewertet). Alchemie: %.0f. Sichtbare Effekte ab %.0f, %.0f, %.0f, %.0f.',
            #items,level,step,2*step,3*step,4*step),
        tostring(#recipes)..' Paare mit einem dir bereits bekannten gemeinsamen Effekt.'}
    local pair=currentRecipe(recipes)
    if pair then
        lines[#lines+1]=string.format('REZEPT %d / %d\n%s x%d + %s x%d',recipeIndex,#recipes,
            pair.first.name,pair.first.count,pair.second.name,pair.second.count)
        lines[#lines+1]='Bekannter gemeinsamer Effekt: '..table.concat(pair.effects,', ')
    else
        lines[#lines+1]='Noch kein fuer dich erkennbares Zutatenpaar. Lies weiter, uebe Alchemie oder sammle Zutaten; unbekannte Originaleffekte bleiben verborgen.'
    end
    if plannedPair then
        local first,second=plannedPair[1],plannedPair[2]
        local remembered
        for _,recipe in ipairs(recipes) do
            if (recipe.first.id==first and recipe.second.id==second)
                or (recipe.first.id==second and recipe.second.id==first) then
                remembered=recipe.first.name..' + '..recipe.second.name;break
            end
        end
        lines[#lines+1]='Dein gespeicherter Plan: '..(remembered or 'Ein frueher gemerktes Paar; Voraussetzungen derzeit nicht sichtbar oder Zutaten fehlen.')
    end
    local mortar=false
    for _,object in ipairs(types.Actor.inventory(self):getAll(types.Apparatus)) do
        if types.Apparatus.record(object).type==types.Apparatus.TYPE.MortarPestle then mortar=true;break end
    end
    lines[#lines+1]=mortar and 'Moerser vorhanden: [Brauen] oeffnet das normale Alchemiefenster.'
        or 'Fuer das originale Alchemiefenster brauchst du einen Moerser und Stoessel.'
    lines[#lines+1]='Ein gemerkter Plan ist eine Notiz. Zutatenverbrauch, Erfolg und Trank folgen ausschliesslich dem normalen Morrowind-System.'
    return table.concat(lines,'\n\n'),#items,#recipes,recipes
end
local function browseRecipe(delta)
    local _,recipes=ingredientRecipes()
    if #recipes==0 then feedback('Noch kein dir bekanntes gemeinsames Zutatenpaar.');return false end
    restoreRecipeSelection=false
    recipeIndex=(recipeIndex-1+delta)%#recipes+1
    refresh()
    return true
end
local function rememberRecipe()
    local _,recipes=ingredientRecipes()
    local recipe=currentRecipe(recipes)
    if not recipe then feedback('Zuerst ein erkennbares Zutatenpaar finden.');return false end
    local first,second=recipe.first.id,recipe.second.id
    if second<first then first,second=second,first end
    plannedPair={first,second}
    restoreRecipeSelection=false
    feedback('Rezept im Morrowind-Spielstand gemerkt: '..recipe.first.name..' + '..recipe.second.name..'.')
    refresh()
    return true
end
local function openAlchemy()
    local _,recipes=ingredientRecipes()
    local recipe=currentRecipe(recipes)
    if not recipe then feedback('Waehle zuerst ein bekanntes Zutatenpaar.');return false end
    local mortar=false
    for _,object in ipairs(types.Actor.inventory(self):getAll(types.Apparatus)) do
        if types.Apparatus.record(object).type==types.Apparatus.TYPE.MortarPestle then mortar=true;break end
    end
    if not mortar then feedback('Du brauchst einen Moerser und Stoessel fuer die normale Alchemie.');return false end
    close()
    local ok=pcall(I.UI.addMode,'Alchemy')
    if not ok then open();feedback('Das normale Alchemiefenster konnte hier nicht geoeffnet werden. Benutze den Moerser im Inventar.')
        return false end
    return true
end
local function journalText()
    local ids = sortedIds()
    if not selectedId or not books[selectedId] then selectedId = ids[1] end
    local lines = {'DEIN WISSENSJOURNAL',tostring(#ids)..' entdeckte Texte in diesem Morrowind-Spielstand.'}
    local entry = selectedId and books[selectedId]
    if not entry then
        lines[#lines+1] = 'Oeffne ein Buch oder eine Schriftrolle in der Welt oder im Inventar. Originaltexte bleiben in ihrem originalen Lesefenster.'
    else
        local position = 1
        for index,id in ipairs(ids) do if id == selectedId then position=index;break end end
        lines[#lines+1] = string.format('%d / %d  |  %s\n%s',position,#ids,entry.isScroll and 'Schriftrolle' or 'Buch',entry.title)
        lines[#lines+1] = 'Gebiet: '..subjectName(entry.skill)
        lines[#lines+1] = string.format('Anzeigezeit im Buchmodus: %.1f s (max. 120 s)',entry.seconds)
        lines[#lines+1] = entry.spent and 'Praxisnotiz bereits angewandt.' or entry.studied and 'Notiz studiert und gespeichert.' or 'Notiz noch nicht studiert: S oder [Studieren].'
        if entry.skill == 'alchemy' and not entry.spent then
            lines[#lines+1] = string.format('Nach dem Studieren: einmalig +%d%% beim naechsten echten Alchemie-Praxisereignis.',percent(entry))
        end
        local own = ownEntry(entry.title)
        if own and own.pages and #own.pages > 0 then
            local index = page % #own.pages + 1
            lines[#lines+1] = string.format('Eigene Lernfrage %d / %d: %s',index,#own.pages,own.pages[index].prompt)
            for n,answer in ipairs(own.pages[index].answers) do lines[#lines+1] = '['..n..'] '..answer end
        end
    end
    lines[#lines+1] = 'Studieren ist sofort moeglich. Die Anzeigezeit kann den einmaligen Praxisbonus von 5 auf 10% erhoehen; sie beweist kein Verstaendnis. Warten allein gibt in diesem Journal keine XP.'
    return table.concat(lines,'\n\n')
end
refresh = function()
    if not window then return end
    leftText.props.text = journalText()
    local ok,text = pcall(ingredientHelp)
    rightText.props.text = ok and text or 'Zutaten werden verfuegbar, sobald dein Inventar geladen ist.'
    local id,bonus = nextCredit()
    rightText.props.text = rightText.props.text..'\n\n'..(id and ('Naechste Praxis: +'..bonus..'% aus '..books[id].title) or 'Keine offene Alchemie-Praxisnotiz. Lies und studiere einen Alchemietext.')
    footerText.props.text = message
    window:update()
end
close = function()
    if window then window:destroy();window=nil end
    leftText,rightText,footerText=nil,nil,nil
    if addedMode then I.UI.removeMode('Interface');addedMode=false end
    panelMode=nil
end
local function selectRelative(delta)
    local ids=sortedIds()
    if #ids == 0 then return end
    local index=1
    for n,id in ipairs(ids) do if id == selectedId then index=n;break end end
    selectedId=ids[(index-1+delta)%#ids+1];page=0;refresh()
end
local function readSelected()
    if not selectedId then feedback('Noch kein Text ausgewaehlt.');return false end
    local object=types.Actor.inventory(self):find(selectedId)
    if not object and activeObject and activeObject:isValid() and activeObject.recordId == selectedId then object=activeObject end
    if not object then feedback('Dieses Buch liegt nicht in deinem Inventar. Suche das Original wieder auf.');return false end
    local mode=books[selectedId].isScroll and 'Scroll' or 'Book'
    close()
    I.UI.addMode(mode,{target=object})
    return true
end
local function contentRequest(request)
    requestSerial=requestSerial+1
    local id='knowledge-'..tostring(requestSerial)..'-'..tostring(math.floor(core.getRealTime()*1000))
    pendingContent[id]=true
    core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request=request,requestId=id})
    feedback(request == 'library' and 'Eigene Buecher werden deinem echten Inventar hinzugefuegt ...' or 'LOVE / SPARK / AEGIS werden in deinem normalen Zauberbuch gelernt ...')
end
local function answer(choice)
    local entry=selectedId and books[selectedId]
    local own=entry and ownEntry(entry.title)
    if not own or not own.pages or #own.pages == 0 then feedback('Fuer diesen Originaltext gibt es keine HALVETH-Prueffrage. S merkt deine Notiz direkt.');return false end
    local question=own.pages[page%#own.pages+1]
    if question.correct ~= choice then feedback('Schlage die Stelle im Originalbuch noch einmal nach; es geht kein Fortschritt verloren.');return false end
    study(selectedId)
    feedback('Die Antwort passt zu dieser eigenen Buchstelle. Deine Notiz ist vermerkt; wiederholte Antworten geben keine XP.')
    return true
end
local function button(label,x,y,w,fn)
    return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(x,y),size=util.vector2(w,30),text=label,textSize=16},
        events={mouseClick=async:callback(fn)}}
end
open = function()
    if window then close();return end
    if I.HALVETH and I.HALVETH.close then I.HALVETH.close() end
    if I.HALVETHUniverse then I.HALVETHUniverse.close() end
    if I.HALVETHPaths then I.HALVETHPaths.close() end
    -- Reuse a native menu's cursor/pause instead of stacking a duplicate
    -- Interface mode: OpenMW removes every matching mode on removeMode.
    panelMode=I.UI.getMode() or 'Interface'
    if not I.UI.getMode() then I.UI.addMode('Interface',{windows={}});addedMode=true end
    local screen=ui.screenSize()
    local w,h=math.min(1120,screen.x-24),math.min(720,screen.y-24)
    local col=(w-54)/2
    local bodyHeight=h-217
    leftText={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(18,75),size=util.vector2(col,bodyHeight),text='',textSize=17,readOnly=true,multiline=true,wordWrap=true}}
    rightText={type=ui.TYPE.TextEdit,template=I.MWUI.templates.textEditBox,
        props={position=util.vector2(36+col,75),size=util.vector2(col,bodyHeight),text='',textSize=17,readOnly=true,multiline=true,wordWrap=true}}
    footerText={type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
        props={position=util.vector2(18,h-83),size=util.vector2(w-36,44),text=message,textSize=15,wordWrap=true}}
    local items={
        {type=ui.TYPE.Text,template=I.MWUI.templates.textHeader,props={position=util.vector2(18,14),text='HALVETH / MORROWIND / WISSEN',textSize=23}},
        {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,props={position=util.vector2(18,46),text='Deine Bibliothek · Alchemie · Magie',textSize=16}},
        button('[Figur / Inventar / F6]',w-280,16,255,function()close();if I.HALVETHUniverse then I.HALVETHUniverse.open() end end),
        button('[< Rezept]',36+col,43,math.floor((col-18)/4),function()browseRecipe(-1)end),
        button('[Rezept >]',42+col+math.floor((col-18)/4),43,math.floor((col-18)/4),function()browseRecipe(1)end),
        button('[Merken]',48+col+2*math.floor((col-18)/4),43,math.floor((col-18)/4),rememberRecipe),
        button('[Brauen]',54+col+3*math.floor((col-18)/4),43,math.floor((col-18)/4),openAlchemy),
        leftText,rightText,footerText,
        button('[< Text]',18,h-128,85,function()selectRelative(-1)end),
        button('[Text >]',108,h-128,85,function()selectRelative(1)end),
        button('[Studieren / S]',198,h-128,156,function()study()end),
        button('[Original lesen / R]',360,h-128,200,readSelected),
        button('[1]',580,h-128,48,function()answer(1)end),
        button('[2]',634,h-128,48,function()answer(2)end),
        button('[3]',688,h-128,48,function()answer(3)end),
        button('[Buecher / B]',18,h-34,175,function()contentRequest('library')end),
        button('[LOVE / SPARK / AEGIS / M]',202,h-34,300,function()contentRequest('spells')end),
        button('[Aktualisieren]',w-315,h-34,160,refresh),
        button('[Schliessen / F7]',w-150,h-34,146,close),
    }
    items[#items+1]=button('[Frage > / Tab]',w-225,h-128,200,function()page=page+1;refresh()end)
    window=ui.create{type=ui.TYPE.Container,template=I.MWUI.templates.boxSolid,layer='Windows',
        props={relativePosition=util.vector2(.5,.5),anchor=util.vector2(.5,.5),size=util.vector2(w,h)},content=ui.content(items)}
    refresh()
end
local function modeChanged(data)
    activeId=nil
    if data.newMode == 'Book' or data.newMode == 'Scroll' then
        if data.arg then observeBook(data.arg)
        elseif activeObject and activeObject:isValid() then observeBook(activeObject) end
    end
end
local function onFrame(dt)
    -- The normal reader pauses simulation, so use bounded real frame time.
    local now=core.getRealTime()
    local displayDelta=lastFrameTime and now-lastFrameTime or 0
    lastFrameTime=now
    if activeId and not window and (I.UI.getMode() == 'Book' or I.UI.getMode() == 'Scroll')
        and finite(displayDelta) and displayDelta > 0 and displayDelta <= 0.5 then
        local entry=books[activeId]
        if entry then entry.seconds=math.min(MAX_SECONDS,entry.seconds+displayDelta) end
    end
    if window and I.UI.getMode() ~= panelMode then close() end
    if window and now-lastRefresh>1 then lastRefresh=now;refresh() end
end
local function onLoad(data)
    close();activeId=nil;activeObject=nil;pendingContent={};lastPractice=nil;lastFrameTime=nil
    books={};selectedId=nil;practiceEvents=0;plannedPair=nil;recipeIndex=1;restoreRecipeSelection=false;retainedInvalidSave=nil
    if data == nil then return end
    local candidate,plan=decodeState(data)
    if not candidate then
        retainedInvalidSave=data
        feedback('Dieser Wissensstand ist inkompatibel. Seine Originaldaten bleiben im Save erhalten.')
        return
    end
    books=candidate;selectedId=data.selectedId;practiceEvents=data.practiceEvents;plannedPair=plan
    restoreRecipeSelection=plan~=nil
end

if I.SkillProgression and I.SkillProgression.addSkillUsedHandler then
    I.SkillProgression.addSkillUsedHandler(skillUsed)
end

return {
    interfaceName='HALVETHKnowledge',
    interface={version=2,open=open,close=close,isOpen=function()return window~=nil end,getState=snapshot,study=study,answer=answer,
        selectBook=function(id) if books[id] then selectedId=id;page=0;refresh();return true end;return false end,
        readSelected=readSelected,requestContent=contentRequest,
        ingredientHelp=ingredientHelp,browseRecipe=browseRecipe,rememberRecipe=rememberRecipe,openAlchemy=openAlchemy,
        -- Read-only save-contract check; never changes player stats or writes a save.
        checkSaveRoundTrip=function()
            local data=exportState();local candidate,plan=decodeState(data)
            return candidate ~= nil and C.json(candidate) == C.json(data.books)
                and C.json(plan)==C.json(data.plannedPair)
        end},
    engineHandlers={onFrame=onFrame,onLoad=onLoad,
        onSave=function() return retainedInvalidSave or exportState() end,
        onKeyPress=function(key)
            if key.code == input.KEY.F7 then open();return end
            if not window then return end
            if key.code == input.KEY.Escape then close()
            elseif key.code == input.KEY.PageDown then selectRelative(1)
            elseif key.code == input.KEY.PageUp then selectRelative(-1)
            elseif key.code == input.KEY.S then study()
            elseif key.code == input.KEY.R then readSelected()
            elseif key.code == input.KEY.B then contentRequest('library')
            elseif key.code == input.KEY.M then contentRequest('spells')
            elseif key.code == input.KEY.Tab then page=page+1;refresh()
            elseif key.code == input.KEY._1 then answer(1)
            elseif key.code == input.KEY._2 then answer(2)
            elseif key.code == input.KEY._3 then answer(3) end
        end},
    eventHandlers={UiModeChanged=modeChanged,
        HALVETH_ContentResult=function(data)
            if type(data) ~= 'table' or not pendingContent[data.requestId] then return end
            pendingContent[data.requestId]=nil
            feedback(tostring(data.message or 'Inhalte verarbeitet.'))
            refresh()
        end,
        HALVETH_KnowledgeTestRequest=function(data)
            -- Local observer interface uses the same deliberate UI operations.
            if type(data) ~= 'table' then return end
            if data.operation == 'open' then if not window then open() end
            elseif data.operation == 'close' then close()
            elseif data.operation == 'study' then study(data.recordId) end
            self:sendEvent('HALVETH_KnowledgeTestResult',{requestId=data.requestId,state=snapshot(),saveRoundTrip=decodeState(exportState()) ~= nil})
        end},
}
