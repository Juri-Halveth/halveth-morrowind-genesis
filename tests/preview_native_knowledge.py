"""Disposable native Morrowind scene for visual and physical-input QA."""
import argparse
import configparser
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import prepare, default_install, atomic_text

LUA = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')
local started,requested,opened,panel,done=nil,false,false,false,false
local result
return {eventHandlers={HALVETH_ContentResult=function(data)
    if data.requestId=='native-visual-books' then result=data end
end},engineHandlers={onFrame=function()
    if done or not self.cell then return end
    if not started then started=core.getRealTime() end
    local t=core.getRealTime()-started
    if t>2 and not requested then
        requested=true
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='both',requestId='native-visual-books'})
    end
    if t>4 and result and result.success and not opened then
        opened=true
        local object=types.Actor.inventory(self):find(result.books[1].recordId)
        I.UI.addMode('Book',{target=object})
        print('HALVETH_NATIVE_VISUAL_BOOK '..result.books[1].title)
    end
    if t>10 and opened and not panel then
        panel=true
        I.UI.removeMode('Book')
        I.HALVETHKnowledge.open()
        print('HALVETH_NATIVE_VISUAL_PANEL '..C.json(I.HALVETHKnowledge.getState()))
    end
    if t>180 then done=true;print('HALVETH_NATIVE_VISUAL_DONE');core.quit() end
end}}
'''

def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    state=ROOT/'.local'/'native-visual'/stamp
    prepared=prepare(argparse.Namespace(install_root=default_install(),state_dir=state,
        source_profile='max',profile='beauty',smoke=True,copy_saves=False,reset_settings=True))
    profile=Path(prepared['profile_dir'])
    settings=configparser.ConfigParser(interpolation=None)
    settings.read(profile/'settings.cfg',encoding='utf-8-sig')
    settings['Video']['window mode']='0'
    out=io.StringIO();settings.write(out)
    atomic_text(profile/'settings.cfg',out.getvalue())
    atomic_text(profile/'data/scripts/halveth_genesis_smoke.lua',LUA)
    log_path=Path(prepared['stdout_log'])
    with log_path.open('w',encoding='utf-8') as log:
        p=subprocess.Popen(prepared['command'],cwd=prepared['cwd'],stdout=log,stderr=subprocess.STDOUT)
        prepared['pid']=p.pid
        atomic_text(state/'preview.json',json.dumps(prepared,indent=2))
        print(json.dumps({'pid':p.pid,'receipt':str(state/'preview.json'),'duration':180}),flush=True)
        try: code=p.wait(timeout=210)
        except subprocess.TimeoutExpired:
            p.terminate();p.wait(timeout=10);code='TIMEOUT'
    text=log_path.read_text(encoding='utf-8',errors='replace')
    errors=[x for x in text.splitlines() if ' E]' in x or 'Lua error' in x]
    result={'exitCode':code,'errors':errors,'markers':[x for x in text.splitlines() if 'HALVETH_NATIVE_VISUAL_' in x],
            'scope':'Fresh native Morrowind window for separate screenshot/input inspection, no personal saves.'}
    atomic_text(state/'result.json',json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return 0 if code==0 and not errors else 1

if __name__=='__main__':
    raise SystemExit(main())
