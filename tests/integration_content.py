"""Exercise native OpenMW books/spells in a fresh disposable Vivec scene.

No existing save is loaded or written. Only the test-owned engine process is
terminated on timeout. This test opens a real game window; run deliberately.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import atomic_text, default_install, prepare


NATIVE_TEST = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local catalog=require('scripts.halveth.content_catalog')
local started,sent,finished,first=nil,false,false,nil
local function finish(success,message)
    if finished then return end
    finished=true
    print('HALVETH_CONTENT_'..(success and 'PASS' or 'FAIL')..' '..message)
    core.quit()
end
local function validate(data)
    assert(data.success, data.message)
    assert(data.inventoryBooks==6 and data.knownSpells==3,'Unexpected native inventory/spells')
    assert(#data.books==6 and #data.spells==3,'Missing record mappings')
    for i,book in ipairs(catalog.books) do
        local actual=data.books[i]
        assert(actual.key==book.key and actual.skill==book.skill,'Wrong book identity')
        local record=types.Book.records[actual.recordId]
        assert(record and record.name==book.title,'Native BOOK record missing')
        assert(record.model~='' and record.icon~='','Native book asset paths missing')
        assert(record.isScroll==book.isScroll,'Wrong native reader type')
        for _,page in ipairs(book.pages) do
            assert(record.text:find(page.text,1,true),'Authored text missing from native book')
        end
        assert(types.Actor.inventory(self):countOf(actual.recordId)==1,'Duplicate or missing native book')
        if first then assert(first.books[i].recordId==actual.recordId,'Record identity changed on repeat') end
    end
    for i,spell in ipairs(catalog.spells) do
        local actual=data.spells[i]
        local record=core.magic.spells.records[actual.recordId]
        assert(actual.key==spell.key and actual.known,'Spell mapping missing')
        assert(types.Actor.spells(self)[actual.recordId],'Native learned spell missing')
        assert(record and record.name==spell.title and record.cost==spell.cost,'Wrong native spell')
        assert(record.type==core.magic.SPELL_TYPE.Spell and record.alwaysSucceedFlag,'Wrong spell mode')
        assert(#record.effects==#spell.effects,'Wrong native effects length')
        for k,effect in ipairs(spell.effects) do
            local e=record.effects[k]
            assert(e.id==effect.id and e.range==core.magic.RANGE[effect.range],'Wrong effect or range')
            assert(e.duration==effect.duration and e.area==effect.area,'Wrong duration or area')
            assert(e.magnitudeMin==effect.magnitudeMin and e.magnitudeMax==effect.magnitudeMax,'Wrong native magnitude')
        end
        if first then assert(first.spells[i].recordId==actual.recordId,'Spell identity changed on repeat') end
    end
end
local function received(data)
    if finished or (data.requestId~='content-first' and data.requestId~='content-repeat') then return end
    local ok,err=pcall(validate,data)
    if not ok then finish(false,tostring(err));return end
    if not first then
        first=data
        print('HALVETH_CONTENT_FIRST books=6 passages=15 spells=3 nativeRecordChecks=PASS')
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='both',requestId='content-repeat'})
    else
        finish(true,'books=6 passages=15 spells=3 inventoryDuplicateCheck=PASS stableRecordIds=PASS nativeEffects=restorehealth,shockdamage,shield')
    end
end
return {eventHandlers={HALVETH_ContentResult=received},engineHandlers={onFrame=function()
    if finished or not self.cell then return end
    if not started then started=core.getRealTime() end
    local elapsed=core.getRealTime()-started
    if elapsed>=2 and not sent then
        sent=true
        core.sendGlobalEvent('HALVETH_ContentRequest',{player=self.object,request='both',requestId='content-first'})
    end
    if elapsed>35 then finish(false,'Timeout waiting for native content event') end
end}}
'''


def run(install_root: Path, state_dir: Path, *, native_test: str = NATIVE_TEST, scope: str | None = None) -> dict:
    args = argparse.Namespace(install_root=install_root, state_dir=state_dir,
                              source_profile="max", profile="original", smoke=True,
                              copy_saves=False, reset_settings=True)
    receipt = prepare(args)
    profile = Path(receipt["profile_dir"])
    data = profile / "data"
    atomic_text(data / "scripts/halveth_genesis_smoke.lua", native_test)
    atomic_text(data / "bridge/inbox.json", '{}\n')
    # Use the normal manifest if integration is present, otherwise add only our
    # GLOBAL script to this isolated VFS overlay. Never mutate the main manifest.
    manifest = (ROOT / "mod/halveth.omwscripts").read_text(encoding="utf-8")
    if "scripts/halveth/content.lua" not in manifest:
        manifest += "\nGLOBAL: scripts/halveth/content.lua\n"
    atomic_text(data / "halveth.omwscripts", manifest)
    log_path = Path(receipt["stdout_log"])
    result = {
        "recordedAt": datetime.now(timezone.utc).isoformat(), "passed": False,
        "scope": scope or "Actual OpenMW, fresh Vivec, six native BOOK records containing fifteen own passages, three native learned SPEL records and exact effect parameters, repeated grant has one copy and stable IDs. No existing save loaded or written; no physical-input or rendering assertion.",
        "profileDir": str(profile), "log": str(log_path),
        "harnessLuaSHA256": hashlib.sha256(native_test.encode("utf-8")).hexdigest(),
        "sourceConfigSHA256": receipt["source_config_sha256"],
        "sourceSettingsSHA256": receipt["source_settings_sha256"],
        "testedFiles": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            "mod/scripts/halveth/content.lua", "mod/scripts/halveth/content_catalog.lua", "data/native-content.json")},
    }
    process = None
    try:
        with log_path.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(receipt["command"], cwd=receipt["cwd"], stdout=output,
                                       stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            result["pid"] = process.pid
            result["exitCode"] = process.wait(timeout=90)
        text = log_path.read_text(encoding="utf-8", errors="replace")
        result["markers"] = [line for line in text.splitlines() if "HALVETH_CONTENT_" in line]
        result["errors"] = [line for line in text.splitlines() if " E]" in line or "Lua error" in line]
        result["passed"] = result["exitCode"] == 0 and any("HALVETH_CONTENT_PASS" in x for x in result["markers"]) and not result["errors"]
        result["testSaveFiles"] = [str(p.relative_to(profile)) for p in profile.rglob("*.omwsave")]
        if result["testSaveFiles"]:
            result["passed"] = False
        source = install_root / "profiles/max"
        result["originalSettingsPreserved"] = all(hashlib.sha256((source / name).read_bytes()).hexdigest() == result[key]
                                                   for name, key in (("openmw.cfg", "sourceConfigSHA256"), ("settings.cfg", "sourceSettingsSHA256")))
        result["passed"] = result["passed"] and result["originalSettingsPreserved"]
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        atomic_text(state_dir / "result.json", json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-root", type=Path, default=default_install())
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    state = args.state_dir or ROOT / ".local/content-integration" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    result = run(args.install_root.resolve(), state.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
