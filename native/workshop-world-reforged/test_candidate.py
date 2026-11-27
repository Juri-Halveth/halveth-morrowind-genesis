#!/usr/bin/env python3
"""Run source-only checks for the World Reforged workshop candidate.

Everything below is synthetic: no installed OpenMW profile, Bethesda game data,
save, World Reforged pack, or live game process is touched.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from build_candidate import ROOT, compile_cs, sha256


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Die gerenderte Oberfläche ist kein PNG.")
        if stream.read(4) != b"\x00\x00\x00\r" or stream.read(4) != b"IHDR":
            raise ValueError("Die gerenderte Oberfläche enthält keinen PNG-IHDR-Block.")
        return struct.unpack(">II", stream.read(8))


def main() -> int:
    sandbox_parent = (ROOT / ".local").resolve()
    sandbox_parent.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="candidate-test-", dir=sandbox_parent))
    core_tests = sandbox / "CoreTests.exe"
    core_receipt = sandbox / "native-core-tests.json"
    compile_cs(core_tests, ["Core.cs", "CoreTests.cs"], "Halveth.Morrowind.CoreTests")
    # Local profile names, overlay paths and staging directories can exceed MAX_PATH.
    # All Core fixtures live under this fresh directory and are removed together.
    with tempfile.TemporaryDirectory(dir=sandbox) as scratch:
        fixture_root = Path(scratch)
        while len(str(fixture_root)) <= 260:
            fixture_root /= "long-workshop-profile"
        subprocess.run([str(core_tests), str(core_receipt), str(fixture_root)], check=True)
    result = json.loads(core_receipt.read_text(encoding="utf-8"))
    if result.get("status") != "PASS":
        raise RuntimeError("Die synthetischen Core-Tests haben keinen PASS-Status geliefert.")

    workshop = sandbox / "Morrowind-Workshop-WorldReforged.exe"
    screenshot = sandbox / "workshop.png"
    compile_cs(workshop, ["Core.cs", "Workshop.cs"], "Halveth.Morrowind.Program")
    subprocess.run([str(workshop), "--render-ui", str(screenshot)], check=True)
    width, height = png_size(screenshot)
    if width < 1000 or height < 850:
        raise RuntimeError(f"Die Kandidatenoberfläche hat eine unerwartete Größe: {width}x{height}")

    report = {
        "status": "PASS",
        "recordedUtc": datetime.now(timezone.utc).isoformat(),
        "coreTests": {"checks": result.get("checks"), "receiptSha256": sha256(core_receipt)},
        "ui": {"screenshot": screenshot.name, "width": width, "height": height, "sha256": sha256(screenshot)},
        "scope": "Synthetic Core fixtures and an offscreen WinForms render only. No installed profile, game data, save, native OpenMW launch, or external effect was exercised.",
    }
    report_path = sandbox / "candidate-test-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
