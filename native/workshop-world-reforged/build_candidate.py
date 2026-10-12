#!/usr/bin/env python3
"""Build an isolated local World Reforged workshop candidate.

The builder copies only a locally installed OpenMW runtime. Bethesda game data,
saves, OpenMW binaries, and World Reforged asset packs are never part of this
source repository. The large patch remains at its bound local source and is
verified by the executable before it becomes part of a profile's load order.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
FRAMEWORK = Path("C:/Windows/Microsoft.NET/Framework64/v4.0.30319")
EXPECTED_PLUGIN_SHA256 = "9805d32df3fe67406ddae40e4ef39929d7bc149d7fac04bd462e7a4bf4f71748"
ENGINE_EXCLUSIONS = {"Uninstall.exe"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise ValueError(f"{label} fehlt: {path}")
    if path.is_symlink():
        raise ValueError(f"{label} darf keine Dateiverknüpfung sein: {path}")
    return path


def local_directory(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"{label} ist kein Ordner: {resolved}")
    if str(resolved).startswith("\\\\"):
        raise ValueError(f"{label} darf kein Netzwerkpfad sein: {resolved}")
    for parent in (resolved, *resolved.parents):
        if parent.is_symlink():
            raise ValueError(f"{label} enthält eine Ordnerverknüpfung: {parent}")
    return resolved


def csc_dll() -> Path:
    root = Path("C:/Program Files/dotnet/sdk")
    candidates = sorted(root.glob("*/Roslyn/bincore/csc.dll"))
    if not candidates:
        raise FileNotFoundError("Kein lokaler .NET-Roslyn-Compiler wurde gefunden.")
    return candidates[-1]


def compile_cs(output: Path, sources: list[str], main: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    refs = [
        "mscorlib", "System", "System.Core", "System.Drawing", "System.Windows.Forms",
        "System.Web.Extensions", "Microsoft.CSharp",
    ]
    command = [
        "dotnet", str(csc_dll()), "/nologo", "/noconfig", "/nostdlib+", "/langversion:latest",
        "/target:winexe", "/platform:x64", "/optimize+", "/utf8output",
        f"/main:{main}", f"/out:{output}", f"/win32manifest:{ROOT / 'app.manifest'}",
    ]
    command.extend(f"/reference:{FRAMEWORK / (reference + '.dll')}" for reference in refs)
    command.extend(str(ROOT / source) for source in sources)
    subprocess.run(command, check=True)


def validate_world_reforged(base_patch: Path, overlay: Path) -> dict[str, object]:
    plugin = require_file(base_patch / "LUCINET-World-Reforged.esp", "World-Reforged-Basisplugin")
    shader = require_file(base_patch / "shaders" / "lucinet_world.omwfx", "World-Reforged-Weltshader")
    plugin_hash = sha256(plugin)
    if plugin_hash != EXPECTED_PLUGIN_SHA256:
        raise ValueError("Der Basispatch stimmt nicht mit der erwarteten Plugin-Prüfsumme überein.")

    manifest_file = require_file(overlay / "MANIFEST.json", "World-Reforged-Korrekturmanifest")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("pluginSha256") != plugin_hash:
        raise ValueError("Das Korrekturoverlay ist nicht an das Basisplugin gebunden.")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Das Korrekturoverlay enthält keine prüfbaren Dateieinträge.")
    seen: set[str] = set()
    receipts: list[dict[str, object]] = []
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Das Korrekturoverlay enthält einen ungültigen Dateieintrag.")
        relative = item.get("path")
        expected_hash = item.get("sha256")
        expected_bytes = item.get("bytes")
        if not isinstance(relative, str) or not relative.startswith("patch/") or ".." in Path(relative).parts:
            raise ValueError("Das Korrekturoverlay enthält einen unsicheren Dateipfad.")
        if relative in seen:
            raise ValueError(f"Das Korrekturoverlay enthält einen doppelten Dateipfad: {relative}")
        seen.add(relative)
        target = require_file(overlay / relative, "World-Reforged-Korrekturdatei")
        if target.stat().st_size != expected_bytes or sha256(target) != expected_hash:
            raise ValueError(f"Die Korrekturdatei stimmt nicht mit ihrem Manifest überein: {relative}")
        receipts.append({"path": relative, "bytes": target.stat().st_size, "sha256": expected_hash})
    return {
        "basePlugin": {"path": str(plugin), "sha256": plugin_hash},
        "worldShader": {"path": str(shader), "sha256": sha256(shader)},
        "overlayManifest": {"path": str(manifest_file), "sha256": sha256(manifest_file)},
        "overlayFiles": receipts,
    }


def copy_verified(source: Path, destination: Path) -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        if item.is_symlink() or (relative.parts and relative.parts[0] == "try-compile") or item.name in ENGINE_EXCLUSIONS:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        source_hash, target_hash = sha256(item), sha256(target)
        if source_hash != target_hash:
            raise ValueError(f"Kopierprüfung der OpenMW-Laufzeit fehlgeschlagen: {relative}")
        receipts.append({"path": relative.as_posix(), "bytes": target.stat().st_size, "sha256": target_hash})
    return receipts


def ensure_new_output(path: Path) -> Path:
    path = path.expanduser().resolve()
    if str(path).startswith("\\\\"):
        raise ValueError("Der Kandidatenordner darf kein Netzwerkpfad sein.")
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"Der Kandidatenordner ist nicht leer und wird nicht überschrieben: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def build(output: Path, engine_source: Path, base_patch: Path, overlay: Path) -> Path:
    output = ensure_new_output(output)
    engine_source = local_directory(engine_source, "OpenMW-Laufzeitquelle")
    base_patch = local_directory(base_patch, "World-Reforged-Basispatch")
    overlay = local_directory(overlay, "World-Reforged-Korrekturoverlay")
    require_file(engine_source / "openmw.exe", "OpenMW-Programm")
    require_file(engine_source / "openmw.cfg", "OpenMW-Konfiguration")
    binding = validate_world_reforged(base_patch, overlay)

    shutil.copy2(ROOT / "LICENSE.txt", output / "LICENSE.txt")
    shutil.copy2(ROOT / "README.md", output / "README.md")
    shutil.copytree(ROOT / "presets", output / "presets")
    engine_receipts = copy_verified(engine_source, output / "engine")
    write_json(output / "world-reforged-source.json", {
        "schema": "halveth.morrowind.world-reforged-link.v1",
        "basePatch": str(base_patch),
        "correctiveOverlay": str(overlay),
        "expectedPluginSha256": EXPECTED_PLUGIN_SHA256,
    })
    executable = output / "Morrowind-Workshop-WorldReforged.exe"
    compile_cs(executable, ["Core.cs", "Workshop.cs"], "Halveth.Morrowind.Program")
    receipt = {
        "status": "LOCAL_CANDIDATE_BUILT_NOT_INSTALLED",
        "recordedUtc": datetime.now(timezone.utc).isoformat(),
        "candidate": str(output),
        "executable": {"path": executable.name, "sha256": sha256(executable), "bytes": executable.stat().st_size},
        "engine": {"source": str(engine_source), "files": len(engine_receipts), "filesSha256": hashlib.sha256(json.dumps(engine_receipts, sort_keys=True).encode("utf-8")).hexdigest()},
        "worldReforged": binding,
        "scope": "OpenMW runtime copy plus local source binding. No game data import, gameplay launch, installation, or overwrite occurred.",
    }
    write_json(output / "evidence" / "candidate-build.json", receipt)
    return executable


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--engine-source", required=True, type=Path)
    parser.add_argument("--world-reforged-base", required=True, type=Path)
    parser.add_argument("--world-reforged-overlay", required=True, type=Path)
    args = parser.parse_args()
    result = build(args.output, args.engine_source, args.world_reforged_base, args.world_reforged_overlay)
    print(result)
