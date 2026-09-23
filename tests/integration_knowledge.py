"""Exercise native reading, alchemy knowledge and real save/reload in a disposable profile.

Uses only test-owned OpenMW processes and a fresh Vivec scene. It writes one
test save under .local/knowledge-integration; existing saves are never loaded.
This exercises the installed Lua interfaces, not physical keyboard input.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare


PLAYER_TEST = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')
local stage,entered,started,finished='start',nil,nil,false
local bookId,scrollId,before,displayBefore,progressBefore,expected,baselineModes
local function transition(nextStage)
    stage=nextStage;entered=core.getRealTime()
end
local function finish(ok,message)
    if finished then return end
    finished=true
    print('HALVETH_KNOWLEDGE_'..(ok and 'PASS' or 'FAIL')..' '..message)
    core.quit()
end
local function state() return I.HALVETHKnowledge.getState() end
local function alchemy() return types.NPC.stats.skills.alchemy(self) end
local function eq(a,b,message) assert(math.abs(a-b)<0.00001,message..' '..a..' / '..b) end
local function modes()
    local result={}
    for _,mode in ipairs(I.UI.modes) do result[#result+1]=mode end
    return table.concat(result,',')
end
local function read(id,mode)
    local object=types.Actor.inventory(self):find(id)
    assert(object,'Native inventory book missing')
    I.UI.addMode(mode,{target=object})
end
local function tick()
    if finished or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>65 then error('Timeout at '..stage) end
    local elapsed=now-entered
    if stage=='start' and elapsed>1 then
        assert(I.HALVETHKnowledge,'Knowledge interface missing')
        assert(state().bookCount==0,'Unexpected pre-existing knowledge')
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='both',requestId='knowledge-content'})
        core.sendGlobalEvent('HALVETH_KnowledgeTestIngredients',{player=self.object})
        transition('content')
    elseif stage=='reader' and elapsed>1.3 then
        local s=state()
        assert(I.UI.getMode()=='Book' and s.activeBookId==bookId,'Native book reader/discovery failed')
        assert(s.bookCount==1 and s.books[bookId].seconds>0.5,'Reading display time missing')
        eq(alchemy().base,before.base,'Idle reading changed skill level')
        eq(alchemy().progress,before.progress,'Idle reading changed skill progress')
        assert(not s.books[bookId].studied and not s.books[bookId].spent,'Idle reading awarded study')
        baselineModes=modes()
        I.HALVETHKnowledge.open()
        displayBefore=state().books[bookId].seconds
        transition('panel')
    elseif stage=='panel' and elapsed>0.8 then
        assert(state().panelOpen,'Native knowledge panel missing')
        eq(state().books[bookId].seconds,displayBefore,'Covered reader accrued time')
        assert(modes()==baselineModes,'Knowledge opening changed existing native menu stack')
        local help,count,pairs=I.HALVETHKnowledge.ingredientHelp()
        assert(count>=2 and pairs>=1 and help:find('Wickwheat',1,true),'Actual inventory ingredient guide failed')
        assert(I.HALVETHKnowledge.study(bookId),'Study failed')
        assert(not I.HALVETHKnowledge.study(bookId),'Repeated study granted another credit')
        assert(state().nextPracticePercent==5,'Unexpected initial bonus')
        eq(alchemy().progress,before.progress,'Studying alone gave XP')
        I.HALVETHKnowledge.close()
        transition('resume-reader')
    elseif stage=='resume-reader' and elapsed>0.7 then
        assert(state().books[bookId].seconds>displayBefore,'Display timer did not resume after native panel')
        assert(modes()==baselineModes,'Knowledge close changed inventory/reader stack')
        I.HALVETH.open()
        transition('companion')
    elseif stage=='companion' and elapsed>0.3 then
        assert(modes()==baselineModes,'Companion opening changed native reader stack')
        I.HALVETH.close()
        I.UI.removeMode('Book')
        transition('reader-close')
    elseif stage=='reader-close' and elapsed>0.2 then
        assert(I.UI.getMode()=='Interface','Inventory mode was lost after reading')
        I.UI.removeMode('Interface')
        I.SkillProgression.skillUsed('alchemy',{useType=1,skillGain=0.05})
        transition('other-practice')
    elseif stage=='other-practice' and elapsed>0.2 then
        assert(not state().books[bookId].spent,'Eating ingredient consumed potion credit')
        before={base=alchemy().base,progress=alchemy().progress}
        progressBefore=I.SkillProgression.getSkillProgressRequirement('alchemy')
        I.SkillProgression.skillUsed('alchemy',{useType=0,skillGain=1})
        transition('first-practice')
    elseif stage=='first-practice' and elapsed>0.2 then
        local s=state()
        assert(s.books[bookId].spent and s.lastPractice.bookId==bookId,'Potion practice did not consume correct note')
        eq(s.lastPractice.final,1.05,'Practice modifier missing')
        eq(alchemy().progress-before.progress,1.05/progressBefore,'Vanilla alchemy did not receive modified gain')
        before={base=alchemy().base,progress=alchemy().progress}
        progressBefore=I.SkillProgression.getSkillProgressRequirement('alchemy')
        I.SkillProgression.skillUsed('alchemy',{useType=0,skillGain=1})
        transition('repeat-practice')
    elseif stage=='repeat-practice' and elapsed>0.2 then
        assert(state().lastPractice.percent==0,'Repeated potion received duplicate bonus')
        eq(alchemy().progress-before.progress,1/progressBefore,'Ordinary repeated alchemy gain changed')
        I.UI.addMode('Interface')
        read(scrollId,'Scroll')
        transition('scroll')
    elseif stage=='scroll' and elapsed>0.7 then
        local s=state()
        assert(I.UI.getMode()=='Scroll' and s.bookCount==2 and s.books[scrollId].isScroll,'Native scroll discovery failed')
        assert(s.books[scrollId].seconds>0.2,'Scroll display time missing')
        assert(I.HALVETHKnowledge.study(scrollId),'Scroll study failed')
        I.UI.removeMode('Scroll');I.UI.removeMode('Interface')
        before={base=alchemy().base,progress=alchemy().progress}
        alchemy().base=100
        transition('cap-ready')
    elseif stage=='cap-ready' and elapsed>0.2 then
        assert(alchemy().base==100,'Isolated test skill cap not applied')
        I.SkillProgression.skillUsed('alchemy',{useType=0,skillGain=1})
        transition('cap-check')
    elseif stage=='cap-check' and elapsed>0.2 then
        assert(not state().books[scrollId].spent,'Capped skill consumed unused credit')
        alchemy().base=before.base
        transition('save-ready')
    elseif stage=='save-ready' and elapsed>0.3 then
        assert(I.HALVETHKnowledge.checkSaveRoundTrip(),'Save schema roundtrip failed')
        expected=state()
        expected.alchemyBase=alchemy().base;expected.alchemyProgress=alchemy().progress
        transition('saved')
        types.Player.sendMenuEvent(self,'HALVETH_KnowledgeSave',{slot='halveth-knowledge-isolated'})
    elseif stage=='reloaded' and elapsed>0.8 then
        local s=state()
        assert(expected and s.bookCount==2,'Knowledge lost during actual save/load')
        assert(s.books[bookId].spent and s.books[scrollId].studied and not s.books[scrollId].spent,'Credit flags lost during save/load')
        eq(s.books[bookId].seconds,expected.books[bookId].seconds,'Book display time changed during save/load')
        eq(s.books[scrollId].seconds,expected.books[scrollId].seconds,'Scroll time changed during save/load')
        eq(alchemy().base,expected.alchemyBase,'Skill base changed during save/load')
        eq(alchemy().progress,expected.alchemyProgress,'Skill progress changed during save/load')
        assert(types.Actor.inventory(self):countOf(bookId)==1,'Native book record/inventory lost during save/load')
        assert(types.Actor.inventory(self):countOf(scrollId)==1,'Native scroll lost during save/load')
        before={base=alchemy().base,progress=alchemy().progress}
        progressBefore=I.SkillProgression.getSkillProgressRequirement('alchemy')
        I.SkillProgression.skillUsed('alchemy',{useType=0,skillGain=1})
        transition('restored-credit')
    elseif stage=='restored-credit' and elapsed>0.2 then
        local s=state()
        assert(s.books[scrollId].spent and s.lastPractice.bookId==scrollId,'Restored pending credit did not work')
        eq(alchemy().progress-before.progress,1.05/progressBefore,'Restored credit did not reach normal progression')
        finish(true,'nativeBook=PASS nativeScroll=PASS displayTime=PASS noIdleXP=PASS studyNoXP=PASS inventoryEffects=PASS nativeMenuStack=PASS alchemyModifier=PASS noRepeatedBonus=PASS capPreservesCredit=PASS actualSaveReload=PASS savedPendingCredit=PASS')
    end
end
return {engineHandlers={
    onFrame=function() local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end end,
    onSave=function() return {phase=stage,bookId=bookId,scrollId=scrollId,expected=expected} end,
    onLoad=function(data)
        assert(data and data.phase=='saved','Test did not load its expected save')
        bookId=data.bookId;scrollId=data.scrollId;expected=data.expected
        finished=false;started=core.getRealTime();transition('reloaded')
        print('HALVETH_KNOWLEDGE_RELOADED '..tostring(bookId))
    end},eventHandlers={HALVETH_ContentResult=function(data)
        if data.requestId~='knowledge-content' then return end
        local ok,err=pcall(function()
            assert(data.success,data.message)
            for _,book in ipairs(data.books) do
                if book.key=='glassleaf-primer' then bookId=book.recordId end
                if book.key=='moonwater-scroll' then scrollId=book.recordId end
            end
            assert(bookId and scrollId,'Expected real books missing')
            before={base=alchemy().base,progress=alchemy().progress}
            I.UI.addMode('Interface')
            read(bookId,'Book');transition('reader')
        end)
        if not ok then finish(false,tostring(err)) end
    end}}
'''

MENU_TEST = r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_KnowledgeSave=function(data)
    assert(not pending and not loaded,'Duplicate test save request')
    assert(data.slot=='halveth-knowledge-isolated','Unexpected test slot')
    pending=data.slot
    menu.saveGame('HALVETH isolated knowledge integration',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    local saves=menu.getSaves(dir)
    for slot,info in pairs(saves) do
        if info.description=='HALVETH isolated knowledge integration' then
            print('HALVETH_KNOWLEDGE_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true
            menu.loadGame(dir,slot)
            return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_KNOWLEDGE_FAIL Test save slot did not materialize');menu.quit()
    end
end}}
'''

GLOBAL_TEST = r'''local world=require('openmw.world')
local types=require('openmw.types')
return {eventHandlers={HALVETH_KnowledgeTestIngredients=function(data)
    local inv=types.Actor.inventory(data.player)
    for _,id in ipairs({'ingred_marshmerrow_01','ingred_wickwheat_01'}) do
        assert(types.Ingredient.records[id],'Original ingredient missing: '..id)
        world.createObject(id,2):moveInto(inv)
    end
end}}
'''


def run(install_root: Path, state_dir: Path) -> dict:
    args = argparse.Namespace(install_root=install_root, state_dir=state_dir,
                              source_profile='max', profile='original', smoke=True,
                              copy_saves=False, reset_settings=True)
    receipt = prepare(args)
    profile = Path(receipt['profile_dir'])
    data = profile / 'data'
    for name, text in (
        ('scripts/halveth_genesis_smoke.lua', PLAYER_TEST),
        ('scripts/halveth_knowledge_test_menu.lua', MENU_TEST),
        ('scripts/halveth_knowledge_test_global.lua', GLOBAL_TEST),
        ('bridge/inbox.json', '{}\n'),
        ('bridge/companion-status.json', '{"status":"offline"}\n'),
    ):
        atomic_text(data / name, text)
    manifest = (ROOT / 'mod/halveth.omwscripts').read_text(encoding='utf-8')
    manifest += '\nMENU: scripts/halveth_knowledge_test_menu.lua\nGLOBAL: scripts/halveth_knowledge_test_global.lua\n'
    atomic_text(data / 'halveth.omwscripts', manifest)
    log_path = Path(receipt['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(), 'passed': False,
        'scope': 'Actual OpenMW interfaces: real Book and Scroll readers, display timer, no idle/study XP, inventory effect pairs, original alchemy progression handler, single-use bonus and skill cap, native menu stack, actual isolated save file and reload. No existing save loaded; no physical-input or screenshot assertion.',
        'profileDir': str(profile), 'log': str(log_path),
        'sourceConfigSHA256': receipt['source_config_sha256'],
        'sourceSettingsSHA256': receipt['source_settings_sha256'],
        'testedFiles': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            'mod/scripts/halveth/knowledge.lua', 'mod/scripts/halveth/player.lua',
            'mod/scripts/halveth/content.lua', 'mod/halveth.omwscripts')},
    }
    process = None
    try:
        with log_path.open('w', encoding='utf-8') as output:
            process = subprocess.Popen(receipt['command'], cwd=receipt['cwd'], stdout=output,
                                       stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            result['pid'] = process.pid
            result['exitCode'] = process.wait(timeout=100)
        text = log_path.read_text(encoding='utf-8', errors='replace')
        result['markers'] = [line for line in text.splitlines() if 'HALVETH_KNOWLEDGE_' in line]
        result['errors'] = [line for line in text.splitlines() if ' E]' in line or 'Lua error' in line]
        result['testSaveFiles'] = [str(p.relative_to(profile)) for p in profile.rglob('*.omwsave')]
        result['passed'] = (result['exitCode'] == 0 and any('HALVETH_KNOWLEDGE_PASS' in line for line in result['markers'])
                            and any('HALVETH_KNOWLEDGE_RELOADED' in line for line in result['markers'])
                            and len(result['testSaveFiles']) == 1 and not result['errors'])
        source = install_root / 'profiles/max'
        result['originalSettingsPreserved'] = all(hashlib.sha256((source / name).read_bytes()).hexdigest() == result[key]
            for name, key in (('openmw.cfg', 'sourceConfigSHA256'), ('settings.cfg', 'sourceSettingsSHA256')))
        result['passed'] = result['passed'] and result['originalSettingsPreserved']
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        atomic_text(state_dir / 'result.json', json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root', type=Path, default=default_install())
    parser.add_argument('--state-dir', type=Path)
    args = parser.parse_args()
    state = args.state_dir or ROOT / '.local/knowledge-integration' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    result = run(args.install_root.resolve(), state.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
