"""Apply the owned 1.0.1 native menu patch to an existing Genesis install.

The installed launcher is retained. Existing packaged files must match the
installer manifest before they can be replaced; game data and saves are never
opened. A byte-for-byte rollback copy is kept under app/.local/patches/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
CHANGED = (
    "app/mod/halveth.omwscripts",
    "app/mod/scripts/halveth/visuals.lua",
    "app/scripts/graphics_profile.py",
)
ADDED = (
    "app/mod/scripts/halveth/menu_portal.lua",
    "app/mod/Textures/halveth/portal-menu-2100.png",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_path(root: Path, relative: str) -> Path:
    path = root.joinpath(*relative.split("/"))
    if not path.resolve(strict=False).is_relative_to(root):
        raise ValueError("Patch path escapes installation: " + relative)
    return path


def apply(installed: Path) -> dict:
    installed = installed.resolve(strict=True)
    if installed.is_symlink() or (hasattr(installed, "is_junction") and installed.is_junction()):
        raise ValueError("Installation root must not be a link")
    state_path = installed / "install-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    if state.get("version") != "1.0.0" or state.get("mode") not in ("local-engine", "owned-mod"):
        raise ValueError("Expected an unpatched Genesis 1.0.0 installation")
    records = {record["path"]: record for record in state["files"]}
    source = {}
    for relative in CHANGED + ADDED:
        source_path = checked_path(ROOT, relative.removeprefix("app/"))
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        source[relative] = source_path
        target = checked_path(installed, relative)
        if relative in CHANGED:
            if relative not in records or not target.is_file():
                raise ValueError("Expected installed file missing: " + relative)
            if target.stat().st_size != records[relative]["bytes"] or sha256(target) != records[relative]["sha256"]:
                raise ValueError("Installed file was changed independently: " + relative)
        elif target.exists() or relative in records:
            raise FileExistsError("New patch file already exists: " + relative)

    backup = installed / "app" / ".local" / "patches" / "1.0.1-before-portal"
    if backup.exists():
        raise FileExistsError("Existing patch backup requires review: " + str(backup))
    backup.mkdir(parents=True)
    written = []
    try:
        for relative in CHANGED:
            original = checked_path(installed, relative)
            copy = backup / relative
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, copy)
            if sha256(copy) != sha256(original):
                raise OSError("Backup differs: " + relative)
        shutil.copy2(state_path, backup / "install-state.json")
        for relative in CHANGED + ADDED:
            target = checked_path(installed, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            staged = target.with_name(target.name + ".patching")
            shutil.copy2(source[relative], staged)
            if sha256(staged) != sha256(source[relative]):
                raise OSError("Staged patch differs: " + relative)
            os.replace(staged, target)
            written.append(relative)
            record = {"path": relative, "sha256": sha256(target), "bytes": target.stat().st_size}
            if relative in records:
                records[relative].update(record)
            else:
                state["files"].append(record)
        state["version"] = "1.0.1"
        staged_state = state_path.with_name("install-state.json.patching")
        staged_state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(staged_state, state_path)
    except Exception:
        for relative in reversed(written):
            target = checked_path(installed, relative)
            if relative in CHANGED:
                shutil.copy2(backup / relative, target)
            else:
                target.unlink(missing_ok=True)
        shutil.copy2(backup / "install-state.json", state_path)
        raise
    receipt = {"status": "PATCHED", "version": "1.0.1", "installed": str(installed),
               "changed": list(CHANGED), "added": list(ADDED), "backup": str(backup),
               "installedFiles": len(state["files"])}
    (backup / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", type=Path, required=True)
    print(json.dumps(apply(parser.parse_args().installed), indent=2))
