#!/usr/bin/env python3
"""Prepare and optionally launch a separate OpenMW Genesis profile.

Original game data, settings and saves are read-only inputs. No Bethesda assets
are copied into this project. Python standard library only, Windows or Linux.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

if __package__:
    from .graphics_profile import GRAPHICS_SECTIONS, load_graphics_manifest, recommendations, resolve_shaders, resolve_visual_plugins
else:
    from graphics_profile import GRAPHICS_SECTIONS, load_graphics_manifest, recommendations, resolve_shaders, resolve_visual_plugins

PROJECT = Path(__file__).resolve().parents[1]


def default_install() -> Path:
    # Packaged desktop apps can redirect LOCALAPPDATA into their own cache.
    # Prefer the user's actual installation before trying that app-local path.
    relative = Path("HALVETH/Morrowind-Native/0.2.0")
    candidates = []
    if os.name == "nt":
        candidates.append(Path.home() / "AppData" / "Local" / relative)
    candidates.append(Path(os.environ.get("LOCALAPPDATA", "~/.local/share")).expanduser() / relative)
    # A prepared local receipt retains the resolved installation path so a
    # later desktop launch outside the packaged app can find the same engine.
    hint = PROJECT / ".local" / "profiles" / "beauty" / "launch.json"
    try:
        previous = json.loads(hint.read_text(encoding="utf-8"))
        candidates.append(Path(previous["engine"]).parent.parent)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return next((candidate for candidate in candidates if (candidate / "engine").is_dir()), candidates[0])


DEFAULT_INSTALL = default_install()


def quoted(path: Path) -> str:
    return '"' + str(path.resolve()).replace("\\", "/").replace("&", "&&").replace('"', '&"') + '"'


def parse_entries(path: Path) -> list[tuple[str, str]]:
    result = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result.append((key.strip(), value.strip()))
    return result


def source_path(value: str, relative_to: Path) -> Path:
    value = value.strip('"').replace('&"', '"').replace("&&", "&")
    if "?" in value:
        raise ValueError(f"Unresolved OpenMW path token in source profile: {value}")
    candidate = Path(value)
    return (candidate if candidate.is_absolute() else relative_to / candidate).resolve()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".new")
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.{suffix}.bak")
    shutil.copy2(path, backup)
    if digest(backup) != digest(path):
        raise OSError(f"Settings backup verification failed: {backup}")
    return str(backup)


def prepare(args: argparse.Namespace) -> dict:
    install = args.install_root.expanduser().resolve()
    state = args.state_dir.expanduser().resolve()
    profile_name = args.profile + ("-smoke" if args.smoke else "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", args.profile):
        raise ValueError("Profile name must use 1-48 ASCII letters, digits, underscore or hyphen.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", args.source_profile):
        raise ValueError("Source profile name must use 1-48 ASCII letters, digits, underscore or hyphen.")
    if args.smoke and args.copy_saves:
        raise ValueError("Smoke mode always uses a fresh game; omit --copy-saves.")
    if state == install or install in state.parents:
        raise ValueError("State directory must be outside the original installation.")
    source = install / "profiles" / args.source_profile
    source_cfg = source / "openmw.cfg"
    source_settings = source / "settings.cfg"
    exe_name = "openmw.exe" if os.name == "nt" else "openmw"
    engine = install / "engine" / exe_name
    mod = PROJECT / "mod"
    # OpenMW indexes VFS names at startup; the mailbox must exist before launch.
    inbox = mod / "bridge" / "inbox.json"
    if not inbox.exists():
        atomic_text(inbox, '{"sequence":0,"sessionId":""}\n')
    for required in (source_cfg, source_settings, engine, mod / "halveth.omwscripts"):
        if not required.is_file():
            raise FileNotFoundError(f"Required local input missing: {required}")
    profile = state / "profiles" / profile_name
    user_data = profile / "user"
    extra_data = profile / "data"
    user_data.mkdir(parents=True, exist_ok=True)
    extra_data.mkdir(parents=True, exist_ok=True)
    entries = parse_entries(source_cfg)
    original_paths = [source_path(value, source) for key, value in entries if key == "data"]
    for data in original_paths:
        if not data.is_dir():
            raise FileNotFoundError(f"Original data directory is unavailable: {data}")
    graphics = load_graphics_manifest(PROJECT, state, getattr(args, "graphics_manifest", None)) if args.profile != "original" else {
        "path": None, "sha256": None, "directories": [], "shaders": [], "visual_plugins": []}
    graphics_paths = [p for p in graphics["directories"] if p not in original_paths and p != mod.resolve()]
    shader_files = resolve_shaders([install / "engine" / "resources" / "vfs", *original_paths, *graphics_paths, mod, extra_data],
                                  graphics["shaders"])
    scenic, uniforms = recommendations(args.profile, graphics["shaders"])
    visual_plugins = resolve_visual_plugins(graphics_paths, graphics["visual_plugins"], [mod, extra_data])
    original_content = {value.strip('"').casefold() for key, value in entries if key == "content"}
    if any(plugin["file"].casefold() in original_content for plugin in visual_plugins):
        raise ValueError("A visual plugin is already present in the original content list; no duplicate added.")
    config_lines = [
        "# Genesis isolated profile; base assets remain external read-only inputs.",
        "replace=config", "replace=content", "replace=fallback-archive", "replace=data",
        "resources=" + quoted(install / "engine" / "resources"),
        "data=" + quoted(install / "engine" / "resources" / "vfs-mw"),
        "user-data=" + quoted(user_data), "data-local=" + quoted(extra_data),
    ]
    for key, value in entries:
        if key == "data":
            config_lines.append("data=" + quoted(source_path(value, source)))
        elif key not in {"config", "replace", "resources", "data-local", "user-data"}:
            config_lines.append(f"{key}={value}")
    config_lines += ["data=" + quoted(directory) for directory in graphics_paths]
    config_lines += ["data=" + quoted(mod)]
    config_lines += ["content=" + plugin["file"] for plugin in visual_plugins]
    config_lines += ["content=halveth.omwscripts"]
    settings_file = profile / "settings.cfg"
    settings_existed = settings_file.is_file()
    apply_settings = not settings_existed or args.smoke or args.reset_settings
    settings = configparser.ConfigParser(interpolation=None, strict=True)
    # Explicit graphics resets preserve this profile's gameplay/audio/input/UI.
    # A fresh profile inherits them from the source profile, which stays untouched.
    settings.read(settings_file if settings_existed else source_settings, encoding="utf-8-sig")
    if apply_settings:
        for section, values in scenic.items():
            if not settings.has_section(section):
                settings.add_section(section)
            settings[section].update(values)
    if args.smoke:
        for section in ("Video", "Sound"):
            if not settings.has_section(section):
                settings.add_section(section)
        settings["Video"].update({"window mode": "2", "resolution x": "1280", "resolution y": "720",
                                  "minimize on focus loss": "false", "framerate limit": "60"})
        settings["Sound"]["master volume"] = "0"
        config_lines.append("content=halveth-genesis-smoke.omwscripts")
        atomic_text(extra_data / "halveth-genesis-smoke.omwscripts", "PLAYER: scripts/halveth_genesis_smoke.lua\n")
        atomic_text(extra_data / "scripts" / "halveth_genesis_smoke.lua", SMOKE_LUA)
    atomic_text(profile / "openmw.cfg", "\n".join(config_lines) + "\n")
    # Re-preparing must retain personal changes made within the new profile.
    settings_backup = None
    shader_backup = None
    shader_settings_file = profile / "shaders.yaml"
    if apply_settings:
        import io
        output = io.StringIO()
        settings.write(output)
        settings_backup = backup_file(settings_file)
        atomic_text(settings_file, output.getvalue())
        if args.profile in {"beauty", "cinematic"}:
            shader_backup = backup_file(shader_settings_file)
            atomic_text(shader_settings_file, json.dumps({"config": uniforms}, indent=2) + "\n")
        elif not shader_settings_file.exists() and (source / "shaders.yaml").is_file():
            shutil.copy2(source / "shaders.yaml", shader_settings_file)
    copied_saves = []
    if args.copy_saves:
        source_user_values = [value for key, value in entries if key == "user-data"]
        if not source_user_values:
            raise ValueError("Source profile has no user-data path.")
        source_saves = source_path(source_user_values[-1], source) / "saves"
        if not source_saves.is_dir():
            raise FileNotFoundError(f"Source save directory not found: {source_saves}")
        for save in source_saves.rglob("*.omwsave"):
            target = user_data / "saves" / save.relative_to(source_saves)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(save, target)
                if digest(save) != digest(target):
                    raise OSError(f"Save-copy verification failed: {target}")
                copied_saves.append(str(target))
    command = [str(engine), "--replace", "config", "--config", str(profile), "--no-grab"]
    if args.smoke:
        command.extend(["--skip-menu", "--start", "Vivec"])
    receipt = {
        "recorded_at": datetime.now(timezone.utc).isoformat(), "profile": profile_name,
        "profile_dir": str(profile), "state_dir": str(state), "project_dir": str(PROJECT),
        "user_data": str(user_data), "engine": str(engine), "cwd": str(engine.parent),
        "source_profile": str(source), "source_config_sha256": digest(source_cfg),
        "source_settings_sha256": digest(source_settings), "source_data_dirs": [str(p) for p in original_paths],
        "mod_dir": str(mod), "inbox": str(mod / "bridge" / "inbox.json"),
        "stdout_log": str(profile / "openmw.stdout.log"), "engine_log": str(profile / "openmw.log"),
        "command": command, "copied_saves": copied_saves, "launched": False,
        "graphics": {"preset": args.profile, "manifest": graphics["path"], "manifest_sha256": graphics["sha256"],
                     "data_directories": [str(p) for p in graphics_paths], "requested_shaders": graphics["shaders"],
                     "shader_files": shader_files,
                     "visual_plugins": visual_plugins,
                     "active_shaders": [name.strip() for name in settings.get("Post Processing", "chain", fallback="").split(",") if name.strip()]
                         if settings.getboolean("Post Processing", "enabled", fallback=False) else [],
                     "applied": apply_settings, "settings_preserved": not apply_settings,
                     "settings_backup": settings_backup, "shader_settings_backup": shader_backup,
                     "settings_file": str(settings_file), "shader_settings_file": str(shader_settings_file),
                     "effective_settings": {section: dict(settings[section]) for section in GRAPHICS_SECTIONS if settings.has_section(section)},
                     "recommended_settings": scenic, "recommended_uniforms": uniforms,
                     "warnings": [] if apply_settings else ["Existing settings preserved; use --reset-settings to apply current graphics recommendations with backups."],
                     "validation": "Configuration prepared; shader compilation, visuals and framerate require a native game run."},
    }
    atomic_text(profile / "launch.json", json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    return receipt


SMOKE_LUA = r'''local core = require('openmw.core')
local self = require('openmw.self')
local types = require('openmw.types')
local started, before = nil, nil
local sent, opened, repeated, closed, damaged, healed, finished = false, false, false, false, false, false, false
return {engineHandlers = {onFrame = function()
    if finished then return end
    if not self.cell then return end
    if not started then started = core.getRealTime() end
    local elapsed = core.getRealTime() - started
    local inventory = types.Actor.inventory(self)
    if elapsed >= 2 and before == nil then before = inventory:countOf('gold_001') end
    if elapsed >= 3 and not sent then
        sent = true
        self:sendEvent('HALVETH_TestRequest', {id='smoke-gold-once', kind='give_gold', params={amount=250}})
    end
    if elapsed >= 4 and not opened then opened = true; self:sendEvent('HALVETH_TestOpen', {}) end
    if elapsed >= 5 and not repeated then
        repeated = true
        self:sendEvent('HALVETH_TestRequest', {id='smoke-gold-once', kind='give_gold', params={amount=250}})
    end
    if elapsed >= 6 and not closed then closed = true; self:sendEvent('HALVETH_TestOpen', {}) end
    if elapsed >= 7 and not damaged then damaged = true; types.Actor.stats.dynamic.health(self).current = 1 end
    if elapsed >= 8 and not healed then
        healed = true
        self:sendEvent('HALVETH_TestRequest', {id='smoke-heal-once', kind='heal_player', params={}})
    end
    if elapsed >= 11 then
        finished = true
        local after = inventory:countOf('gold_001')
        local health = types.Actor.stats.dynamic.health(self)
        local healedFully = health.current >= health.base + health.modifier - .01
        local status = (before ~= nil and after == before + 250 and healedFully) and 'PASS' or 'FAIL'
        print('HALVETH_SMOKE_' .. status .. ' before=' .. tostring(before) .. ' after=' .. tostring(after) .. ' delta=' .. tostring(after-(before or 0)) .. ' health=' .. tostring(health.current) .. ' healthMax=' .. tostring(health.base + health.modifier) .. ' duplicateIdSent=' .. tostring(repeated) .. ' uiOpenAndCloseSent=' .. tostring(opened and closed) .. ' cell=' .. tostring(self.cell.name))
        core.quit()
    end
end}}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-root", type=Path, default=default_install())
    parser.add_argument("--state-dir", type=Path, default=PROJECT / ".local")
    parser.add_argument("--source-profile", default="max")
    parser.add_argument("--profile", choices=("original", "beauty", "cinematic"), default="beauty")
    parser.add_argument("--copy-saves", action="store_true", help="Copy .omwsave files once into the separate profile, never overwrite.")
    parser.add_argument("--reset-settings", action="store_true", help="Back up this Genesis profile's settings and apply current graphics recommendations; preserve gameplay/audio/input/UI.")
    parser.add_argument("--graphics-manifest", type=Path, help="Use an explicit schemaVersion 1 graphics-install manifest; relative dataDirectories resolve from project root.")
    parser.add_argument("--launch", action="store_true", help="Launch the prepared profile and return its PID.")
    parser.add_argument("--smoke", action="store_true", help="Run a fresh disposable Vivec scene, verify +250 gold, then exit.")
    parser.add_argument("--timeout", type=int, default=90, help="Smoke timeout in seconds.")
    args = parser.parse_args()
    if args.timeout < 15 or args.timeout > 300:
        parser.error("--timeout must be between 15 and 300 seconds")
    try:
        receipt = prepare(args)
        result_code = 0
        if args.launch or args.smoke:
            stdout_path = Path(receipt["stdout_log"])
            if stdout_path.exists():
                suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                stdout_path.rename(stdout_path.with_name(f"openmw.stdout.{suffix}.log"))
            with stdout_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(receipt["command"], cwd=receipt["cwd"], stdout=log, stderr=subprocess.STDOUT)
                receipt.update({"launched": True, "pid": process.pid})
                if args.smoke:
                    try:
                        exit_code = process.wait(timeout=args.timeout)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        exit_code = "TIMEOUT"
                    log.flush()
                    text = stdout_path.read_text(encoding="utf-8", errors="replace")
                    markers = [line for line in text.splitlines() if "HALVETH_SMOKE_" in line]
                    errors = [line for line in text.splitlines() if " E]" in line or "Lua error" in line]
                    passed = exit_code == 0 and any("HALVETH_SMOKE_PASS" in line for line in markers) and not errors
                    receipt["smoke"] = {"passed": passed, "exit_code": exit_code, "markers": markers, "errors": errors,
                                        "scope": "Fresh isolated Vivec scene, real +250 gold, repeated action id deduplication, health restoration, UI open/close without Lua errors. No production save loaded or written; no sustained benchmark or visual screenshot QA."}
                    result_code = 0 if passed else 1
            atomic_text(Path(receipt["profile_dir"]) / "launch.json", json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return result_code
    except (OSError, ValueError, configparser.Error) as exc:
        print(f"Genesis profile preparation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
