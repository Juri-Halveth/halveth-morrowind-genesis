"""Compile acquired/generated UV maps to a private OpenMW texture overlay.

This only converts image encoding. It neither invents geometry nor certifies UV
alignment. Inputs remain untouched; activate the output only after native QA.
Pillow is required by this optional authoring tool, not by the game launcher.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def texture_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value or ":" in value:
        raise ValueError("Use a relative texture path with forward slashes.")
    path = PurePosixPath(value)
    if (not value.startswith("textures/") or path.is_absolute()
            or any(p in {"", ".", ".."} for p in value.split("/"))
            or path.suffix.lower() != ".dds"
            or any(ord(c) < 32 for c in value)):
        raise ValueError("Target must be a relative DDS path below textures/.")
    return path


def build(plan_path: Path, output: Path) -> dict:
    from PIL import Image, __version__ as pillow_version

    plan_path = plan_path.resolve(strict=True)
    output = output.resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schemaVersion") != 1 or not isinstance(plan.get("maps"), list):
        raise ValueError("Expected schemaVersion 1 and a maps list.")
    if not 1 <= len(plan["maps"]) <= 64 or output.exists():
        raise ValueError("Use 1..64 maps and a new output directory.")
    seen, records = set(), []
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage all conversions before publishing a complete directory.
    with tempfile.TemporaryDirectory(prefix="material-overlay-", dir=output.parent) as work:
        staging = Path(work) / "pack"
        staging.mkdir()
        for item in plan["maps"]:
            target = texture_path(item["target"])
            if str(target).casefold() in seen:
                raise ValueError("Duplicate texture target.")
            seen.add(str(target).casefold())
            paths = {k: Path(item[k]).resolve(strict=True) for k in ("source", "original")}
            for key, path in paths.items():
                expected = item.get(key + "Sha256", "")
                if not re.fullmatch(r"[a-f0-9]{64}", expected) or path.stat().st_size > 64 * 1024 * 1024:
                    raise ValueError("Bind each bounded input to its SHA-256.")
                if sha256(path) != expected:
                    raise ValueError(f"Input changed: {key}")
            with Image.open(paths["original"]) as original, Image.open(paths["source"]) as source:
                if source.format != "PNG" or original.format != "DDS":
                    raise ValueError("Expected PNG source and DDS UV reference.")
                w, h = source.size
                if min(w, h) < 32 or max(w, h) > 8192 or w * h > 32 * 1024 * 1024:
                    raise ValueError("Texture exceeds the authoring size budget.")
                if w * original.height != h * original.width:
                    raise ValueError("UV atlas aspect ratio changed.")
                rgba = source.convert("RGBA")
                reference_size = list(original.size)
            destination = staging.joinpath(*target.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Uncompressed DDS preserves pixels exactly. No resampling/upscale.
            rgba.save(destination, format="DDS")
            with Image.open(destination) as decoded:
                if decoded.size != rgba.size or decoded.convert("RGBA").tobytes() != rgba.tobytes():
                    raise ValueError("DDS pixel roundtrip failed.")
            for key, path in paths.items():
                if sha256(path) != item[key + "Sha256"]:
                    raise ValueError("Input changed during conversion.")
            records.append({"path": str(target), "sha256": sha256(destination),
                            "bytes": destination.stat().st_size, "size": [w, h],
                            "sourceSize": [w, h], "referenceSize": reference_size,
                            "sourceSha256": item["sourceSha256"],
                            "originalSha256": item["originalSha256"],
                            "pixelRoundtrip": "EXACT_RGBA", "uvAlignment": "REQUIRES_NATIVE_REVIEW"})
        receipt = {"schemaVersion": 1, "recordedAt": datetime.now(timezone.utc).isoformat(),
                   "name": plan.get("name", "Private material overlay"), "files": records,
                   "planSha256": sha256(plan_path), "pillowVersion": pillow_version,
                   "state": "BUILT_NOT_ACTIVATED", "scope": "Texture encoding only; no geometry, rig or gameplay edits."}
        (staging / "material-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.plan, args.output), indent=2))


if __name__ == "__main__":
    main()
