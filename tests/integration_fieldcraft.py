"""Native loose-ingredient survey and isolated save/reload, without personal saves."""
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


GLOBAL_TEST = r'''local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')
return {eventHandlers={HALVETH_FieldcraftFixture=function(data)
    local id='ingred_wickwheat_01'
    assert(types.Ingredient.records[id],'Original Morrowind ingredient missing')
    local object=world.createObject(id,1)
    object:teleport(data.player.cell,data.player.position+util.vector3(100,0,0))
    print('HALVETH_FIELDCRAFT_FIXTURE '..tostring(object.id))
end}}
'''

PLAYER_TEST = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local phase,started,entered,done='start',nil,nil,false
local ingredientId,expected,beforeGold,beforeAlchemy
local function nextPhase(next)
    phase=next;entered=core.getRealTime()
end
local function finish(ok,message)
    if done then return end
    done=true;print('HALVETH_FIELDCRAFT_'..(ok and 'PASS' or 'FAIL')..' '..message);core.quit()
end
local function fixtureEntry()
    local f=I.HALVETHFieldcraft
    f.refresh()
    for _,entry in ipairs(f.getState().nearby) do
        if entry.recordId=='ingred_wickwheat_01' then return entry end
    end
end
local function tick()
    if done or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>45 then error('Timeout at '..phase) end
    local elapsed=now-entered
    local f=I.HALVETHFieldcraft
    assert(f,'Native fieldcraft interface missing')
    if phase=='start' and elapsed>1 then
        beforeGold=types.Actor.inventory(self):countOf('gold_001')
        beforeAlchemy=types.NPC.stats.skills.alchemy(self).base
        assert(#f.getState().sightings==0,'New fieldcraft save not empty')
        core.sendGlobalEvent('HALVETH_FieldcraftFixture',{player=self.object})
        nextPhase('fixture')
    elseif phase=='fixture' and elapsed>1 then
        local entry=fixtureEntry()
        assert(entry and entry.distance<3000,'Real loose ingredient missing from nearby.items')
        assert(entry.direction and entry.direction~='nicht mehr sichtbar','World direction unavailable')
        ingredientId=entry.id
        assert(f.select(ingredientId),'Could not select real ingredient')
        f.open();assert(f.getState().panelOpen,'Native fieldcraft panel absent')
        assert(f.getState().detail:find('Wickwheat',1,true),'Native panel lacks real ingredient')
        assert(f.survey(),'Real location not recorded')
        assert(not f.survey(),'Duplicate ingredient/cell observation counted')
        local s=f.getState()
        assert(#s.sightings==1 and s.sightings[1].recordId=='ingred_wickwheat_01','Observation data invalid')
        expected=s.sightings[1]
        assert(f.track(ingredientId),'Cannot follow real ingredient')
        f.close()
        nextPhase('tracking')
    elseif phase=='tracking' and elapsed>1 then
        local s=f.getState()
        assert(s.tracked==ingredientId and s.trackerOpen,'Native HUD tracking absent')
        assert(types.Actor.inventory(self):countOf('gold_001')==beforeGold,'Gold changed during survey')
        assert(types.NPC.stats.skills.alchemy(self).base==beforeAlchemy,'Original skill changed during survey')
        nextPhase('saved')
        types.Player.sendMenuEvent(self,'HALVETH_FieldcraftSave',{slot='halveth-fieldcraft-isolated'})
    elseif phase=='reloaded' and elapsed>1 then
        local s=f.getState()
        assert(#s.sightings==1,'Fieldcraft observation lost in actual save/reload')
        assert(s.sightings[1].recordId==expected.recordId and s.sightings[1].cell==expected.cell,
            'Fieldcraft observation changed after reload')
        assert(s.tracked==nil and not s.trackerOpen,'Ephemeral world target persisted across reload')
        assert(types.Actor.inventory(self):countOf('gold_001')==beforeGold,'Gold changed after save/reload')
        assert(types.NPC.stats.skills.alchemy(self).base==beforeAlchemy,'Original skill changed after save/reload')
        local entry=fixtureEntry()
        if entry then
            assert(f.select(entry.id),'Saved world item not selectable')
            assert(not f.survey(),'Save/reload allowed duplicate observation')
        end
        finish(true,'realLooseIngredient=PASS nativePanel=PASS uniqueLocation=PASS hudTracker=PASS saveReload=PASS originalGoldAndSkill=PASS')
    end
end
return {engineHandlers={onFrame=function()
    local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end
end,onSave=function()return {phase=phase,expected=expected,beforeGold=beforeGold,beforeAlchemy=beforeAlchemy}end,
onLoad=function(data)
    assert(data and data.phase=='saved','Unexpected isolated save payload')
    expected=data.expected;beforeGold=data.beforeGold;beforeAlchemy=data.beforeAlchemy
    done=false;started=core.getRealTime();nextPhase('reloaded')
    print('HALVETH_FIELDCRAFT_RELOADED')
end}}
'''

MENU_TEST = r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_FieldcraftSave=function(data)
    assert(not pending and not loaded and data.slot=='halveth-fieldcraft-isolated','Unexpected isolated save request')
    pending=data.slot;menu.saveGame('HALVETH isolated fieldcraft integration',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated fieldcraft integration' then
            print('HALVETH_FIELDCRAFT_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true;menu.loadGame(dir,slot);return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_FIELDCRAFT_FAIL Isolated save did not materialize');menu.quit()
    end
end}}
'''


def run(install_root: Path, state_dir: Path) -> dict:
    receipt = prepare(argparse.Namespace(install_root=install_root, state_dir=state_dir,
                                        source_profile='max', profile='original', smoke=True,
                                        copy_saves=False, reset_settings=True))
    profile = Path(receipt['profile_dir'])
    data = profile / 'data'
    for name, value in (
        ('scripts/halveth_genesis_smoke.lua', PLAYER_TEST),
        ('scripts/halveth_fieldcraft_test_global.lua', GLOBAL_TEST),
        ('scripts/halveth_fieldcraft_test_menu.lua', MENU_TEST),
        ('bridge/inbox.json', '{}\n'),
        ('bridge/companion-status.json', '{"status":"offline"}\n'),
    ):
        atomic_text(data / name, value)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'GLOBAL: scripts/halveth_fieldcraft_test_global.lua\n'
                'MENU: scripts/halveth_fieldcraft_test_menu.lua\n'
                'PLAYER: scripts/halveth_genesis_smoke.lua\n')
    receipt['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(receipt['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(), 'passed': False,
        'scope': 'Real nearby.items loose ingredient, in-game native panel and HUD, unique ingredient/cell note, actual isolated OpenMW save/reload, original gold and Alchemy unchanged. Fresh profile; no personal save.',
        'profileDir': str(profile), 'log': str(log), 'personalSavesUsed': False,
        'sourceConfigSHA256': receipt['source_config_sha256'],
        'sourceSettingsSHA256': receipt['source_settings_sha256'],
        'testedFiles': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            'mod/scripts/halveth/fieldcraft.lua', 'mod/scripts/halveth/universe.lua',
            'mod/halveth.omwscripts')},
    }
    process = None
    try:
        with log.open('w', encoding='utf-8') as output:
            process = subprocess.Popen(receipt['command'], cwd=receipt['cwd'], stdout=output,
                                       stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            result['pid'] = process.pid
            result['exitCode'] = process.wait(timeout=75)
        lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
        result['markers'] = [line for line in lines if 'HALVETH_FIELDCRAFT_' in line]
        result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
        result['testSaveFiles'] = [str(p.relative_to(profile)) for p in profile.rglob('*.omwsave')]
        result['originalSettingsPreserved'] = all(
            hashlib.sha256((install_root / 'profiles/max' / name).read_bytes()).hexdigest() == result[key]
            for name, key in (('openmw.cfg', 'sourceConfigSHA256'),
                              ('settings.cfg', 'sourceSettingsSHA256')))
        result['passed'] = (result['exitCode'] == 0 and not result['errors']
                            and any('HALVETH_FIELDCRAFT_PASS' in line for line in result['markers'])
                            and any('HALVETH_FIELDCRAFT_RELOADED' in line for line in result['markers'])
                            and len(result['testSaveFiles']) == 1 and result['originalSettingsPreserved'])
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
    atomic_text(state_dir / 'result.json', json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root', type=Path, default=default_install())
    parser.add_argument('--state-dir', type=Path, default=ROOT / '.local' / 'fieldcraft-integration' /
                        (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]))
    options = parser.parse_args()
    raise SystemExit(0 if run(options.install_root, options.state_dir)['passed'] else 1)
