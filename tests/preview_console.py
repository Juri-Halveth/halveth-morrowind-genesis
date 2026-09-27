"""Capture the actual native F8 window from this test's own OpenMW process.

Windows visual QA only. Uses a fresh disposable profile and no personal save.
"""
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
local I=require('openmw.interfaces')
local started,opened=nil,false
return {engineHandlers={onFrame=function()
    if not self.cell then return end
    if not started then started=core.getRealTime() end
    local elapsed=core.getRealTime()-started
    if elapsed>3 and not opened then
        if I.HALVETHMicrophone and I.HALVETHMicrophone.isOpen() then
            I.HALVETHMicrophone.decline()
        end
        if I.HALVETHOrigin and I.HALVETHOrigin.getState().armed then
            I.HALVETHOrigin.select('journey')
        end
        if I.HALVETH then I.HALVETH.open() end
        opened=true
        print('HALVETH_PREVIEW_CONSOLE_READY')
    end
    if elapsed>20 then print('HALVETH_PREVIEW_CONSOLE_DONE');core.quit() end
end}}
'''


class RECT(ctypes.Structure):
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
            rect = RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)) and rect.right-rect.left > 400:
                found.append((hwnd, rect))
        return True

    user32.EnumWindows(callback_type(inspect), 0)
    return max(found, key=lambda item: (item[1].right-item[1].left)
               * (item[1].bottom-item[1].top)) if found else None


def run() -> int:
    if sys.platform != 'win32':
        raise RuntimeError('Process-bound native capture requires Windows.')
    state = ROOT / '.local' / 'visual-qa' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    prepared = prepare(argparse.Namespace(install_root=default_install(), state_dir=state,
        source_profile='max', profile='beauty', smoke=True, copy_saves=False,
        reset_settings=True))
    profile = Path(prepared['profile_dir'])
    settings = configparser.ConfigParser(interpolation=None)
    settings.read(profile / 'settings.cfg', encoding='utf-8-sig')
    settings['Video'].update({'window mode': '0', 'resolution x': '1600',
                              'resolution y': '900', 'minimize on focus loss': 'false'})
    stream = io.StringIO()
    settings.write(stream)
    atomic_text(profile / 'settings.cfg', stream.getvalue())
    data = profile / 'data'
    atomic_text(data / 'scripts/halveth_console_visual.lua', PLAYER)
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'PLAYER: scripts/halveth_console_visual.lua\n')
    atomic_text(data / 'bridge/inbox.json', '{}\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(prepared['stdout_log'])
    screenshot = state / 'console.png'
    process = None
    try:
        with log.open('w', encoding='utf-8') as output:
            process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                       stdout=output, stderr=subprocess.STDOUT)
            ready = False
            until = time.monotonic() + 16
            while time.monotonic() < until and process.poll() is None:
                if 'HALVETH_PREVIEW_CONSOLE_READY' in log.read_text(encoding='utf-8', errors='replace'):
                    ready = True
                    break
                time.sleep(.25)
            if not ready:
                raise RuntimeError('F8 did not report ready in the disposable game.')
            time.sleep(1)
            window = process_window(process.pid)
            if window is None:
                raise RuntimeError('No visible OpenMW window belongs to the launched PID.')
            hwnd, rect = window
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(.5)
            if ctypes.windll.user32.GetForegroundWindow() != hwnd:
                raise RuntimeError('The bound OpenMW window did not reach the foreground.')
            ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save(screenshot)
            code = process.wait(timeout=20)
        errors = [line for line in log.read_text(encoding='utf-8', errors='replace').splitlines()
                  if ' E]' in line or 'Lua error' in line]
        receipt = {'passed': code == 0 and not errors and screenshot.is_file(),
                   'processId': process.pid, 'screenshot': str(screenshot),
                   'errors': errors, 'personalSavesUsed': False}
        atomic_text(state / 'result.json', json.dumps(receipt, indent=2))
        print(json.dumps(receipt, indent=2))
        return 0 if receipt['passed'] else 1
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    raise SystemExit(run())
