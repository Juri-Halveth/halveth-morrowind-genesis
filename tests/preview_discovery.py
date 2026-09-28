"""Capture the actual Arrille discovery route in an isolated OpenMW process."""
from __future__ import annotations

import argparse
import configparser
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare

PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local nearby=require('openmw.nearby')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local started,scene,reader=false,false,false
return {engineHandlers={onFrame=function()
    if not self.cell or self.cell.name~="Seyda Neen, Arrille's Tradehouse" then return end
    if not started then started=core.getRealTime() end
    local t=core.getRealTime()-started
    if t>2 and not scene then
        scene=true
        assert(not I.HALVETHOrigin.getState().armed,'Forced intro choice appeared')
        assert(I.UI.getMode()~='Interface','Extra intro panel appeared')
        print('HALVETH_DISCOVERY_PREVIEW_SCENE')
    end
    if t>8 and not reader then
        for _,item in ipairs(nearby.items) do
            if item:isValid() and types.Book.objectIsInstance(item) and
                types.Book.record(item).name=='HALVETH: Stille Zeichen am Rand' then
                I.UI.addMode('Scroll',{target=item})
                reader=true
                print('HALVETH_DISCOVERY_PREVIEW_READER')
                break
            end
        end
    end
    if t>20 then print('HALVETH_DISCOVERY_PREVIEW_DONE');core.quit() end
end}}
'''


class Rect(ctypes.Structure):
    _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                ('right', wintypes.LONG), ('bottom', wintypes.LONG)]


def process_window(pid: int):
    user32 = ctypes.windll.user32
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def inspect(hwnd, _data):
        actual = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(actual))
        if actual.value == pid and user32.IsWindowVisible(hwnd):
            rect = Rect()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)) and rect.right-rect.left > 400:
                found.append((hwnd, rect))
        return True

    user32.EnumWindows(callback_type(inspect), 0)
    return max(found, key=lambda item: (item[1].right-item[1].left)
               * (item[1].bottom-item[1].top)) if found else None


def capture(pid: int, path: Path) -> None:
    result = process_window(pid)
    if result is None:
        raise RuntimeError('No visible window belongs to this OpenMW test process.')
    hwnd, rect = result
    user32 = ctypes.windll.user32
    user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wintypes.UINT)
    user32.ShowWindow(hwnd, 9)
    flags = 0x0001 | 0x0002 | 0x0040  # keep position/size, show window
    if not user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, flags):
        raise RuntimeError('Could not raise the isolated OpenMW window for capture.')
    try:
        time.sleep(.5)
        shot = ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom))
        if max(channel[1] for channel in shot.convert('RGB').getextrema()) < 80:
            raise RuntimeError('OpenMW capture is black; visual verification failed.')
        shot.save(path)
    finally:
        user32.SetWindowPos(hwnd, wintypes.HWND(-2), 0, 0, 0, 0, flags)


def main() -> int:
    if sys.platform != 'win32':
        raise RuntimeError('Process-bound visual capture requires Windows.')
    state = ROOT / '.local' / 'discovery-preview' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='beauty', smoke=True, copy_saves=False, reset_settings=True))
    profile = Path(prepared['profile_dir'])
    settings = configparser.ConfigParser(interpolation=None)
    settings.read(profile/'settings.cfg', encoding='utf-8-sig')
    settings['Video'].update({'window mode':'0', 'resolution x':'1600',
                              'resolution y':'900', 'minimize on focus loss':'false'})
    stream = io.StringIO()
    settings.write(stream)
    atomic_text(profile/'settings.cfg', stream.getvalue())
    data = profile/'data'
    atomic_text(data/'scripts/halveth_discovery_preview.lua',PLAYER)
    atomic_text(data/'halveth-genesis-smoke.omwscripts',
                'PLAYER: scripts/halveth_discovery_preview.lua\n')
    script_run = state/'discovery-console.txt'
    atomic_text(script_run,'coc "Seyda Neen, Arrille\'s Tradehouse"\n')
    command = prepared['command'][:-2]+['--new-game=1','--script-run',str(script_run)]
    log = Path(prepared['stdout_log'])
    engine_log = Path(prepared['engine_log'])
    screenshots = {'scene':state/'arrille-scene.png', 'reader':state/'clue-book-reader.png'}
    process = None
    try:
        with log.open('w',encoding='utf-8') as output:
            process = subprocess.Popen(command,cwd=prepared['cwd'],stdout=output,
                                       stderr=subprocess.STDOUT)
            for stage,marker in [('scene','HALVETH_DISCOVERY_PREVIEW_SCENE'),
                                 ('reader','HALVETH_DISCOVERY_PREVIEW_READER')]:
                until = time.monotonic()+26
                while time.monotonic()<until and process.poll() is None:
                    if engine_log.is_file() and marker in engine_log.read_text(encoding='utf-8',errors='replace'):
                        time.sleep(.4)
                        capture(process.pid,screenshots[stage])
                        break
                    time.sleep(.2)
                else:
                    raise RuntimeError('Native preview marker missing: '+marker)
            code = process.wait(timeout=20)
        lines = engine_log.read_text(encoding='utf-8',errors='replace').splitlines()
        errors = [line for line in lines if ' E]' in line or 'Lua error' in line]
        passed = code==0 and not errors and all(path.is_file() for path in screenshots.values())
        receipt = {'passed':passed,'processId':process.pid,'exitCode':code,
                   'screenshots':{k:str(v) for k,v in screenshots.items()},
                   'markers':[line for line in lines if 'HALVETH_DISCOVERY_PREVIEW_' in line],
                   'errors':errors,'personalSavesUsed':False,
                   'scope':'Only the visible window belonging to the disposable OpenMW PID was captured. A test coc bypassed manual vanilla character creation.'}
        atomic_text(state/'result.json',json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(receipt,indent=2,ensure_ascii=False))
        return 0 if passed else 1
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__=='__main__':
    raise SystemExit(main())
