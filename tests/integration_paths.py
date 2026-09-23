"""Exercise save-backed HALVETH routes in a disposable native Morrowind session.

The test uses real OpenMW Book/Scroll windows, two dynamically-created book
records, and Arrille's loaded NPC reference. Only its isolated profile receives
a save; it never copies or loads a personal savegame.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
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
local nearby=require('openmw.nearby')
local I=require('openmw.interfaces')
local phase,entered,started,finished='start',nil,nil,false
local bookId,scrollId,actorId,expected
local function transition(nextPhase)
    phase=nextPhase;entered=core.getRealTime()
end
local function finish(ok,message)
    if finished then return end
    finished=true
    print('HALVETH_PATHS_'..(ok and 'PASS' or 'FAIL')..' '..message)
    core.quit()
end
local function has(list,value)
    for _,item in ipairs(list) do if item==value then return true end end
    return false
end
local function actor()
    for _,item in ipairs(nearby.actors) do
        if item:isValid() and item.recordId=='arrille' then return item end
    end
end
local function item(id)
    return types.Actor.inventory(self):find(id)
end
local function route() return I.HALVETHPaths.getState() end
local function tick()
    if finished or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>65 then error('Timeout at '..phase) end
    local elapsed=now-entered
    if phase=='start' and elapsed>1 then
        assert(I.HALVETHPaths,'Native paths interface missing')
        assert(#route().completed==0 and #route().rewarded==0,'Unexpected fresh route state')
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='library',requestId='paths-books'})
        transition('content')
    elseif phase=='begin' and elapsed>0.2 then
        assert(bookId and scrollId and item(bookId) and item(scrollId),'Real book records absent from native inventory')
        assert(not I.HALVETHPaths.begin('not-a-route'),'Unknown route accepted')
        assert(I.HALVETHPaths.begin('lore'),'Knowledge route could not start')
        assert(not I.HALVETHPaths.begin('people'),'Started a second route over an active route')
        assert(route().active=='lore','Selected route not active')
        I.HALVETHPaths.open()
        assert(route().panelOpen,'Native path window did not open')
        I.HALVETHPaths.close()
        assert(not route().panelOpen,'Native path window did not close')
        I.UI.addMode('Interface',{windows={'Inventory'}})
        I.UI.addMode('Book',{target=item(bookId)})
        transition('book')
    elseif phase=='book' and elapsed>0.4 then
        assert(I.UI.getMode()=='Book','Original book reader did not open')
        assert(has(route().books,bookId),'Original book window did not advance route')
        assert(not I.HALVETHPaths.noteBook(item(bookId)),'Same book counted twice')
        I.UI.removeMode('Book')
        I.UI.addMode('Scroll',{target=item(scrollId)})
        transition('scroll')
    elseif phase=='scroll' and elapsed>0.4 then
        assert(I.UI.getMode()=='Scroll','Original scroll reader did not open')
        assert(has(route().books,scrollId) and #route().books==2,'Distinct scroll did not advance route once')
        I.UI.removeMode('Scroll');I.UI.removeMode('Interface')
        local npc=actor()
        assert(npc and (npc.position-self.position):length()<=3000,'Arrille NPC reference not nearby')
        actorId=tostring(npc.id)
        assert(I.HALVETHPaths.noteNpc(npc),'Actual Arrille NPC did not complete route')
        local s=route()
        assert(not s.active and has(s.completed,'lore') and #s.people==0,'Completed route state invalid')
        assert(not has(s.rewarded,'lore'),'Route auto-claimed reward')
        local fatigue=types.Actor.stats.dynamic.fatigue(self)
        local ceiling=math.max(0,fatigue.base+fatigue.modifier)
        fatigue.current=math.max(0,ceiling-80)
        local before=fatigue.current
        assert(I.HALVETHPaths.claim(),'Completed route reward not claimable')
        assert(math.abs(fatigue.current-before-30)<.001,'Reward did not restore exactly 30 fatigue')
        assert(not I.HALVETHPaths.claim(),'One-time reward claimed twice')
        assert(has(route().rewarded,'lore'),'Claim flag missing after reward')
        assert(not I.HALVETHPaths.begin('lore'),'Completed route restarted')
        assert(I.HALVETHPaths.begin('people'),'Second route did not start')
        assert(#route().places==1,'Starting cell not registered in route')
        assert(I.HALVETHPaths.noteNpc(npc),'Actual NPC did not advance second route')
        assert(not I.HALVETHPaths.noteNpc(npc),'NPC counted twice within one route')
        assert(has(route().people,actorId),'Actual NPC identity not retained in progress')
        assert(I.HALVETHPaths.checkSaveRoundTrip(),'Route save schema failed preflight')
        expected={active='people',actorId=actorId,place=route().places[1]}
        transition('saved')
        types.Player.sendMenuEvent(self,'HALVETH_PathsSave',{slot='halveth-paths-isolated'})
    elseif phase=='reloaded' and elapsed>0.8 then
        local s=route()
        assert(expected and s.active==expected.active,'Active route lost across actual save/load')
        assert(#s.people==1 and has(s.people,expected.actorId),'Real NPC progress lost across save/load')
        assert(#s.places==1 and has(s.places,expected.place),'Cell progress lost across save/load')
        assert(has(s.completed,'lore') and has(s.rewarded,'lore'),'Completed/rewarded route lost across save/load')
        assert(not I.HALVETHPaths.claim(),'Reward duplicated after reload')
        assert(not I.HALVETHPaths.begin('world'),'Reloaded active route allowed a second active route')
        assert(I.HALVETHPaths.abandon(),'Could not leave active route after reload')
        assert(not route().active and has(route().completed,'lore'),'Leaving route erased completed route')
        assert(not I.HALVETHPaths.begin('lore'),'Completed route restarted after reload')
        finish(true,'realBook=PASS realScroll=PASS nativeReaders=PASS realNPC=PASS dedup=PASS routeCompletion=PASS oneTimeReward=PASS activeRouteSaveReload=PASS')
    end
end
return {engineHandlers={
    onFrame=function() local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end end,
    onSave=function() return {phase=phase,bookId=bookId,scrollId=scrollId,expected=expected} end,
    onLoad=function(data)
        assert(data and data.phase=='saved','Unexpected test save payload')
        bookId=data.bookId;scrollId=data.scrollId;expected=data.expected
        finished=false;started=core.getRealTime();transition('reloaded')
        print('HALVETH_PATHS_RELOADED '..tostring(bookId))
    end},eventHandlers={HALVETH_ContentResult=function(data)
        if data.requestId~='paths-books' then return end
        local ok,err=pcall(function()
            assert(data.success,data.message)
            for _,book in ipairs(data.books) do
                if book.key=='glassleaf-primer' then bookId=book.recordId end
                if book.key=='moonwater-scroll' then scrollId=book.recordId end
            end
            assert(bookId and scrollId,'Own actual book and scroll not returned')
            transition('begin')
        end)
        if not ok then finish(false,tostring(err)) end
    end}}
'''

MENU_TEST = r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_PathsSave=function(data)
    assert(not pending and not loaded and data.slot=='halveth-paths-isolated','Unexpected save request')
    pending=data.slot
    menu.saveGame('HALVETH isolated paths integration',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated paths integration' then
            print('HALVETH_PATHS_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true
            menu.loadGame(dir,slot)
            return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_PATHS_FAIL Isolated save did not materialize');menu.quit()
    end
end}}
'''


def run(install_root: Path, state_dir: Path) -> dict:
    args = argparse.Namespace(install_root=install_root, state_dir=state_dir,
                              source_profile='max', profile='original', smoke=True,
                              copy_saves=False, reset_settings=True)
    prepared = prepare(args)
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    atomic_text(data / 'scripts/halveth_genesis_smoke.lua', PLAYER_TEST)
    atomic_text(data / 'scripts/halveth_paths_test_menu.lua', MENU_TEST)
    atomic_text(data / 'bridge/inbox.json', '{}\n')
    atomic_text(data / 'bridge/companion-status.json', '{"status":"offline"}\n')
    live_manifest = (ROOT / 'mod/halveth.omwscripts').read_text(encoding='utf-8')
    path_registration = '' if 'PLAYER: scripts/halveth/paths.lua' in live_manifest else (
        'PLAYER: scripts/halveth/paths.lua\n')
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                path_registration + 'MENU: scripts/halveth_paths_test_menu.lua\n'
                'PLAYER: scripts/halveth_genesis_smoke.lua\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(prepared['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'passed': False,
        'scope': 'Actual OpenMW book/scroll modes and record references, loaded Arrille NPC, route completion and one-time fatigue reward, then real isolated save/load with active route. Fresh game; no personal saves, physical input, or screenshot assertion.',
        'profileDir': str(profile), 'log': str(log), 'personalSavesUsed': False,
        'sourceConfigSHA256': prepared['source_config_sha256'],
        'sourceSettingsSHA256': prepared['source_settings_sha256'],
        'testedFiles': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            'mod/scripts/halveth/paths.lua', 'mod/scripts/halveth/content.lua',
            'mod/halveth.omwscripts')},
    }
    process = None
    try:
        with log.open('w', encoding='utf-8') as output:
            process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'], stdout=output,
                                       stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            result['pid'] = process.pid
            result['exitCode'] = process.wait(timeout=90)
        lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
        result['markers'] = [line for line in lines if 'HALVETH_PATHS_' in line]
        result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
        result['testSaveFiles'] = [str(p.relative_to(profile)) for p in profile.rglob('*.omwsave')]
        result['originalSettingsPreserved'] = all(
            hashlib.sha256((install_root / 'profiles/max' / name).read_bytes()).hexdigest() == result[key]
            for name, key in (('openmw.cfg', 'sourceConfigSHA256'),
                              ('settings.cfg', 'sourceSettingsSHA256')))
        result['passed'] = (
            result['exitCode'] == 0 and not result['errors']
            and any('HALVETH_PATHS_PASS' in line for line in result['markers'])
            and any('HALVETH_PATHS_RELOADED' in line for line in result['markers'])
            and len(result['testSaveFiles']) == 1 and result['originalSettingsPreserved'])
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root', type=Path, default=default_install())
    parser.add_argument('--state-dir', type=Path)
    args = parser.parse_args()
    state = args.state_dir or ROOT / '.local/paths-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    result = run(args.install_root.resolve(), state.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
