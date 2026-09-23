"""Exercise native NPC observation, dialogue memory and save reload in Morrowind.

The OpenMW profile is disposable. The only NPC under test is the real Arrille
reference from an installed TES III game; personal saves are never copied.
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

PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local nearby=require('openmw.nearby')
local I=require('openmw.interfaces')
local phase,entered,started,done='observe',nil,nil,false
local actorId
local function finish(ok,detail)
    if done then return end
    done=true
    print('HALVETH_WORLDLIFE_'..(ok and 'PASS' or 'FAIL')..' '..detail)
    core.quit()
end
local function nextPhase(next)
    phase=next;entered=core.getRealTime()
end
local function actor()
    for _,obj in ipairs(nearby.actors) do
        if obj:isValid() and obj.recordId=='arrille' then return obj end
    end
end
local function person(id)
    for _,p in ipairs(I.HALVETHWorldlife.getState().people) do
        if p.id==id then return p end
    end
end
local function tick()
    if done or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>80 then error('Timeout at '..phase) end
    if phase=='observe' and now-entered>3 then
        assert(I.HALVETHWorldlife,'Native worldlife interface absent')
        local npc=actor()
        assert(npc,'Real Arrille NPC not loaded')
        actorId=tostring(npc.id)
        local p=person(actorId)
        assert(p and p.name and p.sightings==1,'Passive real NPC observation missing')
        assert(I.HALVETHWorldlife.observe(npc,true),'Real dialogue observation failed')
        assert(not I.HALVETHWorldlife.observe(npc,true),'Rapid dialogue repeat was counted twice')
        p=person(actorId)
        assert(p.dialogues==1 and p.sightings==1,'Dialogue or daily presence count incorrect')
        local c=I.HALVETHWorldlife.getContext()
        assert(c and c.observedPeople>=1 and c.pulseMeaning,'Companion context lacks bounded worldlife')
        I.HALVETHWorldlife.open()
        assert(I.HALVETHWorldlife.isOpen(),'Native chronicle window did not open')
        assert(not I.HALVETHWorldlife.select('missing-instance'),'Unknown NPC was selected')
        assert(I.HALVETHWorldlife.select(actorId),'Observed Arrille could not be selected')
        assert(I.HALVETHWorldlife.talkSelected(),'Chronicle could not open conversation with nearby Arrille')
        assert(not I.HALVETHWorldlife.isOpen(),'Native chronicle window did not close')
        assert(I.HALVETH.isOpen(),'Selected NPC conversation did not open in game')
        I.HALVETH.close()
        nextPhase('saved')
        require('openmw.types').Player.sendMenuEvent(self,'HALVETH_WorldlifeSave',{slot='worldlife-isolated'})
    elseif phase=='reloaded' and now-entered>1 then
        local p=person(actorId)
        assert(p and p.dialogues==1 and p.sightings==1,'Real NPC memory lost across save reload')
        assert(I.HALVETHWorldlife.getState().panelOpen==false,'UI state persisted as open')
        assert(I.HALVETHWorldlife.observe(actor(),false),'Real NPC no longer observable after reload')
        assert(person(actorId).sightings==1,'Same-day presence inflated after reload')
        finish(true,'realNPC=PASS presenceDedup=PASS dialogueDedup=PASS nativeConversation=PASS companionContext=PASS actualSaveReload=PASS')
    end
end
return {engineHandlers={
    onFrame=function() local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end end,
    onSave=function()return {phase=phase,actorId=actorId}end,
    onLoad=function(data)
        assert(data and data.phase=='saved','Unexpected isolated save payload')
        actorId=data.actorId;done=false;started=core.getRealTime();nextPhase('reloaded')
        print('HALVETH_WORLDLIFE_RELOADED '..tostring(actorId))
    end}}
'''

MENU = r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_WorldlifeSave=function(data)
    assert(not pending and not loaded and data.slot=='worldlife-isolated','Unexpected save request')
    pending=data.slot
    menu.saveGame('HALVETH isolated worldlife integration',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<1 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated worldlife integration' then
            print('HALVETH_WORLDLIFE_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true
            menu.loadGame(dir,slot)
            return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_WORLDLIFE_FAIL Isolated save absent');menu.quit()
    end
end}}
'''


def run() -> int:
    state = ROOT / '.local' / 'worldlife-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    )
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='original', smoke=True, copy_saves=False, reset_settings=True
    ))
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    atomic_text(data / 'scripts/halveth_worldlife_test.lua', PLAYER)
    atomic_text(data / 'scripts/halveth_worldlife_menu.lua', MENU)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'MENU: scripts/halveth_worldlife_menu.lua\n'
                'PLAYER: scripts/halveth_worldlife_test.lua\n')
    atomic_text(data / 'bridge/inbox.json', '{}\n')
    atomic_text(data / 'bridge/companion-status.json', '{"status":"offline"}\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(prepared['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Disposable installed OpenMW, actual Arrille NPC and native UI, save/reload; no personal saves or Bethesda record mutation.',
        'sourceSha256': hashlib.sha256((ROOT / 'mod/scripts/halveth/worldlife.lua').read_bytes()).hexdigest(),
        'personalSavesUsed': False,
    }
    with log.open('w', encoding='utf-8') as output:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                   stdout=output, stderr=subprocess.STDOUT)
        print(json.dumps({'pid': process.pid, 'state': str(state)}), flush=True)
        try:
            result['exitCode'] = process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            result['exitCode'] = 'TIMEOUT'
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers'] = [line for line in lines if 'HALVETH_WORLDLIFE_' in line]
    result['passed'] = (result['exitCode'] == 0 and not result['errors']
                        and any('HALVETH_WORLDLIFE_PASS' in line for line in lines))
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
