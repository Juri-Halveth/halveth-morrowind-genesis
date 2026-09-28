"""Verify the native consent gate only opens after a deliberate F8 action.

This never starts the Python companion and never opens an audio device.
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
local I=require('openmw.interfaces')
local began,done=nil,false
local function finish(ok,message)
    if done then return end
    done=true
    print('HALVETH_MICROPHONE_'..(ok and 'PASS' or 'FAIL')..' '..message)
    core.quit()
end
return {engineHandlers={onFrame=function()
    if done or not self.cell then return end
    local ok,err=pcall(function()
        if not began then began=core.getRealTime() end
        if core.getRealTime()-began<4 then return end
        local mic=assert(I.HALVETHMicrophone,'Native microphone consent interface missing')
        assert(mic.getState()=='undecided','Microphone was enabled without consent')
        assert(not mic.isOpen(),'New Game opened unsolicited microphone consent')
        local initialMode=I.UI.getMode() -- Another story window may be open.
        I.HALVETH.open()
        assert(I.HALVETH.isOpen(),'F8 console did not open before mic request')
        I.HALVETH.close()
        mic.open()
        assert(mic.isOpen(),'Deliberate microphone request did not open consent')
        assert(I.UI.getMode()=='Interface','Native microphone choice has no focus')
        I.HALVETH.open()
        assert(not I.HALVETH.isOpen(),'F8 console covered the consent choice')
        assert(mic.isOpen(),'Consent was displaced by F8 console')
        mic.decline()
        assert(mic.getState()=='declined','No did not persist for this session')
        assert(not mic.isOpen(),'Consent panel remained visible after No')
        assert(I.UI.getMode()==initialMode,'Consent modal changed the previous UI mode')
        finish(true,'noStartupPrompt=PASS defaultOff=PASS deliberatePrompt=PASS f8Blocked=PASS decline=PASS')
    end)
    if not ok then finish(false,tostring(err)) end
    if began and core.getRealTime()-began>15 then finish(false,'Timeout') end
end}}
'''


def run() -> int:
    state = ROOT / '.local' / 'microphone-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='original', smoke=True, copy_saves=False, reset_settings=True))
    data = Path(prepared['profile_dir']) / 'data'
    atomic_text(data / 'scripts' / 'halveth_microphone_smoke.lua', PLAYER)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'PLAYER: scripts/halveth_microphone_smoke.lua\n')
    prepared['command'][-1] = 'Seyda Neen'
    log = Path(prepared['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Fresh disposable native game: no startup prompt, deliberate F8 permission request, No path; no companion, no microphone process, no personal saves.',
        'testedFiles': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in ('mod/scripts/halveth/microphone.lua', 'mod/halveth.omwscripts')},
        'personalSavesUsed': False,
    }
    with log.open('w', encoding='utf-8') as output:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                   stdout=output, stderr=subprocess.STDOUT)
        try:
            result['exitCode'] = process.wait(timeout=40)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            result['exitCode'] = 'TIMEOUT'
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers'] = [line for line in lines if 'HALVETH_MICROPHONE_' in line]
    result['passed'] = result['exitCode'] == 0 and not result['errors'] and any(
        'HALVETH_MICROPHONE_PASS' in line for line in lines)
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
