"""Open a fresh native visual field with the installed OpenMW engine.

No existing character is loaded and the normal game profile is unchanged.
"""
from pathlib import Path
import argparse
import configparser
import io
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_profile import prepare,atomic_text
from scripts.visual_field import build,CELL


def assess(text, code):
    """Require observed movement and growth, not just a successful engine exit."""
    errors=[line for line in text.splitlines()
            if any(x in line for x in [' E]','Lua error','Failed to compile','ERROR:'])]
    markers=[line for line in text.splitlines() if 'HALVETH_FIELD_' in line]
    motion={}
    stages=set()
    for line in markers:
        match=re.search(r'HALVETH_FIELD_MOTION slot=(\d+) distance=([\d.eE+-]+)',line)
        if match:
            slot=int(match[1])
            motion[slot]=max(motion.get(slot,0),float(match[2]))
        match=re.search(r'HALVETH_FIELD_GROWTH stage=(\d+)',line)
        if match:stages.add(int(match[1]))
    checks={
        'engineExitedCleanly':code==0 and not errors,
        'sixteenObjectsCreated':any('objects=16 ' in line for line in markers),
        'allGrowthStagesObserved':{1,2,3,4}.issubset(stages),
        'threeActorsCrossedInitialSpacing':all(motion.get(slot,0)>2200 for slot in (1,2,3)),
        'durationCompleted':any('HALVETH_FIELD_DONE' in line for line in markers),
    }
    return {'recordedAt':datetime.now(timezone.utc).isoformat(),'exitCode':code,
        'passed':all(checks.values()),'checks':checks,
        'maxObservedDisplacement':motion,'errors':errors,'markers':markers,
        'scope':'Fresh isolated native field; no saved character loaded. Movement belongs to generated study actors.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root',type=Path,required=True)
    parser.add_argument('--graphics-manifest',type=Path,required=True)
    parser.add_argument('--tag',default='visual-field')
    parser.add_argument('--duration',type=int,default=90)
    parser.add_argument('--interactive',action='store_true',
        help='Leave the native field open without a timer; does not change the ordinary play profile.')
    args=parser.parse_args()
    if not re.fullmatch('[a-zA-Z0-9_-]{1,50}',args.tag):parser.error('Invalid tag')
    if not 40<=args.duration<=240:parser.error('Duration must be 40..240')
    duration=0 if args.interactive else args.duration
    state=ROOT/'.local/graphics/checks'/args.tag
    if state.exists():raise FileExistsError('Use a fresh tag to retain previous results')
    field=state/'field'
    build(field)
    receipt=prepare(argparse.Namespace(install_root=args.install_root,state_dir=state,
        source_profile='max',profile='beauty',smoke=True,copy_saves=False,
        reset_settings=True,graphics_manifest=args.graphics_manifest))
    profile=Path(receipt['profile_dir'])
    configpath=profile/'openmw.cfg'
    text=configpath.read_text(encoding='utf-8')
    text=text.replace('content=halveth-genesis-smoke.omwscripts','')
    text+='\ndata="'+str(field).replace('\\','/')+'"\ncontent=HALVETH-Visual-Field.esp\ncontent=halveth-visual-field.omwscripts\n'
    atomic_text(configpath,text)
    player=field/'scripts/halveth_visual_field/player.lua'
    atomic_text(player,player.read_text(encoding='utf-8').replace('local duration=0 -- FIELD_DURATION',f'local duration={duration} -- FIELD_DURATION'))
    build_receipt=field/'field-receipt.json'
    bound=json.loads(build_receipt.read_text(encoding='utf-8'))
    for f in bound['files']:
        f['sha256']=hashlib.sha256((field/f['file']).read_bytes()).hexdigest()
    bound['qaDuration']=duration
    atomic_text(build_receipt,json.dumps(bound,indent=2))
    config=configparser.ConfigParser(interpolation=None)
    config.read(profile/'settings.cfg',encoding='utf-8')
    config['Video'].update({'resolution x':'2560','resolution y':'1440','window mode':'2',
        'vsync mode':'0','framerate limit':'120','minimize on focus loss':'false'})
    # The development interior has no exterior sun; do not ask shadow cascades
    # to track a static aerial camera in this particular profile.
    config['Shadows']['enable shadows']='false'
    buf=io.StringIO();config.write(buf);atomic_text(profile/'settings.cfg',buf.getvalue())
    uniforms=json.loads((profile/'shaders.yaml').read_text(encoding='utf-8'))
    uniforms['config']['ssao']['cfg_intensity']=.75
    uniforms['config']['ssao']['cfg_radius']=18
    uniforms['config']['halveth_storybook']={'uStrength':.35,'uSurfaceSoftness':.25,'uRadius':1,'uColor':.05}
    uniforms['config']['lucinet_world']={'uStrength':.15}
    atomic_text(profile/'shaders.yaml',json.dumps(uniforms,indent=2))
    receipt['command'][-1]=CELL
    atomic_text(state/'launch.json',json.dumps(receipt,indent=2))
    logfile=Path(receipt['stdout_log'])
    with logfile.open('w',encoding='utf-8') as log:
        proc=subprocess.Popen(receipt['command'],cwd=receipt['cwd'],stdout=log,stderr=subprocess.STDOUT)
        launch={'pid':proc.pid,'profile':str(profile),'duration':duration,
                'interactive':args.interactive,'normalProfileChanged':False}
        atomic_text(state/'active.json',json.dumps(launch,indent=2))
        print(json.dumps(launch),flush=True)
        if args.interactive:return
        try:code=proc.wait(timeout=args.duration+70)
        except subprocess.TimeoutExpired:
            proc.terminate();proc.wait(timeout=10);code='TIMEOUT'
    text=logfile.read_text(encoding='utf-8',errors='replace')
    result=assess(text,code)
    atomic_text(state/'result.json',json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
