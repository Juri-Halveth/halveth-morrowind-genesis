"""Exercise ordinary native LOVE/AEGIS casting in a fresh disposable character.

The fixture lowers only its new character's health and supplies enough magicka.
It selects spells, enters spell stance and presses the native one-frame use
control. It does not force active effects or bypass the engine's casting path.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.integration_content import run
from scripts.prepare_profile import default_install


CAST_TEST = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local I=require('openmw.interfaces')
local started,phase,at,finished=nil,0,nil,false
local ids,healthBefore,magickaBefore,loveHealth,loveMana={},nil,nil,nil,nil
local function finish(success,message)
    if finished then return end
    finished=true
    self.controls.use=self.ATTACK_TYPE.NoAttack
    I.Controls.overrideCombatControls(false)
    print('HALVETH_CONTENT_'..(success and 'PASS' or 'FAIL')..' nativeCast '..message)
    core.quit()
end
local function received(data)
    if finished or data.requestId~='cast-spells' then return end
    local ok,err=pcall(function()
        assert(data.success and data.knownSpells==3,'Native spell grant failed')
        for _,spell in ipairs(data.spells) do ids[spell.key]=spell.recordId end
        assert(ids.love and ids.aegis,'Missing requested native spell IDs')
        I.UI.setMode()
        I.Controls.overrideCombatControls(true)
        types.Actor.stats.dynamic.health(self).current=1
        local magicka=types.Actor.stats.dynamic.magicka(self)
        magicka.current=math.max(24,magicka.base+magicka.modifier)
        types.Actor.setSelectedSpell(self,core.magic.spells.records[ids.love])
        phase=2;at=core.getRealTime()
    end)
    if not ok then finish(false,tostring(err)) end
end
local function tick()
    if finished or not self.cell then return end
    local now=core.getRealTime()
    if not started then started=now end
    if now-started>40 then error('Cast test timed out in phase '..phase) end
    if phase==0 and now-started>=2 then
        phase=1
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='spells',requestId='cast-spells'})
    elseif phase==2 and now-at>=1 then
        -- Selection reaches the player's native UI asynchronously. The engine
        -- rejects spell stance until that selection is present in the UI.
        types.Actor.setStance(self,types.Actor.STANCE.Spell)
        phase=2.5;at=now
    elseif phase==2.5 and now-at>=1 then
        assert(types.Actor.getStance(self)==types.Actor.STANCE.Spell,'Spell stance was not entered')
        healthBefore=types.Actor.stats.dynamic.health(self).current
        magickaBefore=types.Actor.stats.dynamic.magicka(self).current
        assert(magickaBefore>=20,'Fixture does not have enough actual magicka')
        self.controls.use=self.ATTACK_TYPE.Any
        phase=3;at=now
    elseif phase==3 then
        self.controls.use=self.ATTACK_TYPE.NoAttack
        if now-at>=4 then
            loveHealth=types.Actor.stats.dynamic.health(self).current
            loveMana=types.Actor.stats.dynamic.magicka(self).current
            print('HALVETH_CONTENT_CAST_OBSERVATION health='..loveHealth..' before='..healthBefore..' mana='..loveMana..' beforeMana='..magickaBefore..' stance='..tostring(types.Actor.getStance(self))..' selected='..tostring(types.Actor.getSelectedSpell(self))..' mode='..tostring(I.UI.getMode()))
            assert(loveHealth>healthBefore+1,'LOVE did not restore health through native casting')
            assert(math.abs(magickaBefore-loveMana-8)<0.1,'LOVE did not consume exactly 8 magicka')
            print('HALVETH_CONTENT_LOVE healthBefore='..healthBefore..' healthAfter='..loveHealth..' magickaBefore='..magickaBefore..' magickaAfter='..loveMana)
            types.Actor.setSelectedSpell(self,core.magic.spells.records[ids.aegis])
            phase=4;at=now
        end
    elseif phase==4 and now-at>=1 then
        self.controls.use=self.ATTACK_TYPE.Any
        phase=5;at=now
    elseif phase==5 then
        self.controls.use=self.ATTACK_TYPE.NoAttack
        if now-at>=3 then
            local shield=types.Actor.activeEffects(self):getEffect('shield').magnitude
            local mana=types.Actor.stats.dynamic.magicka(self).current
            assert(math.abs(shield-20)<0.1,'AEGIS did not produce native shield20')
            assert(types.Actor.activeSpells(self):isSpellActive(ids.aegis),'AEGIS not recorded as active native spell')
            assert(math.abs(loveMana-mana-12)<0.1,'AEGIS did not consume exactly 12 magicka')
            print('HALVETH_CONTENT_AEGIS shield='..shield..' magickaBefore='..loveMana..' magickaAfter='..mana)
            finish(true,'LOVE_health_restoration=PASS LOVE_cost8=PASS AEGIS_shield20=PASS AEGIS_cost12=PASS directActiveEffectInjection=false animationVisualReview=false')
        end
    end
end
return {eventHandlers={HALVETH_ContentResult=received},engineHandlers={onFrame=function()
    local ok,err=pcall(tick)
    if not ok then finish(false,tostring(err)) end
end}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-root", type=Path, default=default_install())
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    state = args.state_dir or ROOT / ".local/cast-integration" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    scope = "Actual OpenMW native casting via selected spell, spell stance and one-frame use control on a fresh disposable Vivec character. LOVE health increase and exact 8-magicka consumption; AEGIS native shield20, active spell and exact 12-magicka consumption. No direct active-effect injection, no personal save, no physical-input or animation screenshot claim."
    result = run(args.install_root.resolve(), state.resolve(), native_test=CAST_TEST, scope=scope)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
