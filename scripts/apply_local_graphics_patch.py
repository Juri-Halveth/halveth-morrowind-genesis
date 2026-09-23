"""Copy already-owned local graphics packs into an installed Genesis game.

This is a private installation helper. It never downloads or redistributes
third-party assets, touches the original game files, or overwrites saves.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--installed-app", type=Path, required=True)
    args = parser.parse_args()
    source_manifest = args.source_manifest.resolve(strict=True)
    source_root = source_manifest.parent
    installed_app = args.installed_app.resolve(strict=True)
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    if source.get("schemaVersion") != 1 or not isinstance(source.get("dataDirectories"), list):
        raise ValueError("Expected a graphics schemaVersion 1 manifest")
    if not (installed_app / "scripts" / "prepare_profile.py").is_file():
        raise FileNotFoundError("Installed Genesis app is missing its profile helper")
    if source_root == installed_app / ".local" / "graphics":
        raise ValueError("Source and destination graphics roots must differ")

    graphics = installed_app / ".local" / "graphics"
    installed_manifest = graphics / "install.json"
    if installed_manifest.exists():
        raise FileExistsError(f"Existing installed graphics manifest requires manual review: {installed_manifest}")
    graphics.mkdir(parents=True, exist_ok=True)
    mapped = []
    copied_files = 0
    copied_bytes = 0
    for raw in source["dataDirectories"]:
        origin = Path(raw).resolve(strict=True)
        if not origin.is_dir() or not origin.is_relative_to(source_root):
            raise ValueError(f"Graphics directory escapes the selected source: {origin}")
        relative = origin.relative_to(source_root)
        target = graphics / relative
        if target.exists():
            raise FileExistsError(f"Destination already exists: {target}")
        shutil.copytree(origin, target)
        source_files = sorted(path for path in origin.rglob("*") if path.is_file())
        target_files = sorted(path for path in target.rglob("*") if path.is_file())
        if len(source_files) != len(target_files):
            raise OSError(f"Copy count differs: {relative}")
        for original in source_files:
            copy = target / original.relative_to(origin)
            if digest(original) != digest(copy):
                raise OSError(f"Copied graphics file differs: {relative / original.relative_to(origin)}")
            copied_files += 1
            copied_bytes += original.stat().st_size
        mapped.append(str(target))

    updated = dict(source)
    updated["dataDirectories"] = mapped
    updated["recordedAt"] = datetime.now(timezone.utc).isoformat()
    installed_manifest.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"installedManifest": str(installed_manifest), "copiedFiles": copied_files,
                      "copiedBytes": copied_bytes, "directoryCount": len(mapped)}, indent=2))


if __name__ == "__main__":
    main()
