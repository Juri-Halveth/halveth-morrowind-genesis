"""Check the original 0.7 LOVE artwork in a disposable native OpenMW window."""
import argparse
import configparser
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare

ART = ROOT / 'mod' / 'Textures' / 'halveth' / 'love-astrolabe-0.7.png'
PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local ui=require('openmw.ui')
local vfs=require('openmw.vfs')
local I=require('openmw.interfaces')
local started,done=nil,false
local path='textures/halveth/love-astrolabe-0.7.png'
local function finish(ok,detail)
    done=true
    print('HALVETH_ART_070_'..(ok and 'PASS' or 'FAIL')..' '..detail)
    core.quit()
end
return {engineHandlers={onFrame=function()
    if done or not self.cell then return end
    if not started then started=core.getRealTime() end
    local elapsed=core.getRealTime()-started
    if elapsed<2 then return end
    local ok,err=pcall(function()
        assert(vfs.fileExists(path),'owned texture not mounted')
        local size=ui.screenSize()
        assert(size.x>=900 and size.y>=550,'test window too small for art')
        local h=I.HALVETH
        assert(h and h.getArtworkPath,'native F8 art interface missing')
        h.open()
        assert(h.isOpen(),'native F8 panel did not open')
        assert(h.getArtworkPath()==path,'native panel selected '..tostring(h.getArtworkPath()))
        h.close()
        assert(h.getArtworkPath()==nil,'closed panel still reports art')
    end)
    finish(ok,ok and 'native F8 selected original PNG and closed cleanly' or tostring(err))
end}}
'''


def run() -> int:
    state = ROOT / '.local' / 'art-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    )
    prepared = prepare(argparse.Namespace(
        install_root=default_install(), state_dir=state, source_profile='max',
        profile='beauty', smoke=True, copy_saves=False, reset_settings=True
    ))
    profile = Path(prepared['profile_dir'])
    data = profile / 'data'
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(profile / 'settings.cfg', encoding='utf-8-sig')
    cfg['Video']['window mode'] = '0'
    cfg['Video']['resolution x'] = '1280'
    cfg['Video']['resolution y'] = '720'
    cfg['Video']['minimize on focus loss'] = 'false'
    settings = io.StringIO()
    cfg.write(settings)
    atomic_text(profile / 'settings.cfg', settings.getvalue())
    atomic_text(data / 'scripts' / 'halveth_art_070_smoke.lua', PLAYER)
    # prepare_profile wires this exact smoke manifest into the isolated profile.
    atomic_text(data / 'halveth-genesis-smoke.omwscripts',
                'PLAYER: scripts/halveth_art_070_smoke.lua\n')
    atomic_text(data / 'bridge' / 'inbox.json', '{}\n')
    prepared['command'][-1] = "Seyda Neen, Arrille's Tradehouse"
    log = Path(prepared['stdout_log'])
    result = {
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Fresh native Morrowind F8 art selection, owned PNG; no personal saves or world-changing actions.',
        'assetSha256': hashlib.sha256(ART.read_bytes()).hexdigest(),
        'playerScriptSha256': hashlib.sha256((ROOT / 'mod/scripts/halveth/player.lua').read_bytes()).hexdigest(),
        'personalSavesUsed': False,
    }
    with log.open('w', encoding='utf-8') as output:
        process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                   stdout=output, stderr=subprocess.STDOUT)
        print(json.dumps({'pid': process.pid, 'state': str(state)}), flush=True)
        try:
            result['exitCode'] = process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
            result['exitCode'] = 'TIMEOUT'
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    result['errors'] = [line for line in lines if ' E]' in line or 'Lua error' in line]
    result['markers'] = [line for line in lines if 'HALVETH_ART_070_' in line]
    result['passed'] = (result['exitCode'] == 0 and not result['errors']
                        and any('HALVETH_ART_070_PASS' in line for line in lines))
    atomic_text(state / 'result.json', json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
