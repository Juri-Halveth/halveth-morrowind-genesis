"""Exercise native plant resonance in a disposable OpenMW world.

The installed Reforged models and licensed base data are read-only VFS inputs.
Only two new test references and one disposable save are created. The harness
uses the installed Genesis engine and never opens or copies a personal save.
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
from scripts.prepare_profile import atomic_text, default_install, prepare, quoted, source_path


PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local nearby=require('openmw.nearby')
local camera=require('openmw.camera')
local util=require('openmw.util')
local I=require('openmw.interfaces')
local target,rayStart,rayPoint,attempt,settled,requested=nil,nil,nil,0,0,false
local xs={0,-10,10,-25,25,-40,40}
local zs={60,40,80,20,100,10,120}
local function tick()
    if not target or not self.cell then return end
    if not rayStart then
        attempt=attempt+1
        assert(attempt<=#xs*#zs,'No native rendering-ray intersection with the test plant')
        local x=xs[(attempt-1)%#xs+1]
        local z=zs[math.floor((attempt-1)/#xs)+1]
        local from=target.position+util.vector3(x,-220,z)
        local to=target.position+util.vector3(x,100,z)
        local hit=nearby.castRenderingRay(from,to,{ignore=self})
        if attempt<=3 then
            print('HALVETH_RESONANCE_TEST_RAY_DIAG attempt='..attempt..
                ' from='..tostring(from)..' hit='..tostring(hit.hit)..
                ' object='..tostring(hit.hitObject and hit.hitObject.id)..
                ' expected='..target.id..' position='..tostring(hit.hitPos))
        end
        if hit.hitObject and tostring(hit.hitObject.id)==target.id and hit.hitPos then
            rayStart,rayPoint=from,hit.hitPos
            print('HALVETH_RESONANCE_TEST_RAY '..target.id..' attempt='..attempt)
            core.sendGlobalEvent('HALVETH_ResonanceTestRay',{
                point=rayPoint,id=target.id})
        end
        return
    end
    camera.setMode(camera.MODE.Static,true)
    camera.setStaticPosition(rayStart)
    camera.setYaw(0);camera.setPitch(0)
    camera.setExtraYaw(0);camera.setExtraPitch(0)
    settled=settled+1
    if settled>=4 and not requested then
        assert(I.HALVETHResonance,'Native resonance PLAYER interface missing')
        assert(I.HALVETH,'Native F8 console interface missing')
        I.HALVETH.open()
        assert(I.HALVETH.isOpen(),'Native F8 console did not open')
        -- Use the existing test event to exercise the same submit/command path
        -- as typed F8 input, without pretending this is a physical-keyboard test.
        self:sendEvent('HALVETH_TestChat',{text='/resonanz'})
        requested=true
        print('HALVETH_RESONANCE_TEST_CONSOLE_REQUEST')
    end
end
return {eventHandlers={
    HALVETH_ResonanceTestAim=function(data)
        target=data;rayStart=nil;rayPoint=nil;attempt=0;settled=0;requested=false
    end,
    HALVETH_ResonanceResult=function(data)
        if requested and data.success then
            assert(not I.HALVETH.isOpen(),'Resonance command left the scene covered by F8')
        end
        core.sendGlobalEvent('HALVETH_ResonanceTestReply',data)
    end,
    HALVETH_ResonanceTestSave=function()
        types.Player.sendMenuEvent(self,'HALVETH_ResonanceTestMenuSave',{
            slot='resonance-isolated'})
    end,
},engineHandlers={onFrame=function()
    local ok,err=pcall(tick)
    if not ok then
        print('HALVETH_RESONANCE_TEST_FAIL '..tostring(err));target=nil;core.quit()
    end
end,onLoad=function()
    target=nil;rayStart=nil;rayPoint=nil;attempt=0;settled=0;requested=false
end}}
'''


GLOBAL = r'''local core=require('openmw.core')
local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')
local I=require('openmw.interfaces')
local phase,started,entered,done='start',nil,nil,false
local first,second,firstId,secondId,recordId,point,reply,baseline,rayBound
local PREVIEW_SECONDS=__PREVIEW_SECONDS__
local previewStarted,previewDone,expectedFirstVisits=nil,false,1
local function plain(p) return {x=p.x,y=p.y,z=p.z} end
local function vector(p) return util.vector3(p.x,p.y,p.z) end
local function snapshot(object)
    return {recordId=object.recordId,position=plain(object.position),scale=object.scale}
end
local function sameObject(object,b)
    return object:isValid() and object.recordId==b.recordId and object.scale==b.scale
        and (object.position-vector(b.position)):length()<0.001
end
local function playerSnapshot(player)
    local out={gold=types.Actor.inventory(player):countOf('gold_001')}
    for _,name in ipairs({'health','magicka','fatigue'}) do
        local s=types.Actor.stats.dynamic[name](player)
        out[name]={current=s.current,base=s.base,modifier=s.modifier}
    end
    return out
end
local function assertBaseline(player)
    assert(sameObject(first,baseline.first) and sameObject(second,baseline.second),
        'Resonance changed a test reference model, position or scale')
    local current=playerSnapshot(player)
    assert(current.gold==baseline.player.gold,'Resonance changed player gold')
    for _,name in ipairs({'health','magicka','fatigue'}) do
        for _,key in ipairs({'current','base','modifier'}) do
            assert(current[name][key]==baseline.player[name][key],
                'Player statistic changed: '..name..'.'..key..' before='..tostring(baseline.player[name][key])..
                ' after='..tostring(current[name][key]))
        end
    end
end
local function finish(ok,why)
    if done then return end
    done=true
    print('HALVETH_RESONANCE_TEST_'..(ok and 'PASS' or 'FAIL')..' '..why)
    if first and first:isValid() then first:remove() end
    if second and second:isValid() then second:remove() end
    core.quit()
end
local function nextPhase(value)
    phase=value;entered=core.getRealTime();reply=nil
    print('HALVETH_RESONANCE_TEST_PHASE '..value)
end
local function send(player,target,action,next)
    nextPhase(next)
    local at=point and target.position+(point-first.position) or target.position+util.vector3(0,0,60)
    core.sendGlobalEvent('HALVETH_ResonanceRequest',{
        player=player,target=target,point=at,action=action,
        sun=0.6,storm=false,requestId='resonance-test-'..next})
end
local function expect(success,status)
    if not reply then return false end
    assert(reply.success==success and reply.status==status,
        'Unexpected reply in '..phase..': '..tostring(reply.status)..' '..tostring(reply.message))
    return true
end
local function lookup(player,id)
    for _,object in ipairs(player.cell:getAll(types.Static)) do
        if tostring(object.id)==id then return object end
    end
end
local function start(player)
    assert(player.cell.isExterior,'Test scene must be exterior')
    local candidates={}
    for _,record in ipairs(types.Static.records) do
        local model=record.model:lower():gsub('\\','/')
        if model=='meshes/lucinet/plant0.dae' then candidates[#candidates+1]=record.id end
    end
    table.sort(candidates)
    recordId=assert(candidates[1],'Installed Reforged plant0 record missing')
    -- Suspended test references are isolated from terrain and existing foliage.
    -- Their geometry and model remain the installed read-only plant assets.
    first=world.createObject(recordId);second=world.createObject(recordId)
    first:teleport(player.cell,player.position+util.vector3(350,0,950))
    second:teleport(player.cell,player.position+util.vector3(-350,0,950))
    firstId=tostring(first.id);secondId=tostring(second.id)
    assert(firstId~=secondId and first.recordId==second.recordId,'Test references lack separate identities')
    nextPhase('settling')
end
local function tick()
    if done or #world.players==0 then return end
    local player=world.players[1]
    if not player.cell then return end
    local now=core.getRealTime()
    if not started then started=now;entered=now end
    if now-started>95+PREVIEW_SECONDS then error('Timeout in '..phase) end
    local resonance=assert(I.HALVETHResonanceWorld,'Native resonance GLOBAL interface missing')
    local s=resonance.getState()
    assert(s.version==1 and not s.blocked,'Resonance state unavailable or blocked')
    if phase=='start' and now-entered>2 then
        assert(s.entryCount==0,'Disposable start unexpectedly has memories')
        start(player)
    elseif phase=='settling' and now-entered>1 then
        print('HALVETH_RESONANCE_TEST_OBJECT first='..tostring(first.id)..
            ' pos='..tostring(first.position)..' record='..first.recordId..
            ' model='..types.Static.record(first).model..' scale='..first.scale)
        baseline={first=snapshot(first),second=snapshot(second),player=playerSnapshot(player)}
        send(player,first,'answer','early-answer')
    elseif phase=='early-answer' and expect(false,'FIRST_LISTEN_REQUIRED') then
        assert(s.entryCount==0,'Rejected answer created a memory')
        send(player,player,'listen','wrong-target')
    elseif phase=='wrong-target' and expect(false,'UNSUPPORTED_TARGET') then
        assert(s.entryCount==0 and s.effectSpawnCount==0,'Wrong target changed memory or effects')
        nextPhase('native-listen')
        player:sendEvent('HALVETH_ResonanceTestAim',{id=firstId,position=first.position})
    elseif phase=='native-listen' and expect(true,'LISTENED') then
        assert(rayBound and point,'Successful request lacks an actual test rendering-ray witness')
        assert(s.entryCount==1 and s.entries[firstId].stage==1 and s.entries[firstId].visits==expectedFirstVisits,
            'Native listen did not create exactly one first-stage memory')
        assert(s.cooldownRemaining>0 and s.activeEffect and s.effectSpawnCount==expectedFirstVisits,
            'Successful native listen did not create the bounded effect and cooldown')
        assertBaseline(player)
        if PREVIEW_SECONDS>0 and not previewDone then
            previewStarted=now
            nextPhase('preview')
            print('HALVETH_RESONANCE_TEST_PREVIEW_READY seconds='..PREVIEW_SECONDS..
                ' target='..firstId..' camera=static')
        else send(player,first,'listen','duplicate') end
    elseif phase=='preview' and s.cooldownRemaining<=0 then
        expectedFirstVisits=expectedFirstVisits+1
        if now-previewStarted>=PREVIEW_SECONDS then
            previewDone=true
            send(player,first,'listen','native-listen')
        else send(player,first,'listen','preview-repeat') end
    elseif phase=='preview-repeat' and expect(true,'LISTENED') then
        assert(s.entries[firstId].visits==expectedFirstVisits,'Preview response did not match instance memory')
        nextPhase('preview')
    elseif phase=='duplicate' and expect(false,'COOLDOWN') then
        assert(s.entries[firstId].visits==expectedFirstVisits and s.effectSpawnCount==expectedFirstVisits,
            'Cooldown request mutated state')
        assert(s.cooldownRemaining>3,'Save did not begin while meaningful cooldown remained')
        nextPhase('saved')
        player:sendEvent('HALVETH_ResonanceTestSave',{})
    elseif phase=='reload' and now-entered>0.15 then
        first=assert(lookup(player,firstId),'First test instance lost across save reload')
        second=assert(lookup(player,secondId),'Second test instance lost across save reload')
        assert(s.entryCount==1 and s.entries[firstId].stage==1 and not s.entries[secondId],
            'Saved per-instance memory did not round-trip')
        assert(s.cooldownRemaining>0,'Save reload removed the outstanding cooldown')
        assert(not s.activeEffect and s.effectSpawnCount==0,'Transient VFX state persisted on load')
        assertBaseline(player)
        print('HALVETH_RESONANCE_TEST_RELOAD cooldown='..s.cooldownRemaining)
        send(player,second,'listen','reload-cooldown')
    elseif phase=='reload-cooldown' and expect(false,'COOLDOWN') then
        assert(s.entryCount==1 and not s.entries[secondId],'Reload cooldown admitted a second memory')
        nextPhase('second-ready')
    elseif phase=='second-ready' and s.cooldownRemaining<=0 then
        send(player,second,'listen','second-listen')
    elseif phase=='second-listen' and expect(true,'LISTENED') then
        assert(s.entryCount==2 and s.entries[firstId].stage==1 and s.entries[secondId].stage==1,
            'Same-record instances were merged')
        assert(s.entries[firstId].visits==expectedFirstVisits and s.entries[secondId].visits==1,
            'Second instance inflated first instance memory')
        assert(s.activeEffect and s.effectSpawnCount==1,'Second instance did not spawn its transient effect')
        nextPhase('second-cleanup')
    elseif phase=='second-cleanup' and s.cooldownRemaining<=0 then
        assert(not s.activeEffect and s.cleanupCount==1,'Owned transient effect was not cleaned up')
        assertBaseline(player)
        send(player,first,'answer','answer')
    elseif phase=='answer' and expect(true,'ANSWERED') then
        assert(s.entries[firstId].stage==2 and s.entries[secondId].stage==1,
            'Answer did not preserve instance-specific stage progression')
        nextPhase('same-day-ready')
    elseif phase=='same-day-ready' and s.cooldownRemaining<=0 then
        send(player,first,'listen','same-day')
    elseif phase=='same-day' and expect(true,'LISTENED') then
        assert(s.entries[firstId].stage==2,'Same-day repetition unlocked next-day memory')
        nextPhase('next-day-ready')
    elseif phase=='next-day-ready' and s.cooldownRemaining<=0 then
        world.advanceTime(24)
        nextPhase('advanced')
    elseif phase=='advanced' and now-entered>0.1 then
        send(player,first,'listen','remembered')
    elseif phase=='remembered' and expect(true,'REMEMBERED') then
        local entry=s.entries[firstId]
        assert(entry.stage==3 and entry.lastDay>entry.firstDay and entry.visits==expectedFirstVisits+3,
            'Next-day progression or visit count incorrect')
        assert(s.entries[secondId].stage==1 and s.entries[secondId].visits==1,
            'Independent second instance changed during first progression')
        nextPhase('last-cleanup')
    elseif phase=='last-cleanup' and s.cooldownRemaining<=0 then
        assert(not s.activeEffect and s.effectSpawnCount==4 and s.cleanupCount==4,
            'Transient effect lifecycle counts are inconsistent after reload')
        assertBaseline(player)
        finish(true,'nativeRenderingRay=PASS nativeConsoleCommand=PASS queuedPlayerRequest=PASS earlyAnswer=PASS wrongTarget=PASS '..
            'perInstanceMemory=PASS cooldown=PASS actualSaveReload=PASS savedCooldown=PASS '..
            'answer=PASS nextDayMemory=PASS ownedEffectLifecycle=PASS statisticsAndReferencesPreserved=PASS')
    end
end
return {eventHandlers={
    HALVETH_ResonanceTestReply=function(data)reply=data end,
    HALVETH_ResonanceTestRay=function(data)
        assert(data.id==firstId,'Rendering ray selected another instance')
        point=data.point;rayBound=true
    end,
},engineHandlers={onUpdate=function()
    local ok,err=pcall(tick);if not ok then finish(false,tostring(err)) end
end,onSave=function()
    return {phase=phase,firstId=firstId,secondId=secondId,recordId=recordId,
        point=point and plain(point),baseline=baseline,rayBound=rayBound,
        expectedFirstVisits=expectedFirstVisits}
end,onLoad=function(data)
    assert(data and data.phase=='saved','Unexpected disposable resonance save payload')
    firstId=data.firstId;secondId=data.secondId;recordId=data.recordId
    point=vector(data.point);baseline=data.baseline;rayBound=data.rayBound
    expectedFirstVisits=data.expectedFirstVisits
    first=nil;second=nil;done=false;started=core.getRealTime();nextPhase('reload')
end}}
'''


MENU = r'''local core=require('openmw.core')
local menu=require('openmw.menu')
local pending,started,loaded
return {eventHandlers={HALVETH_ResonanceTestMenuSave=function(data)
    assert(not pending and not loaded and data.slot=='resonance-isolated','Unexpected save request')
    pending=data.slot
    menu.saveGame('HALVETH isolated resonance integration',pending)
    started=core.getRealTime()
end},engineHandlers={onFrame=function()
    if not pending or core.getRealTime()-started<0.35 then return end
    local dir=menu.getCurrentSaveDir()
    for slot,info in pairs(menu.getSaves(dir)) do
        if info.description=='HALVETH isolated resonance integration' then
            print('HALVETH_RESONANCE_TEST_SAVED '..dir..'/'..slot)
            pending=nil;loaded=true;menu.loadGame(dir,slot);return
        end
    end
    if core.getRealTime()-started>10 then
        print('HALVETH_RESONANCE_TEST_FAIL disposable save absent');menu.quit()
    end
end}}
'''


def installed_genesis() -> Path:
    relative = Path('HALVETH/Morrowind Genesis')
    candidates = [Path.home() / 'AppData/Local' / relative,
                  Path(os.environ.get('LOCALAPPDATA', '~/.local/share')).expanduser() / relative]
    for candidate in candidates:
        if (candidate / 'engine/openmw.exe').is_file():
            return candidate.resolve()
    raise FileNotFoundError('Installed Genesis engine not found; provide --genesis-root.')


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--genesis-root', type=Path)
    parser.add_argument('--source-install', type=Path, default=default_install())
    parser.add_argument('--reforged-root', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--preview-seconds', type=int, default=0,
                        help='Hold the aimed test scene with bounded native pulses before assertions continue (0..120).')
    args = parser.parse_args()
    if not 0 <= args.preview_seconds <= 120:
        parser.error('--preview-seconds must be between 0 and 120')
    genesis = args.genesis_root.resolve() if args.genesis_root else installed_genesis()
    reforged = (args.reforged_root or genesis / 'app/.local/graphics/mods/LUCINET-World-Reforged-1.1.0').resolve()
    engine = genesis / 'engine/openmw.exe'
    plugin = reforged / 'LUCINET-World-Reforged.esp'
    sources = [ROOT / 'mod/scripts/halveth' / name for name in (
        'resonance_rules.lua', 'world_resonance_global.lua', 'world_resonance.lua')]
    for required in [engine, plugin, reforged / 'Meshes/lucinet/plant0.dae', *sources]:
        if not required.is_file():
            raise FileNotFoundError(f'Required local test input absent: {required}')
    state = ROOT / '.local/resonance-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    prepared = prepare(argparse.Namespace(
        install_root=args.source_install, state_dir=state, source_profile='max',
        profile='original', smoke=True, copy_saves=False, reset_settings=True))
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    for name, text in [('player', PLAYER), ('global', GLOBAL), ('menu', MENU)]:
        atomic_text(data / f'scripts/halveth_resonance_test_{name}.lua',
                    text.replace('__PREVIEW_SECONDS__', str(args.preview_seconds)))
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'MENU: scripts/halveth_resonance_test_menu.lua\n'
                'GLOBAL: scripts/halveth_resonance_test_global.lua\n'
                'PLAYER: scripts/halveth_resonance_test_player.lua\n')
    atomic_text(data / 'bridge/inbox.json', '{}\n')
    atomic_text(data / 'bridge/companion-status.json', '{"status":"offline"}\n')
    # Bind the running engine and five static model overrides to Genesis. All
    # other licensed input paths remain references; no game asset is copied.
    cfg = profile / 'openmw.cfg'
    lines = []
    for line in cfg.read_text(encoding='utf-8').splitlines():
        key, sep, value = line.partition('=')
        if key == 'resources':
            line = 'resources=' + quoted(engine.parent / 'resources')
        elif key == 'data':
            path = source_path(value, profile)
            if path.name.casefold() == reforged.name.casefold():
                continue
            if path.name == 'vfs-mw' and path.parent.name == 'resources':
                line = 'data=' + quoted(engine.parent / 'resources/vfs-mw')
        elif key == 'content' and value.strip('"').casefold() == plugin.name.casefold():
            continue
        lines.append(line)
    insert = next(index for index, line in enumerate(lines) if line == 'content=halveth.omwscripts')
    lines[insert:insert] = ['data=' + quoted(reforged), 'content=' + plugin.name]
    atomic_text(cfg, '\n'.join(lines) + '\n')
    prepared['command'][0] = str(engine)
    prepared['command'][-1] = 'Seyda Neen'
    prepared['cwd'] = str(engine.parent)
    log = Path(prepared['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Disposable native OpenMW: rendering-ray selection and native F8 command submission, two own same-record plant references, '
                 'per-instance memory, cooldown, save/reload, authored next-day progression, transient VFX '
                 'lifecycle counters and unchanged player statistics/references. No visual-quality, physical '
                 'keyboard-input, audible-sound or unrelated-VFX-preservation claim.',
        'personalSavesUsed': False,
        'engine': str(engine), 'reforgedInput': str(reforged), 'state': str(state),
        'sourceSha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [*sources, ROOT / 'mod/halveth.omwscripts', Path(__file__)]},
        'pluginSha256': hashlib.sha256(plugin.read_bytes()).hexdigest(),
        'preparedOnly': args.prepare_only,
        'previewSeconds': args.preview_seconds,
    }
    if args.prepare_only:
        atomic_text(state / 'prepared.json', json.dumps(result, indent=2, ensure_ascii=False))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    with log.open('w', encoding='utf-8') as output:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                   stdout=output, stderr=subprocess.STDOUT)
        print(json.dumps({'pid': process.pid, 'state': str(state),
                          'windowTitleHint': 'OpenMW', 'previewSeconds': args.preview_seconds}), flush=True)
        try:
            result['exitCode'] = process.wait(timeout=120 + args.preview_seconds)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=10)
            result['exitCode'] = 'TIMEOUT'
    records = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result['errors'] = [line for line in records if ' E]' in line or 'Lua error' in line]
    result['markers'] = [line for line in records if 'HALVETH_RESONANCE_TEST_' in line]
    result['passed'] = (result['exitCode'] == 0 and not result['errors']
                        and not any('HALVETH_RESONANCE_TEST_FAIL' in line for line in records)
                        and any('HALVETH_RESONANCE_TEST_PASS' in line for line in records))
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
