"""Exercise the optional Heart Letter inside an isolated native Morrowind game."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare

PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local I=require('openmw.interfaces')
local stage,entered,started,done='start',nil,nil,false
local bookId,loveId
local function move(next) stage=next;entered=core.getRealTime() end
local function finish(ok,detail)
    if done then return end
    done=true;print('HALVETH_HEART_'..(ok and 'PASS' or 'FAIL')..' '..detail);core.quit()
end
local function arrille()
    for _,actor in ipairs(nearby.actors) do
        if actor:isValid() and actor.recordId=='arrille' then return actor end
    end
end
local function tick()
    if done or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>80 then error('Timeout at '..stage) end
    if stage=='start' and now-entered>1 then
        assert(I.HALVETHHeart and I.HALVETHHeart.getState().phase=='sealed','Heart Letter unavailable')
        assert(not I.HALVETHHeart.begin('invalid'),'Invalid response accepted')
        assert(I.HALVETHHeart.open() and I.HALVETHHeart.isOpen(),'Native Heart Letter panel failed')
        I.HALVETHHeart.close()
        assert(I.HALVETHHeart.begin('come'),'Letter response rejected')
        assert(not I.HALVETHHeart.begin('question'),'Response changed after choice')
        assert(not I.HALVETHHeart.advance(),'Advanced without world actions')
        core.sendGlobalEvent('HALVETH_ContentRequest',{
            player=self.object,request='library',requestId='heart-book'})
        move('content')
    elseif stage=='read' and now-entered>.2 then
        local book=types.Actor.inventory(self):find(bookId)
        assert(book and types.Book.record(book),'Original engine book absent')
        I.UI.addMode('Interface',{windows={'Inventory'}})
        I.UI.addMode('Book',{target=book})
        move('reader')
    elseif stage=='reader' and now-entered>.5 then
        assert(I.UI.getMode()=='Book','Normal Morrowind book reader did not open')
        assert(I.HALVETHKnowledge.getState().bookCount>=1,'Book reading was not observed')
        I.UI.removeMode('Book');I.UI.removeMode('Interface')
        assert(not I.HALVETHHeart.advance(),'Advanced without an NPC conversation')
        local npc=arrille()
        assert(npc,'Real Arrille reference absent')
        assert(I.HALVETHWorldlife.observe(npc,true),'Real NPC encounter was not recorded')
        assert(I.HALVETHHeart.advance(),'Real reading and NPC encounter did not unlock the letter')
        assert(I.HALVETHHeart.getState().phase=='ready','Letter stage mismatch')
        assert(I.HALVETHHeart.claim(),'LOVE reward request failed')
        assert(not I.HALVETHHeart.claim(),'Duplicate LOVE request accepted')
        move('reward')
    elseif stage=='reward' and now-entered>2 then
        assert(I.HALVETHHeart.getState().phase=='completed','Letter did not complete')
        assert(loveId and types.Actor.spells(self)[loveId],'LOVE missing from native spellbook')
        local count=0
        for _,record in pairs(types.Actor.spells(self)) do
            if record.name=='HALVETH SPARK - Sternenfunke' or record.name=='HALVETH AEGIS - Lichtwacht' then
                error('Heart reward granted unrelated spells')
            end
            if record.name=='HALVETH LOVE - Heilschein' then count=count+1 end
        end
        assert(count==1,'LOVE granted more than once')
        move('saved')
        types.Player.sendMenuEvent(self,'HALVETH_HeartSave',{slot='heart-isolated'})
    elseif stage=='reloaded' and now-entered>1 then
        assert(I.HALVETHHeart.getState().phase=='completed','Heart Letter progress lost after save/load')
        assert(types.Actor.spells(self)[loveId],'Native LOVE spell lost after save/load')
        assert(not I.HALVETHHeart.claim(),'Completed letter rewarded again')
        finish(true,'nativeLetter=PASS realBook=PASS realNPC=PASS onlyLOVE=PASS saveReload=PASS')
    end
end
return {engineHandlers={
    onFrame=function()local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end end,
    onSave=function()return {stage=stage,loveId=loveId}end,
    onLoad=function(data)
        assert(data and data.stage=='saved','Unexpected test save payload')
        loveId=data.loveId;done=false;started=core.getRealTime();move('reloaded')
        print('HALVETH_HEART_RELOADED')
    end},eventHandlers={HALVETH_ContentResult=function(data)
        if data.requestId=='heart-book' then
            assert(data.success,data.message)
            for _,book in ipairs(data.books) do
                if book.key=='glassleaf-primer' then bookId=book.recordId end
            end
            assert(bookId,'Own book mapping absent');move('read')
        elseif data.request=='love' and data.success then
            for _,spell in ipairs(data.spells) do
                if spell.key=='love' then loveId=spell.recordId end
            end
        end
    end}}
'''

MENU = r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_HeartSave=function(data)
    assert(not pending and not loaded and data.slot=='heart-isolated','Unexpected save request')
    pending=data.slot;menu.saveGame('HALVETH isolated Heart Letter',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated Heart Letter' then
            print('HALVETH_HEART_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true;menu.loadGame(dir,slot);return
        end
    end
    if core.getRealTime()-started>10 then print('HALVETH_HEART_FAIL save missing');menu.quit() end
end}}
'''


def run(install_root: Path, state_dir: Path) -> dict:
    prepared = prepare(argparse.Namespace(
        install_root=install_root, state_dir=state_dir, source_profile='max',
        profile='original', smoke=True, copy_saves=False, reset_settings=True))
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    atomic_text(data / 'scripts/halveth_genesis_smoke.lua', PLAYER)
    atomic_text(data / 'scripts/halveth_heart_test_menu.lua', MENU)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'MENU: scripts/halveth_heart_test_menu.lua\n'
                'PLAYER: scripts/halveth_genesis_smoke.lua\n')
    atomic_text(data / 'bridge/inbox.json', '{}\n')
    atomic_text(data / 'bridge/companion-status.json', '{"status":"offline"}\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    result = {'recordedAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'Disposable native OpenMW game: original book reader, real Arrille reference, owned spell record, save/reload. No personal save or physical mouse assertion.',
              'passed': False, 'profileDir': str(profile), 'personalSavesUsed': False}
    log = Path(prepared['stdout_log'])
    process = None
    try:
        with log.open('w', encoding='utf-8') as output:
            process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                       stdout=output, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            result['pid'] = process.pid
            result['exitCode'] = process.wait(timeout=90)
        lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
        result['markers'] = [line for line in lines if 'HALVETH_HEART_' in line]
        result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
        result['testSaveFiles'] = [str(p.relative_to(profile)) for p in profile.rglob('*.omwsave')]
        result['passed'] = (result['exitCode'] == 0 and not result['errors']
                            and any('HALVETH_HEART_PASS' in s for s in result['markers'])
                            and any('HALVETH_HEART_RELOADED' in s for s in result['markers'])
                            and len(result['testSaveFiles']) == 1)
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        atomic_text(state_dir / 'result.json', json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root', type=Path, default=default_install())
    parser.add_argument('--state-dir', type=Path)
    args = parser.parse_args()
    state = args.state_dir or ROOT / '.local/heart-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    result = run(args.install_root.resolve(), state.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
