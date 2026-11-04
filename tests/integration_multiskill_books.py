"""Verify study credits in a fresh native OpenMW character, without personal saves."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import default_install
from tests.integration_content import run


NATIVE_TEST = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local started,phase,at,finished=nil,'start',nil,false
local ids={}
local cases={
    {key='ink-between-stars',skill='enchant',use='Enchant_Recharge',mode='Book'},
    {key='three-supports',skill='armorer',use='Armorer_Repair',mode='Book'},
    {key='council-journal',skill='speechcraft',use='Speechcraft_Success',mode='Book'},
}
local index=1
local function move(next)
    phase=next;at=core.getRealTime()
end
local function finish(ok,message)
    if finished then return end
    finished=true
    print('HALVETH_CONTENT_'..(ok and 'PASS' or 'FAIL')..' multiSkill '..message)
    core.quit()
end
local function tick()
    if finished or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now;at=now end
    if now-started>45 then error('Timeout at '..phase) end
    if phase=='start' and now-at>1 then
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='library',requestId='multiskill-books'})
        move('content')
    elseif phase=='open' then
        local case=cases[index]
        if not case then finish(true,'enchant=PASS armorer=PASS speechcraft=PASS oneTime=PASS mismatchedUse=PASS');return end
        local object=types.Actor.inventory(self):find(ids[case.key])
        assert(object,'Native book absent: '..case.key)
        I.UI.addMode('Interface',{windows={'Inventory'}})
        I.UI.addMode(case.mode,{target=object})
        move('read')
    elseif phase=='read' and now-at>0.4 then
        local case=cases[index]
        local id=ids[case.key]
        assert(I.HALVETHKnowledge.getState().books[id],'Book not observed: '..case.key)
        assert(I.HALVETHKnowledge.study(id),'Study rejected: '..case.key)
        I.UI.removeMode(case.mode);I.UI.removeMode('Interface')
        local uses=I.SkillProgression.SKILL_USE_TYPES
        local wrong=case.skill=='speechcraft' and uses.Speechcraft_Fail or 999
        I.SkillProgression.skillUsed(case.skill,{useType=wrong,skillGain=1})
        assert(not I.HALVETHKnowledge.getState().books[id].spent,'Wrong use consumed credit')
        local stat=types.NPC.stats.skills[case.skill](self)
        local before=stat.progress
        local requirement=I.SkillProgression.getSkillProgressRequirement(case.skill)
        I.SkillProgression.skillUsed(case.skill,{useType=uses[case.use],skillGain=1})
        local state=I.HALVETHKnowledge.getState()
        assert(state.books[id].spent and state.lastPractice.bookId==id and state.lastPractice.skill==case.skill,
            'Native practice did not consume matching book: '..case.skill)
        assert(math.abs(state.lastPractice.final-1.05)<0.00001,'Expected 5 percent practice bonus')
        assert(math.abs(stat.progress-before-1.05/requirement)<0.0001,
            'Modified gain did not reach native skill progress: '..case.skill)
        I.SkillProgression.skillUsed(case.skill,{useType=uses[case.use],skillGain=1})
        assert(I.HALVETHKnowledge.getState().lastPractice.percent==0,'Credit repeated: '..case.skill)
        index=index+1
        move('open')
    end
end
return {eventHandlers={HALVETH_ContentResult=function(data)
    if data.requestId~='multiskill-books' then return end
    local ok,err=pcall(function()
        assert(data.success,data.message)
        for _,book in ipairs(data.books) do ids[book.key]=book.recordId end
        for _,case in ipairs(cases) do assert(ids[case.key],'Missing book: '..case.key) end
        move('open')
    end)
    if not ok then finish(false,tostring(err)) end
end},engineHandlers={onFrame=function()
    local ok,err=pcall(tick)
    if not ok then finish(false,tostring(err)) end
end}}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root', type=Path, default=default_install())
    parser.add_argument('--state-dir', type=Path)
    args = parser.parse_args()
    state = args.state_dir or ROOT / '.local/multiskill-integration' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    result = run(args.install_root.resolve(), state.resolve(), native_test=NATIVE_TEST,
                 scope='Fresh OpenMW character: native book readers, studied credits, actual skill progress for enchanting, repair and speechcraft. Disposable profile and no personal saves.')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
