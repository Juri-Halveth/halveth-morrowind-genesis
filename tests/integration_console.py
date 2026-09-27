#!/usr/bin/env python3
"""Check the native F8 book context and typed citizen actions in disposable OpenMW."""
from __future__ import annotations

import argparse
import configparser
from datetime import datetime, timezone
import io
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
local I=require('openmw.interfaces')
local markup=require('openmw.markup')
local started,phase,bookId,finished,phaseAt=nil,'start',nil,false,nil

local function finish(ok,message)
    if finished then return end
    finished=true
    print('HALVETH_CONSOLE_'..(ok and 'PASS' or 'FAIL')..' '..message)
    core.quit()
end

return {engineHandlers={onFrame=function()
    if finished or not self.cell then return end
    if not started then started=core.getRealTime() end
    local now=core.getRealTime()
    local ok,err=pcall(function()
        if now-started>2 and phase=='start' then
            phase='books'
            core.sendGlobalEvent('HALVETH_ContentRequest',
                {player=self.object,request='library',requestId='console-books'})
        elseif phase=='launcher' and now-phaseAt>.4 then
            local launcher=I.HALVETHUniverse.getLauncherState()
            assert(launcher.visible and launcher.entryCount==1,'single native launcher did not appear')
            I.HALVETH.open()
            assert(I.HALVETH.isOpen(),'native F8 window did not open')
            phase,phaseAt='console',now
        elseif phase=='console' and now-phaseAt>.4 then
            local launcher=I.HALVETHUniverse.getLauncherState()
            assert(not launcher.visible,'launcher remained over F8')
            local console=I.HALVETH
            assert(console.attachItem(bookId),'could not insert owned inventory book')
            local state=console.getConsoleState()
            assert(state.attachedItemId==bookId and state.inputText:find('Inventar:',1,true),
                'selected book not inserted into visible prompt')
            phase='chat'
            self:sendEvent('HALVETH_TestChat',{entityMode='jarvis',text='Was ist dieses Buch?'})
        end
        if now-started>25 then finish(false,'timed out waiting for native book/context') end
    end)
    if not ok then finish(false,tostring(err)) end
end},eventHandlers={
    HALVETH_ContentResult=function(data)
        if phase~='books' or data.requestId~='console-books' then return end
        local ok,err=pcall(function()
            assert(data.success and data.books[1],'native book not created')
            bookId=data.books[1].recordId
            assert(types.Actor.inventory(self):find(bookId),'real inventory book missing')
            if I.HALVETHMicrophone and I.HALVETHMicrophone.isOpen
                and I.HALVETHMicrophone.isOpen() then I.HALVETHMicrophone.decline() end
            I.UI.addMode('Interface',{windows={'Inventory'}})
            phase,phaseAt='launcher',core.getRealTime()
        end)
        if not ok then finish(false,tostring(err)) end
    end,
    HALVETH_ChatSubmitted=function(data)
        if phase~='chat' then return end
        local ok,err=pcall(function()
            local c=markup.decodeYaml(data.contextJson)
            local item=c.selectedInventoryItem
            assert(item and item.id==bookId,'real selected item absent from chat context')
            assert(item.count==types.Actor.inventory(self):countOf(bookId),'inventory count mismatch')
            local book=types.Book.records[bookId]
            assert(item.book and item.book.title==book.name,'book metadata missing')
            assert(item.book.text==book.text,'authored book text was not attached')
            assert(data.text=='Was ist dieses Buch?','the question changed during submission')
            assert(I.HALVETH.getConsoleState().attachedItemId==nil,'attachment not cleared after send')
            phase='citizens_spawn'
            self:sendEvent('HALVETH_TestChat',{text='/buerger rufen'})
        end)
        if not ok then finish(false,tostring(err)) end
    end,
    HALVETH_CitizensResult=function(data)
        local ok,err=pcall(function()
            if phase=='citizens_spawn' and data.message=='Eigene Buerger koennen nur draussen gerufen werden.' then
                phase='citizens_dismiss'
                self:sendEvent('HALVETH_TestChat',{text='/buerger entfernen'})
            elseif phase=='citizens_dismiss' and data.message=='Keine aktiven eigenen Buerger vorhanden.' then
                phase='citizens_status'
                self:sendEvent('HALVETH_TestChat',{text='/buerger status'})
            elseif phase=='citizens_status' then
                assert(I.HALVETH.isOpen(),'citizen commands closed the native console')
                I.HALVETH.close()
                assert(not I.HALVETH.isOpen(),'F8 window stayed open')
                I.UI.removeMode('Interface')
                finish(true,'one launcher -> F8 book context -> typed citizen spawn/dismiss/status -> close')
            end
        end)
        if not ok then finish(false,tostring(err)) end
    end
}}
'''


def run() -> int:
    state = ROOT / '.local' / 'console-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    )
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='beauty', smoke=True, copy_saves=False, reset_settings=True
    ))
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    settings = configparser.ConfigParser(interpolation=None)
    settings.read(profile / 'settings.cfg', encoding='utf-8-sig')
    settings['Video']['window mode'] = '0'
    settings['Video']['resolution x'] = '1280'
    settings['Video']['resolution y'] = '720'
    settings['Video']['minimize on focus loss'] = 'false'
    output = io.StringIO()
    settings.write(output)
    atomic_text(profile / 'settings.cfg', output.getvalue())
    atomic_text(data / 'scripts' / 'halveth_console_smoke.lua', PLAYER)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'PLAYER: scripts/halveth_console_smoke.lua\n')
    atomic_text(data / 'bridge' / 'inbox.json', '{}\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(prepared['stdout_log'])
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                   stdout=stream, stderr=subprocess.STDOUT)
        try:
            exit_code = process.wait(timeout=35)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            exit_code = 'TIMEOUT'
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result = {
        'scope': 'Fresh isolated OpenMW at 1280x720: one native F8 launcher, real book context, typed citizen command routing, no personal saves or model request required.',
        'exitCode': exit_code,
        'errors': [line for line in lines if ' E]' in line or 'Lua error' in line],
        'markers': [line for line in lines if 'HALVETH_CONSOLE_' in line],
        'log': str(log),
    }
    result['passed'] = (exit_code == 0 and not result['errors']
                        and any('HALVETH_CONSOLE_PASS' in line for line in result['markers']))
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
