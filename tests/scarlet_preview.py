"""Prepare or run a disposable native LOVE-tapestry and F8 image scene.

Uses a fresh Suran Temple scene, isolated state, no personal save and automatic
quit. --run opens the real engine for external screenshot inspection. The
receipt checks VFS header/object/UI lifecycle; visual quality is checked apart.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_profile import prepare, default_install, atomic_text

CELL = "Suran, Suran Temple"
PLAYER = r'''local core=require('openmw.core')
local self=require('openmw.self')
local camera=require('openmw.camera')
local util=require('openmw.util')
local vfs=require('openmw.vfs')
local interfaces=require('openmw.interfaces')
local started,target,opened,done=nil,nil,false,false
return {eventHandlers={HALVETH_ScarletTarget=function(data) target=data end},
engineHandlers={onFrame=function()
    if done or not self.cell then return end
    local now=core.getRealTime()
    if not started then
        started=now
        local file=vfs.open('textures/tx_de_tapestry_02.tga')
        local header=file and file:read(18) or ''
        if file then file:close() end
        local w,h=0,0
        if #header==18 then
            w=header:byte(13)+256*header:byte(14)
            h=header:byte(15)+256*header:byte(16)
        end
        print('HALVETH_SCARLET_VFS path=textures/tx_de_tapestry_02.tga width='..w..' height='..h..' png='..tostring(vfs.fileExists('textures/halveth/scarlet-love-banner.png')))
        local dds=vfs.open('textures/tx_de_tapestry_02.dds')
        local dh=dds and dds:read(128) or ''
        local bytes=dds and dds:seek('end') or 0
        if dds then dds:close() end
        local function u32(s,i) return s:byte(i)+256*s:byte(i+1)+65536*s:byte(i+2)+16777216*s:byte(i+3) end
        local dw,dhh=0,0
        if #dh==128 and dh:sub(1,4)=='DDS ' then dw=u32(dh,17);dhh=u32(dh,13) end
        print('HALVETH_SCARLET_DDS path=textures/tx_de_tapestry_02.dds width='..dw..' height='..dhh..' bytes='..bytes)
    end
    if target then
        camera.setMode(camera.MODE.Static,true)
        camera.setStaticPosition(target.position+util.transform.rotateZ(target.yaw)*util.vector3(0,320,-110))
        camera.setYaw(target.yaw+math.pi)
        camera.setPitch(0)
        camera.showCrosshair(false)
    end
    local elapsed=now-started
    if elapsed>=UI_AFTER and not opened then
        interfaces.HALVETH.open();opened=true
        print('HALVETH_SCARLET_UI_OPEN')
    end
    if elapsed>=DURATION then
        done=true
        print('HALVETH_SCARLET_DONE target='..tostring(target~=nil)..' ui='..tostring(opened))
        core.quit()
    end
end}}
'''
GLOBAL = r'''local world=require('openmw.world')
local util=require('openmw.util')
local found=false
return {engineHandlers={onUpdate=function()
    if found or #world.players==0 or not world.players[1].cell then return end
    local player=world.players[1]
    local expected=util.vector3(221.199081,-480.061127,99.223228)
    for _,object in ipairs(player.cell:getAll()) do
        if object.recordId=='furn_de_tapestry_02' and (object.position-expected):length()<2 then
            found=true
            world.setGameTimeScale(0)
            player:sendEvent('HALVETH_ScarletTarget',{position=object.position,yaw=object.rotation:getYaw()})
            print('HALVETH_SCARLET_OBJECT record='..object.recordId..' id='..tostring(object.id)..' cell='..player.cell.name..' position='..tostring(object.position))
            break
        end
    end
end}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Launch this isolated, self-closing native preview.")
    parser.add_argument("--duration", type=int, default=100)
    parser.add_argument("--ui-after", type=int, default=45)
    parser.add_argument("--profile", choices=("beauty", "cinematic"), default="beauty")
    args = parser.parse_args()
    if not 60 <= args.duration <= 180 or not 10 <= args.ui_after < args.duration - 10:
        parser.error("duration must be 60..180; ui-after must leave at least 10 seconds of native UI.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    state = ROOT / ".local/graphics/checks" / ("scarlet-" + stamp)
    receipt = prepare(argparse.Namespace(install_root=default_install(), state_dir=state,
        source_profile="max", profile=args.profile, smoke=True, copy_saves=False, reset_settings=True))
    profile = Path(receipt["profile_dir"])
    atomic_text(profile / "data/scripts/halveth_genesis_smoke.lua",
                PLAYER.replace("UI_AFTER", str(args.ui_after)).replace("DURATION", str(args.duration)))
    atomic_text(profile / "data/scripts/halveth_scarlet_scene.lua", GLOBAL)
    atomic_text(profile / "data/halveth-genesis-smoke.omwscripts",
                "PLAYER: scripts/halveth_genesis_smoke.lua\nGLOBAL: scripts/halveth_scarlet_scene.lua\n")
    receipt["command"][-1] = CELL
    # The reusable smoke helper ends in --start Vivec; replace only that value.
    assert receipt["command"][-2] == "--start"
    png = ROOT / "mod/Textures/halveth/scarlet-love-banner.png"
    tga = ROOT / ".local/graphics/ScarletLoveBanner/Textures/Tx_de_tapestry_02.tga"
    dds = ROOT / ".local/graphics/ScarletLoveBanner/Textures/Tx_de_tapestry_02.dds"
    expected_width, expected_height = struct.unpack_from("<HH", tga.read_bytes()[:18], 12)
    receipt["scarletPreview"] = {"cell": CELL, "recordId": "furn_de_tapestry_02", "sourceRefnum": 352021,
        "durationSeconds": args.duration, "uiOpensAfterSeconds": args.ui_after,
        "tgaSha256": hashlib.sha256(tga.read_bytes()).hexdigest(),
        "ddsSha256": hashlib.sha256(dds.read_bytes()).hexdigest(),
        "expectedDdsBytes": dds.stat().st_size,
        "expectedTextureDimensions": [expected_width, expected_height],
        "pngSha256": hashlib.sha256(png.read_bytes()).hexdigest(),
        "scope": "Fresh world only. Native object, VFS header and F8 lifecycle; screenshot quality checked separately."}
    atomic_text(state / "preview.json", json.dumps(receipt, indent=2))
    if args.run:
        log_path = Path(receipt["stdout_log"])
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(receipt["command"], cwd=receipt["cwd"], stdout=log, stderr=subprocess.STDOUT)
            receipt.update({"launched": True, "pid": process.pid})
            atomic_text(state / "preview.json", json.dumps(receipt, indent=2))
            print(json.dumps({"pid": process.pid, "receipt": str(state / "preview.json"), "uiAfter": args.ui_after,
                              "autoQuitAfter": args.duration}), flush=True)
            try:
                exit_code = process.wait(timeout=args.duration + 60)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
                exit_code = "TIMEOUT"
        text = log_path.read_text(encoding="utf-8", errors="replace")
        markers = [line for line in text.splitlines() if "HALVETH_SCARLET_" in line]
        errors = [line for line in text.splitlines() if " E]" in line or "Lua error" in line]
        expected_vfs = f"HALVETH_SCARLET_VFS path=textures/tx_de_tapestry_02.tga width={expected_width} height={expected_height} png=true"
        expected_dds = f"HALVETH_SCARLET_DDS path=textures/tx_de_tapestry_02.dds width={expected_width} height={expected_height} bytes={dds.stat().st_size}"
        passed = exit_code == 0 and not errors and any(expected_vfs in line for line in markers) and any(expected_dds in line for line in markers) and any("HALVETH_SCARLET_OBJECT" in line for line in markers) and any(
            "HALVETH_SCARLET_DONE target=true ui=true" in line for line in markers)
        receipt["nativeResult"] = {"passed": passed, "exitCode": exit_code, "markers": markers, "errors": errors}
        atomic_text(state / "preview.json", json.dumps(receipt, indent=2))
        print(json.dumps(receipt["nativeResult"], indent=2))
        return 0 if passed else 1
    print(json.dumps({"prepared": True, "receipt": str(state / "preview.json"), "command": receipt["command"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
