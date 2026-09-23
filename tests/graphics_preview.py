"""Isolated fixed-view graphics check, with optional close-up and time of day.

Fresh character only. Prints frame-callback timing, not a GPU benchmark. Native
scene and shader errors are recorded. Never opens or writes an existing save.
"""
from pathlib import Path
import argparse, configparser, io, json, re, subprocess, sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_profile import prepare,default_install,atomic_text

PLAYER=r'''local core=require('openmw.core')
local self=require('openmw.self')
local camera=require('openmw.camera')
local util=require('openmw.util')
local nearby=require('openmw.nearby')
local interfaces=require('openmw.interfaces')
local started,previous,position=nil,nil,nil
local frames,total,worst,over33=0,0,0,0
local done,opened=false,false
return {engineHandlers={onFrame=function()
    if not self.cell or done then return end
    local now=core.getRealTime()
    if not started then started=now end
    local t=now-started
    if SHOW_UI and t>=12 and not opened then
        interfaces.HALVETH.open();opened=true
    end
    local yaw,pitch=0.70,0.35
    if PORTRAIT ~= '' then
        for _,actor in ipairs(nearby.actors) do
            if actor.recordId == PORTRAIT then
                yaw=actor.rotation:getYaw()+math.pi;pitch=0
                position=actor.position+util.transform.rotateZ(actor.rotation:getYaw())*util.vector3(0,140,135)
                break
            end
        end
    end
    if not position then position=self.position+util.vector3(-2200,-3700,2200) end
    camera.setMode(camera.MODE.Static,true)
    camera.setStaticPosition(position)
    camera.setYaw(yaw)
    camera.setPitch(pitch)
    camera.showCrosshair(false)
    if previous and t>=10 and t<35 then
        local dt=now-previous
        frames=frames+1;total=total+dt;worst=math.max(worst,dt)
        if dt>0.033333 then over33=over33+1 end
    end
    previous=now
    if t>=35 and frames>0 then
        print(string.format('HALVETH_GRAPHICS_SAMPLE frames=%d seconds=%.3f meanFps=%.2f worstMs=%.2f over33ms=%d',frames,total,frames/total,worst*1000,over33))
        frames=0
    end
    if t>=DURATION then
        done=true;print('HALVETH_GRAPHICS_DONE cell='..self.cell.name);core.quit()
    end
end}}
'''
GLOBAL=r'''local world=require('openmw.world')
local core=require('openmw.core')
local set=false
return {engineHandlers={onUpdate=function()
    if set or #world.players==0 or not world.players[1].cell then return end
    set=true
    world.mwscript.getGlobalVariables().gamehour=HOUR
    world.setGameTimeScale(0)
    local cell=world.players[1].cell
    if cell.region then core.weather.changeWeather(cell.region,core.weather.records['clear']) end
    print('HALVETH_GRAPHICS_SCENE cell='..cell.name..' hour=HOUR')
end}}
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['original','beauty','cinematic'],default='beauty')
    parser.add_argument('--cell',default='Seyda Neen')
    parser.add_argument('--duration',type=int,default=90)
    parser.add_argument('--tag',default='graphics-check')
    parser.add_argument('--hour',type=float,default=13)
    parser.add_argument('--portrait',default='',help='Nearby NPC record ID for a face-and-shoulders view.')
    parser.add_argument('--ui',action='store_true',help='Open the existing companion UI through its interface after 12 seconds.')
    args=parser.parse_args()
    if not re.fullmatch('[a-zA-Z0-9_-]{1,50}',args.tag):parser.error('Invalid tag')
    if not 40<=args.duration<=240:parser.error('Duration must be 40..240')
    if not 0<=args.hour<24:parser.error('Hour must be 0..<24')
    if not re.fullmatch('[a-zA-Z0-9_ ]{0,80}',args.portrait):parser.error('Invalid NPC ID')
    state=ROOT/'.local/graphics/checks'/args.tag
    receipt=prepare(argparse.Namespace(install_root=default_install(),state_dir=state,
        source_profile='max',profile=args.profile,smoke=True,copy_saves=False,reset_settings=True))
    profile=Path(receipt['profile_dir'])
    atomic_text(profile/'data/scripts/halveth_genesis_smoke.lua',PLAYER.replace('DURATION',str(args.duration)).replace('PORTRAIT',json.dumps(args.portrait)).replace('SHOW_UI',str(args.ui).lower()))
    atomic_text(profile/'data/scripts/halveth_graphics_global.lua',GLOBAL.replace('HOUR',str(args.hour)))
    atomic_text(profile/'data/halveth-genesis-smoke.omwscripts','PLAYER: scripts/halveth_genesis_smoke.lua\nGLOBAL: scripts/halveth_graphics_global.lua\n')
    config=configparser.ConfigParser(interpolation=None)
    config.read(profile/'settings.cfg',encoding='utf-8')
    config['Video'].update({'resolution x':'2560','resolution y':'1440','window mode':'2','vsync mode':'0','framerate limit':'120','minimize on focus loss':'false'})
    buffer=io.StringIO();config.write(buffer);atomic_text(profile/'settings.cfg',buffer.getvalue())
    receipt['command'][-1]=args.cell
    logfile=Path(receipt['stdout_log'])
    atomic_text(state/'launch.json',json.dumps(receipt,indent=2))
    with logfile.open('w',encoding='utf-8') as log:
        process=subprocess.Popen(receipt['command'],cwd=receipt['cwd'],stdout=log,stderr=subprocess.STDOUT)
        print(json.dumps({'pid':process.pid,'profile':args.profile,'log':str(logfile),'duration':args.duration}),flush=True)
        try:code=process.wait(timeout=args.duration+70)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=8);code='TIMEOUT'
    text=logfile.read_text(encoding='utf-8',errors='replace')
    errors=[line for line in text.splitlines() if any(x in line for x in [' E]','Lua error','Failed to compile','ERROR:','Failed to load effect'])]
    markers=[line for line in text.splitlines() if 'HALVETH_GRAPHICS_' in line]
    result={'recordedAt':datetime.now(timezone.utc).isoformat(),'profile':args.profile,'cell':args.cell,'hour':args.hour,'portrait':args.portrait,'ui':args.ui,'resolution':[2560,1440],
        'passed':code==0 and not errors and any('HALVETH_GRAPHICS_DONE' in m for m in markers),'exitCode':code,'errors':errors,'markers':markers,
        'scope':'Fixed fresh scene. Frame-callback intervals over 25 seconds after warmup; not a sustained or GPU benchmark. No existing save loaded.'}
    atomic_text(state/'result.json',json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
