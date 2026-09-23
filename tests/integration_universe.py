"""Native character/inventory/spell/encounter integration, isolated fresh world."""
import argparse
import configparser
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_profile import prepare,default_install,atomic_text

GLOBAL=r'''local world=require('openmw.world')
local types=require('openmw.types')
return {eventHandlers={HALVETH_UniverseFixtures=function(data)
    for _,family in ipairs({'Weapon','Armor','Potion','Ingredient','Apparatus','Miscellaneous','Clothing','Light','Lockpick','Probe','Repair'}) do
        for _,record in pairs(types[family].records) do
            if record.name~='' then
                world.createObject(record.id,1):moveInto(types.Actor.inventory(data.player));break
            end
        end
    end
end}}
'''

PLAYER=r'''local core=require('openmw.core')
local types=require('openmw.types')
local self=require('openmw.self')
local I=require('openmw.interfaces')
local C=require('scripts.halveth.common')
local started,phase,done,content,spellId=nil,0,false,nil,nil
local counts={}
local function finish(ok,text)
    done=true;print('HALVETH_UNIVERSE_'..(ok and 'PASS' or 'FAIL')..' '..text);core.quit()
end
local function step(t)
    local u=I.HALVETHUniverse
    assert(u,'Universe interface absent')
    if phase==0 and t>2 then
        phase=1
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='both',requestId='universe-books'})
        core.sendGlobalEvent('HALVETH_UniverseFixtures',{player=self.object})
    elseif phase==1 and t>4 and content then
        phase=2
        u.open('character')
        local s=u.getState();assert(s.panelOpen and s.entryCount==28,'Character +27 skills missing')
        assert(s.detail:find('ATTRIBUTE',1,true),'Native character attributes missing')
        counts.skills=s.entryCount-1
        u.selectTab('inventory');s=u.getState();assert(s.entryCount>=17,'Fixture inventory missing')
        counts.inventory=s.entryCount
        local families={}
        for _,entry in ipairs(s.entries) do
            assert(u.select(entry.id),'Cannot select inventory entry')
            local details=u.getState().detail
            assert(details:find('Basiswert',1,true),'Native item explanation failed: '..entry.title)
            families[entry.category]=true
        end
        counts.itemFamilies=0;for _ in pairs(families) do counts.itemFamilies=counts.itemFamilies+1 end
        assert(counts.itemFamilies==12,'Not all inventory families inspected')
        u.search('NO_SUCH_ITEM_050');assert(u.getState().filteredCount==0,'Search did not filter')
        u.search('');assert(u.getState().filteredCount==counts.inventory,'Search did not restore inventory')
        u.selectTab('magic');s=u.getState();assert(s.entryCount>=3,'Native spells absent')
        spellId=content.spells[1].recordId;assert(u.select(spellId),'Cannot select learned LOVE')
        assert(u.getState().detail:find('Selbst',1,true),'Effect range description absent')
        assert(u.perform(),'Native spell selection failed')
    elseif phase==2 and t>5 then
        phase=3
        assert(types.Actor.getSelectedSpell(self).id==spellId,'Engine selected spell mismatch')
        u.selectTab('nearby');local s=u.getState();assert(s.entryCount>0,'No native encounter in tradehouse')
        counts.actors=s.entryCount
        local target=s.entries[1].id;u.select(target);assert(u.perform(),'Cannot begin selected NPC conversation')
        assert(I.HALVETH.getContext().npc.id==target,'NPC conversation targeted another actor')
        assert(not u.getState().panelOpen,'Universe panel did not close for conversation')
        I.HALVETH.close()
    elseif phase==3 and t>6 then
        phase=4
        I.UI.addMode('Interface',{windows={'Inventory'}})
        u.open('inventory')
    elseif phase==4 and t>7 then
        phase=5
        u.close();assert(I.UI.getMode()=='Interface','Closing panel removed original inventory')
        I.UI.removeMode('Interface')
    elseif phase==5 and t>8 then
        phase=6
        u.open('inventory')
        local inventory=types.Actor.inventory(self)
        local book=inventory:find(content.books[1].recordId)
        assert(book and u.select(book.id),'Native book absent from panel')
        assert(u.perform(),'Native reader did not open')
    elseif phase==6 and t>9 then
        phase=7
        assert(I.UI.getMode()=='Book','Native Book mode absent')
        assert(I.HALVETHKnowledge.getState().bookCount>=1,'Knowledge did not receive native reading event')
        I.UI.removeMode('Book')
        finish(true,C.json(counts))
    end
    if t>35 then finish(false,'phase timeout '..phase) end
end
return {eventHandlers={HALVETH_ContentResult=function(data)
    if data.requestId=='universe-books' then assert(data.success,data.message);content=data end
end},engineHandlers={onFrame=function()
    if done or not self.cell then return end
    if not started then started=core.getRealTime() end
    local ok,err=pcall(step,core.getRealTime()-started)
    if not ok then finish(false,tostring(err)) end
end}}
'''

def run(preview=False):
    state=ROOT/'.local'/'universe-integration'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    r=prepare(argparse.Namespace(install_root=default_install(),state_dir=state,source_profile='max',
        profile='beauty',smoke=True,copy_saves=False,reset_settings=True))
    profile=Path(r['profile_dir']);data=profile/'data'
    cfg=configparser.ConfigParser(interpolation=None);cfg.read(profile/'settings.cfg',encoding='utf-8-sig')
    cfg['Video']['window mode']='0';cfg['Video']['minimize on focus loss']='false'
    settings=io.StringIO();cfg.write(settings);atomic_text(profile/'settings.cfg',settings.getvalue())
    player=PLAYER
    if preview:
        player=PLAYER.replace("finish(true,C.json(counts))","u.open('inventory');print('HALVETH_UNIVERSE_PREVIEW '..C.json(counts))")
        player=player.replace("if t>35 then finish(false,'phase timeout '..phase) end","if t>180 then finish(true,C.json(counts)) end")
    atomic_text(data/'scripts/halveth_genesis_smoke.lua',player)
    atomic_text(data/'scripts/halveth_universe_fixtures.lua',GLOBAL)
    atomic_text(data/'halveth-genesis-smoke.omwscripts','PLAYER: scripts/halveth_genesis_smoke.lua\nGLOBAL: scripts/halveth_universe_fixtures.lua\n')
    atomic_text(data/'bridge/inbox.json','{}\n')
    r['command'][-1]="Seyda Neen, Arrille's Tradehouse"
    log=Path(r['stdout_log'])
    files=['mod/scripts/halveth/'+name+'.lua' for name in ('universe','inspect','player','knowledge')]
    result={'recordedAt':datetime.now(timezone.utc).isoformat(),'scope':'Fresh native Morrowind, actual inventory/spell/menu/encounter APIs. Personal saves excluded.',
        'testedFiles':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},'preview':preview}
    with log.open('w',encoding='utf-8') as output:
        p=subprocess.Popen(r['command'],cwd=r['cwd'],stdout=output,stderr=subprocess.STDOUT)
        print(json.dumps({'pid':p.pid,'state':str(state)}),flush=True)
        try: result['exitCode']=p.wait(timeout=220 if preview else 60)
        except subprocess.TimeoutExpired:
            p.terminate();p.wait(timeout=10);result['exitCode']='TIMEOUT'
    lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
    result['errors']=[x for x in lines if ' E]' in x or 'Lua error' in x or 'HALVETH_UNIVERSE_DESCRIBE' in x or 'HALVETH_UNIVERSE_COLLECT' in x]
    result['markers']=[x for x in lines if 'HALVETH_UNIVERSE_' in x]
    result['passed']=result['exitCode']==0 and not result['errors'] and any('HALVETH_UNIVERSE_PASS' in x for x in lines)
    result['personalSavesUsed']=False
    atomic_text(state/'result.json',json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result['passed'] else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true')
    raise SystemExit(run(parser.parse_args().preview))
