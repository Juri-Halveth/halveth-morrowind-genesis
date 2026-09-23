#!/usr/bin/env python3
"""Install three pinned shader packages as local data; never execute upstream code.

Python standard library only. Downloads and extracted assets stay below .local
and are excluded from the Genesis source release. This does not license or
redistribute third-party assets. Existing different files cause a clear error.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import urllib.request
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_EXTRACTED = 64 * 1024 * 1024
MAX_FILES = 8192
CHAIN = ["ssao", "clouds", "bloomlinear", "hdr_linear", "FollowerAA"]
PACKAGES = (
    {"repo": "zesterer/openmw-ssao", "name": "Zesterer High Quality SSAO",
     "commit": "fa5ec4303ee557b75e3c51c02ab14ff0334271c4",
     "sha256": "18e3cfba20e1005939dbfab7ea659cd942dd970dd6419f6a6852b33901ce587c",
     "license": "Author public download; no standalone LICENSE file; private install only"},
    {"repo": "zesterer/openmw-volumetric-clouds", "name": "Zesterer Volumetric Clouds and Mist",
     "commit": "c8830bcd2de0f6e7355f91880308426203eded3c",
     "sha256": "64223c03f771a17035653e0f6ba7238bf8bd32f873d22df66a661eb427c3b454",
     "license": "Author permits modpack inclusion subject to README requests; private install only"},
    {"repo": "wareya/OpenMW-Shaders", "name": "Wareya FollowerAA",
     "commit": "76e0637187cc2878575528119aed72bbbf1a12cf",
     "sha256": "99b1fd6647dd088a72e605dcfae2f1be0805fb28ee4dea4faacf67a06cb0df56",
     "license": "Apache-2.0; this installer keeps the assets local"},
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_link(path: Path) -> None:
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError(f"Linked installation path is unsupported: {path}")


def atomic_bytes(path: Path, data: bytes) -> None:
    reject_link(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as f:
        temporary = Path(f.name)
        f.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_archive(package: dict, downloads: Path) -> bytes:
    stem = package["repo"].split("/")[1] + "-" + package["commit"][:12]
    archive = downloads / (stem + ".zip")
    reject_link(archive)
    if archive.exists():
        if not archive.is_file() or archive.stat().st_size > MAX_ARCHIVE:
            raise ValueError(f"Invalid cached archive: {archive}")
        data = archive.read_bytes()
    else:
        url = f"https://codeload.github.com/{package['repo']}/zip/{package['commit']}"
        request = urllib.request.Request(url, headers={"User-Agent": "HALVETH-Genesis-pinned-shader-installer"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_ARCHIVE + 1)
        if len(data) > MAX_ARCHIVE:
            raise ValueError(f"Shader archive exceeds 32 MiB: {package['name']}")
    if sha256(data) != package["sha256"]:
        raise ValueError(f"Archive SHA-256 mismatch; existing files kept: {archive}")
    if not archive.exists():
        atomic_bytes(archive, data)
    return data


def archive_files(package: dict, data: bytes) -> dict[str, bytes]:
    """Validate the complete archive before writing any asset directory."""
    root = package["repo"].split("/")[1] + "-" + package["commit"]
    files = {}
    seen = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > MAX_FILES or sum(m.file_size for m in members) > MAX_EXTRACTED:
            raise ValueError("Shader archive exceeds the 64 MiB / 8192 entry extraction budget.")
        for member in members:
            name = member.filename
            parts = name.rstrip("/").split("/")
            mode = member.external_attr >> 16
            if (not parts or parts[0] != root or any(p in {"", ".", ".."} for p in parts)
                    or "\\" in name or ":" in name or "\x00" in name or name.startswith("/")
                    or stat.S_ISLNK(mode) or member.flag_bits & 1
                    or (stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)))):
                raise ValueError(f"Unsupported archive entry: {name!r}")
            for part in parts:
                if part.endswith((" ", ".")) or re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", part, re.I):
                    raise ValueError(f"Non-portable archive entry: {name!r}")
            if len(parts) == 1:
                if not member.is_dir():
                    raise ValueError("Archive root must be a directory.")
                continue
            relative = PurePosixPath(*parts[1:]).as_posix()
            key = relative.casefold()
            if key in seen:
                raise ValueError(f"Duplicate archive path: {relative}")
            seen.add(key)
            if member.is_dir():
                continue
            with archive.open(member) as source:
                content = source.read(MAX_EXTRACTED - total + 1)
            total += len(content)
            if total > MAX_EXTRACTED or len(content) != member.file_size:
                raise ValueError("Extracted shader data exceeds the declared size budget.")
            files[relative] = content
    if not files or not any(name.startswith("shaders/") and name.endswith(".omwfx") for name in files):
        raise ValueError("Archive has no OpenMW shader data.")
    return files


def verify_directory(destination: Path, expected: dict[str, bytes]) -> None:
    reject_link(destination)
    if not destination.is_dir():
        raise ValueError(f"Existing shader destination is not a directory: {destination}")
    actual = {}
    for current, directories, names in os.walk(destination, followlinks=False):
        current = Path(current)
        for name in directories + names:
            reject_link(current / name)
        for name in names:
            path = current / name
            relative = path.relative_to(destination).as_posix()
            if relative not in expected or path.stat().st_size != len(expected[relative]):
                raise ValueError(f"Existing shader files differ; directory kept unchanged: {path}")
            actual[relative] = sha256(path.read_bytes())
    if set(actual) != set(expected) or any(actual[name] != sha256(value) for name, value in expected.items()):
        raise ValueError(f"Existing shader hashes differ; directory kept unchanged: {destination}")


def install_package(package: dict, graphics: Path) -> dict:
    content = archive_files(package, read_archive(package, graphics / "downloads"))
    destination = graphics / "mods" / (package["repo"].split("/")[1] + "-" + package["commit"][:12])
    if destination.exists() or destination.is_symlink():
        verify_directory(destination, content)
    else:
        with tempfile.TemporaryDirectory(prefix=".shader-stage-", dir=graphics / "mods") as temporary:
            stage = Path(temporary) / "data"
            stage.mkdir()
            for name, value in content.items():
                target = stage.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
            verify_directory(stage, content)
            if destination.exists():
                raise FileExistsError(f"Shader destination appeared during installation: {destination}")
            stage.rename(destination)
    return {"name": package["name"], "version": package["commit"][:12], "commit": package["commit"],
            "status": "installed", "bytes": sum(len(value) for value in content.values()), "fileCount": len(content),
            "license": package["license"], "source": "https://github.com/" + package["repo"],
            "download": f"https://codeload.github.com/{package['repo']}/zip/{package['commit']}",
            "sha256": package["sha256"], "dataDirectory": str(destination),
            "shaders": sorted(PurePosixPath(name).stem for name in content if name.startswith("shaders/") and name.endswith(".omwfx")),
            "verifiedFiles": [{"path": name, "bytes": len(value), "sha256": sha256(value)} for name, value in sorted(content.items())]}


def merge_manifest(previous: dict, packages: list[dict]) -> dict:
    if previous and (previous.get("schemaVersion") != 1 or not isinstance(previous.get("dataDirectories", []), list)
                     or not isinstance(previous.get("packages", []), list)):
        raise ValueError("Existing graphics manifest must use schemaVersion 1 and list-valued dataDirectories/packages.")
    sources = {p["source"] for p in packages}
    old_packages = previous.get("packages", [])
    if any(not isinstance(p, dict) for p in old_packages):
        raise ValueError("Existing graphics package metadata must contain objects.")
    replaced_paths = {p.get("dataDirectory") for p in old_packages if p.get("source") in sources}
    new_paths = [p["dataDirectory"] for p in packages]
    remaining_paths = [p for p in previous.get("dataDirectories", []) if p not in replaced_paths and p not in new_paths]
    if any(not isinstance(p, str) for p in remaining_paths):
        raise ValueError("Existing graphics data directories must contain strings.")
    result = dict(previous)
    # Shader data first; existing stars/landscape/heads retain their mutual
    # override order afterwards. Preserve unrelated metadata and packages.
    result.update({"schemaVersion": 1, "recordedAt": datetime.now(timezone.utc).isoformat(),
                   "dataDirectories": new_paths + remaining_paths, "shaders": CHAIN,
                   "packages": packages + [p for p in old_packages if p.get("source") not in sources]})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=PROJECT / ".local", help="Local runtime directory; defaults to project/.local.")
    args = parser.parse_args()
    graphics = args.state_dir.expanduser().resolve() / "graphics"
    lock = graphics / ".install-shaders.lock"
    acquired = False
    try:
        for path in (graphics, graphics / "downloads", graphics / "mods"):
            reject_link(path)
            path.mkdir(parents=True, exist_ok=True)
        with lock.open("x", encoding="ascii") as file:
            file.write(str(os.getpid()))
        acquired = True
        manifest = graphics / "install.json"
        reject_link(manifest)
        before = manifest.read_bytes() if manifest.exists() else None
        previous = json.loads(before.decode("utf-8-sig")) if before else {}
        if not isinstance(previous, dict):
            raise ValueError("Existing graphics manifest must be an object.")
        installed = [install_package(package, graphics) for package in PACKAGES]
        merged = merge_manifest(previous, installed)
        if (manifest.read_bytes() if manifest.exists() else None) != before:
            raise RuntimeError("Graphics manifest changed while installing; installed assets kept, manifest not overwritten. Retry after other preparation ends.")
        if before is not None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            atomic_bytes(manifest.with_name(f"install.json.{stamp}.bak"), before)
        shader_receipt = merge_manifest({}, installed)
        atomic_bytes(graphics / "shader-install.json", (json.dumps(shader_receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        atomic_bytes(manifest, (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(json.dumps({"installed": [p["name"] for p in installed], "manifest": str(manifest),
                          "shaders": CHAIN, "game_launched": False}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"Shader installation stopped: {error}", file=sys.stderr)
        return 2
    finally:
        if acquired:
            lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
