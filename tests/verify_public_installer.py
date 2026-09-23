"""Verify the public one-file Setup EXE without installing or running the game.

The build embeds a ZIP resource inside a .NET single-file executable. This
check reads that resource, its manifest, and the current Git source snapshot.
It never needs OpenMW, Morrowind data, saves, Ollama, or a model download.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer import build_installer  # noqa: E402
from scripts import build_release  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def embedded_payload(executable: bytes) -> tuple[zipfile.ZipFile, bytes]:
    """Open the intact ZIP resource inside the .NET single-file bundle."""
    end_record = executable.rfind(b"PK\x05\x06")
    require(end_record >= 0 and end_record + 22 <= len(executable),
            "Embedded ZIP end record missing")
    comment_length = struct.unpack_from("<H", executable, end_record + 20)[0]
    end = end_record + 22 + comment_length
    require(end <= len(executable), "Embedded ZIP end record is truncated")
    archive = zipfile.ZipFile(io.BytesIO(executable[:end]))
    central_offset = struct.unpack_from("<I", executable, end_record + 16)[0]
    start = archive.start_dir - central_offset
    require(start >= 0 and executable[start:start + 4] == b"PK\x03\x04",
            "Embedded ZIP start is invalid")
    return archive, executable[start:end]


def verify(exe: Path) -> dict[str, object]:
    require(exe.is_file(), f"Public Setup EXE is absent: {exe}")
    executable = exe.read_bytes()
    require(not re.search(rb"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+[\\/]",
                          executable, re.IGNORECASE),
            "A machine-specific user path appears in the Setup EXE")
    archive, payload_bytes = embedded_payload(executable)
    require(archive.testzip() is None, "Embedded ZIP has a CRC failure")

    receipt_path = exe.with_suffix(".json")
    require(receipt_path.is_file(), "Setup build receipt is absent")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("sha256") == sha256(executable), "Setup EXE hash differs from receipt")
    require(receipt.get("payloadSha256") == sha256(payload_bytes),
            "Embedded ZIP hash differs from receipt")
    require(receipt.get("mode") == "owned-mod", "Receipt is not for the public setup")

    manifest = json.loads(archive.read("payload-manifest.json"))
    require(manifest.get("version") == build_release.VERSION, "Setup version differs from source")
    require(manifest.get("mode") == "owned-mod", "Setup contains a non-public payload mode")
    require(manifest.get("engineSource") is None, "Public setup declares an engine source")
    require(manifest.get("pythonSha256") == build_installer.PYTHON_SHA256,
            "Python runtime hash differs from the pinned builder input")

    records = manifest.get("files")
    require(isinstance(records, list) and records, "Payload manifest has no file records")
    paths = [record["path"] for record in records]
    require(len(paths) == len(set(paths)), "Payload manifest has duplicate paths")
    require(len(paths) == len({path.casefold() for path in paths}),
            "Payload paths collide on Windows")
    for path in paths:
        parts = path.split("/")
        require(not path.startswith("/") and "\\" not in path and ":" not in path
                and all(part not in ("", ".", "..") for part in parts),
                f"Unsafe payload path: {path}")
        require(parts[0] in ("app", "runtime"), f"Unexpected payload root: {path}")
        require(not path.casefold().endswith((".esm", ".esp", ".bsa", ".omwsave",
                                            ".ess", ".gguf", ".safetensors")),
                f"Game data, save or model weight in public setup: {path}")
        require(not any(part.casefold() in (".local", "saves", "backups", "screenshots",
                                                "logs", "profiles") for part in parts),
                f"Private runtime directory in public setup: {path}")
    entries = [entry.filename for entry in archive.infolist()]
    require(len(entries) == len(set(entries)), "Embedded ZIP has duplicate entries")
    require(set(entries) == set(paths) | {"payload-manifest.json"},
            "Embedded ZIP does not match its file manifest")

    for record in records:
        content = archive.read(record["path"])
        require(len(content) == record["bytes"]
                and sha256(content) == record["sha256"],
                f"Payload file hash or size mismatch: {record['path']}")

    source = build_release.collect_files()
    build_release.validate_files(source)
    expected_app = {"app/" + name: content for name, content in source.items()
                    if name != "RELEASE-NOTE.txt"}
    actual_app = {path: archive.read(path) for path in paths if path.startswith("app/")}
    require(actual_app == expected_app,
            "Installed app bytes do not match the checked current source snapshot")
    require(actual_app["app/mod/bridge/inbox.json"]
            == b'{"sequence":0,"sessionId":""}\n',
            "Embedded game bridge contains non-empty runtime state")
    require("app/mod/bridge/companion-status.json" not in actual_app,
            "Companion runtime status is bundled")
    require("runtime/python.exe" in paths and "runtime/LICENSE.txt" in paths,
            "Official Python runtime or its license is absent")

    return {"state": "PASS", "version": build_release.VERSION,
            "exeSha256": sha256(executable), "payloadSha256": sha256(payload_bytes),
            "payloadFiles": len(paths), "appFiles": len(actual_app),
            "engineFiles": 0, "gameDataIncluded": False}


def main() -> None:
    default_exe = (ROOT / "dist" / "installer-candidates"
                   / f"HALVETH-Morrowind-Genesis-{build_release.VERSION}-Setup.exe")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=default_exe)
    args = parser.parse_args()
    print(json.dumps(verify(args.exe.resolve()), indent=2))


if __name__ == "__main__":
    main()
