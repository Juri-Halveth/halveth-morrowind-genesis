"""Install or disable the optional Scarlet LOVE tapestry in a Genesis profile.

Consumes finished PNG, TGA and DDS files; this tool never converts or edits pixels.
Only a separate mod directory and graphics manifest change. Original game data,
quests, actors, saves and source images remain untouched. Restart OpenMW and
prepare the Genesis profile after applying or restoring the graphics manifest.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import uuid

PROJECT = Path(__file__).resolve().parents[1]
PACK_ID = "halveth-scarlet-love-banner-v1"
PACK_NAME = "Scarlet LOVE Banner"
TGA_PATH = Path("Textures/Tx_de_tapestry_02.tga")
DDS_PATH = Path("Textures/Tx_de_tapestry_02.dds")
PNG_PATH = Path("Textures/halveth/scarlet-love-banner.png")
MAX_BYTES = 128 * 1024 * 1024


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_bytes(raw)
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def image_input(path: Path, kind: str) -> tuple[bytes, tuple[int, int]]:
    path = Path(path)
    if not path.is_file() or not 18 <= path.stat().st_size <= MAX_BYTES:
        raise ValueError(f"Missing or oversized {kind.upper()} input: {path}")
    raw = path.read_bytes()
    if kind == "png":
        if len(raw) < 33 or raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR" or raw[8:12] != b"\0\0\0\r":
            raise ValueError("PNG input must contain a standard PNG signature and IHDR.")
        width, height = struct.unpack_from(">II", raw, 16)
    elif kind == "tga":
        if raw[1] != 0 or raw[2] not in (2, 10) or raw[16] not in (24, 32):
            raise ValueError("TGA input must be true-color 24/32-bit, uncompressed or RLE.")
        width, height = struct.unpack_from("<HH", raw, 12)
        if raw[2] == 2 and len(raw) < 18 + raw[0] + width * height * (raw[16] // 8):
            raise ValueError("Truncated uncompressed TGA pixel data.")
    else:
        if len(raw) < 128 or raw[:4] != b"DDS " or struct.unpack_from("<I", raw, 4)[0] != 124:
            raise ValueError("DDS input must contain a DDS signature and 124-byte header.")
        height, width = struct.unpack_from("<II", raw, 12)
        pf_size, pf_flags = struct.unpack_from("<II", raw, 76)
        bits = struct.unpack_from("<I", raw, 88)[0]
        if pf_size != 32 or not pf_flags & 0x40 or pf_flags & 0x4 or bits != 32:
            raise ValueError("DDS input must be uncompressed 32-bit RGB(A).")
        if len(raw) < 128 + width * height * 4:
            raise ValueError("Truncated uncompressed DDS pixel data.")
    if width < 128 or width > 4096 or height != width * 2:
        raise ValueError("Banner dimensions must be portrait 1:2, from 128x256 to 4096x8192.")
    return raw, (width, height)


def paths(state_dir: Path, project_dir: Path = PROJECT) -> tuple[Path, Path, Path]:
    state = Path(state_dir).resolve()
    manifest = state / "graphics/install.json"
    pack = state / "graphics/ScarletLoveBanner"
    for target in (manifest, pack, pack / TGA_PATH, pack / DDS_PATH, pack / PNG_PATH):
        if not target.resolve().is_relative_to(state):
            raise ValueError("Banner destination must remain inside the selected Genesis state directory.")
    return state, manifest, pack


@contextmanager
def operation_lock(state: Path):
    lock = state / "graphics/scarlet-banner.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError("Another banner operation owns scarlet-banner.lock; finish it before retrying.") from exc
    try:
        stream.write(datetime.now(timezone.utc).isoformat())
        stream.close()
        yield
    finally:
        stream.close()
        lock.unlink()


def read_manifest(path: Path) -> tuple[dict, bytes | None]:
    raw = path.read_bytes() if path.exists() else None
    data = json.loads(raw.decode("utf-8-sig")) if raw is not None else {
        "schemaVersion": 1, "dataDirectories": [], "shaders": ["bloomlinear"], "packages": []}
    if not isinstance(data, dict) or data.get("schemaVersion") != 1 or not isinstance(data.get("dataDirectories"), list):
        raise ValueError("Expected schemaVersion 1 graphics manifest with dataDirectories.")
    if any(not isinstance(value, str) for value in data["dataDirectories"]):
        raise ValueError("Graphics dataDirectories must contain paths.")
    if not isinstance(data.get("packages", []), list) or any(not isinstance(item, dict) for item in data.get("packages", [])):
        raise ValueError("Graphics packages must be objects.")
    return data, raw


def is_pack_path(value: str, project_dir: Path, pack: Path) -> bool:
    candidate = Path(value).expanduser()
    return (candidate if candidate.is_absolute() else project_dir / candidate).resolve() == pack


def record_operation(manifest: Path, pack: Path, before: bytes | None, after: bytes, details: dict) -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = manifest.with_name("install.before-scarlet-" + stamp + ".json") if before is not None else None
    if backup:
        atomic_bytes(backup, before)
        if backup.read_bytes() != before:
            raise OSError("Graphics manifest backup verification failed.")
    receipt = {"schema": "halveth.scarlet-banner.install.v1", "recordedAt": datetime.now(timezone.utc).isoformat(),
        **details, "manifest": str(manifest), "manifestBackup": str(backup) if backup else None,
        "manifestBeforeSha256": sha256(before) if before is not None else None,
        "manifestAfterSha256": sha256(after),
        "scope": "Optional texture-only override for all furn_de_tapestry_02 uses; no plugin, original file or save edits.",
        "nextStep": "Prepare the Genesis graphics profile and restart OpenMW to update its VFS."}
    atomic_bytes(manifest, after)
    atomic_bytes(pack / "receipts" / (stamp + ".json"), encoded(receipt))
    atomic_bytes(pack / "install-receipt.json", encoded(receipt))
    return receipt


def apply(png: Path, tga: Path, state_dir: Path, project_dir: Path = PROJECT, dds: Path | None = None) -> dict:
    png_raw, png_size = image_input(png, "png")
    tga_raw, tga_size = image_input(tga, "tga")
    dds = Path(dds) if dds is not None else project_dir / "assets/ScarletLoveBanner" / DDS_PATH
    dds_raw, dds_size = image_input(dds, "dds")
    if png_size != tga_size or png_size != dds_size:
        raise ValueError("PNG, TGA and DDS dimensions must match; convert the same banner before installation.")
    state, manifest, pack = paths(state_dir, project_dir)
    with operation_lock(state):
        data, before = read_manifest(manifest)
        owned = any(item.get("id") == PACK_ID for item in data.get("packages", []))
        present = any(is_pack_path(value, project_dir, pack) for value in data["dataDirectories"])
        if present and not owned:
            raise ValueError("An unowned manifest entry already uses ScarletLoveBanner; review it before applying.")
        source_digests = {str(Path(png).resolve()): sha256(png_raw), str(Path(tga).resolve()): sha256(tga_raw),
                          str(dds.resolve()): sha256(dds_raw)}
        asset_receipts = []
        for relative, raw in ((PNG_PATH, png_raw), (TGA_PATH, tga_raw), (DDS_PATH, dds_raw)):
            destination = pack / relative
            if destination.exists() and destination.read_bytes() != raw:
                old = destination.read_bytes()
                atomic_bytes(pack / "asset-backups" / sha256(old) / relative, old)
            atomic_bytes(destination, raw)
            if sha256(destination.read_bytes()) != sha256(raw):
                raise OSError("Copied banner asset does not match its source.")
            asset_receipts.append({"path": str(relative).replace("\\", "/"), "bytes": len(raw), "sha256": sha256(raw)})
        data["dataDirectories"] = [value for value in data["dataDirectories"] if not is_pack_path(value, project_dir, pack)] + [str(pack)]
        data["packages"] = [item for item in data.get("packages", []) if item.get("id") != PACK_ID] + [{
            "id": PACK_ID, "name": PACK_NAME, "version": "1.0.0", "status": "installed",
            "dataDirectory": str(pack), "bytes": len(png_raw) + len(tga_raw) + len(dds_raw), "fileCount": 3,
            "source": "User-directed original generated Scarlet LOVE artwork", "activeTextureCount": 1,
            "activation": "Texture-only override; all existing copies of this tapestry use the optional artwork."}]
        return record_operation(manifest, pack, before, encoded(data), {"operation": "apply", "active": True,
            "assetHeaderDimensions": list(png_size), "assets": asset_receipts, "inputSha256": source_digests,
            "validation": "Image headers, copied bytes and manifest backup verified; native visual check is separate."})


def restore(state_dir: Path, project_dir: Path = PROJECT) -> dict:
    state, manifest, pack = paths(state_dir, project_dir)
    with operation_lock(state):
        data, before = read_manifest(manifest)
        owned = any(item.get("id") == PACK_ID for item in data.get("packages", []))
        present = any(is_pack_path(value, project_dir, pack) for value in data["dataDirectories"])
        if present and not owned:
            raise ValueError("No owned Scarlet banner entry; refusing to alter that manifest path.")
        if not present and not owned:
            return {"schema": "halveth.scarlet-banner.install.v1", "operation": "restore", "active": False, "changed": False}
        # Remove only this pack, retaining graphics changes made since installation.
        data["dataDirectories"] = [value for value in data["dataDirectories"] if not is_pack_path(value, project_dir, pack)]
        data["packages"] = [item for item in data.get("packages", []) if item.get("id") != PACK_ID]
        return record_operation(manifest, pack, before, encoded(data), {"operation": "restore", "active": False,
            "changed": True, "retainedAssets": str(pack), "restoreMode": "Only this pack disabled; unrelated manifest changes retained."})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("apply", "restore"))
    parser.add_argument("--state-dir", type=Path, default=PROJECT / ".local")
    parser.add_argument("--png", type=Path, default=PROJECT / "mod" / PNG_PATH,
                        help="Finished 1:2 PNG for native F8 artwork.")
    parser.add_argument("--tga", type=Path, default=PROJECT / "assets/ScarletLoveBanner" / TGA_PATH,
                        help="Finished matching TGA for the existing tapestry mesh.")
    parser.add_argument("--dds", type=Path, default=PROJECT / "assets/ScarletLoveBanner" / DDS_PATH,
                        help="Finished matching 32-bit DDS overriding OpenMW's preferred archive alternative.")
    args = parser.parse_args()
    try:
        result = apply(args.png, args.tga, args.state_dir, dds=args.dds) if args.operation == "apply" else restore(args.state_dir)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Banner operation stopped: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
