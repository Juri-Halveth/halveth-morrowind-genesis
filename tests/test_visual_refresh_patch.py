"""Exercise the five-file installer against disposable Windows fixtures only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "scripts" / "Apply-VisualRefresh.ps1"
FILES = (
    "server.py",
    "dialogue_method.py",
    "mod/scripts/halveth/player.lua",
    "scripts/graphics_profile.py",
    "mod/shaders/halveth_sculpted.omwfx",
)
OLD_FILES = (FILES[0], FILES[2], FILES[3])


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell"), "Windows PowerShell required")
class VisualRefreshPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = ROOT / ".local" / "visual-refresh-patch-tests"
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.scratch)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / "source"
        self.install = self.base / "install"
        self.script = self.source / "scripts" / PATCH.name
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(PATCH, self.script)
        self.new = {name: ("new fixture: " + name + "\n").encode() for name in FILES}
        self.old = {name: ("old fixture: " + name + "\n").encode() for name in OLD_FILES}
        for name, raw in self.new.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for name, raw in self.old.items():
            path = self.install / "app" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (self.install / "HALVETH Morrowind.exe").write_bytes(b"fixture marker; never execute")
        self.state_path = self.install / "install-state.json"
        state = {
            "version": "1.0.6-preview",
            "files": [
                {"path": "app/" + name, "sha256": sha(raw), "bytes": len(raw)}
                for name, raw in self.old.items()
            ],
            "features": {"worldResonance": {"version": 1}},
        }
        self.state_before = json.dumps(state, indent=2).encode()
        self.state_path.write_bytes(self.state_before)
        self.untouched = {
            "app/.local/graphics/install.json": b'{"fixture": "graphics manifest"}',
            "app/profiles/beauty/settings.cfg": b"[fixture]\npreserved=true\n",
            "app/profiles/beauty/saves/untouched.omwsave": b"fixture save bytes",
        }
        for name, raw in self.untouched.items():
            path = self.install / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def tearDown(self) -> None:
        if not self.base.is_relative_to(self.scratch.resolve()):
            raise AssertionError("Fixture escaped scratch root")
        self.temp.cleanup()

    def run_patch(self, *args: str, locked: bool = False) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("PSMODULEPATH", None)
        command = ["powershell", "-NoProfile", "-NonInteractive"]
        if locked:
            env["VISUAL_FIXTURE_SCRIPT"] = str(self.script)
            env["VISUAL_FIXTURE_ROOT"] = str(self.install)
            env["VISUAL_FIXTURE_LOCK"] = str(self.install / "app" / FILES[2])
            env["VISUAL_FIXTURE_PLAN"] = args[-1]
            command += ["-Command", """
$ErrorActionPreference='Stop'
$held=[IO.File]::Open($env:VISUAL_FIXTURE_LOCK,'Open','Read','Read')
try {
    & $env:VISUAL_FIXTURE_SCRIPT -InstallRoot $env:VISUAL_FIXTURE_ROOT -Apply -ExpectedPlanSha256 $env:VISUAL_FIXTURE_PLAN
    exit 0
} catch { Write-Output $_.Exception.Message; exit 1 }
finally { $held.Dispose() }
"""]
        else:
            command += ["-File", str(self.script), "-InstallRoot", str(self.install), *args]
        return subprocess.run(command, cwd=self.base, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=90)

    def plan(self) -> dict:
        result = self.run_patch("-DryRun")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def assert_untouched(self) -> None:
        for name, raw in self.untouched.items():
            self.assertEqual((self.install / name).read_bytes(), raw)

    def test_plan_apply_and_verified_backups(self) -> None:
        plan = self.plan()
        self.assertEqual(plan["status"], "PLAN")
        self.assertEqual(len(plan["contract"]["files"]), 5)
        self.assertEqual(plan["planSha256"], self.plan()["planSha256"])
        self.assertFalse((self.install / "app/.local/patch-backups").exists())
        self.assertEqual(self.state_path.read_bytes(), self.state_before)
        result = self.run_patch("-Apply", "-ExpectedPlanSha256", plan["planSha256"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "APPLIED")
        self.assertEqual(receipt["planSha256"], plan["planSha256"])
        backup = Path(receipt["backup"])
        self.assertTrue(backup.is_relative_to(self.install))
        self.assertEqual((backup / "install-state.json").read_bytes(), self.state_before)
        for name, raw in self.old.items():
            self.assertEqual((backup / "app" / name).read_bytes(), raw)
        state = json.loads(self.state_path.read_bytes())
        self.assertEqual(state["version"], "1.0.6-preview")
        self.assertEqual(state["features"]["worldResonance"], {"version": 1})
        for feature in ("sculptedVisuals", "dialogueMethod"):
            self.assertEqual(state["features"][feature]["version"], "1.0.0")
        records = {record["path"]: record for record in state["files"]}
        self.assertEqual(len(records), 5)
        for name, raw in self.new.items():
            self.assertEqual((self.install / "app" / name).read_bytes(), raw)
            self.assertEqual(records["app/" + name]["sha256"], sha(raw))
        self.assertEqual(receipt["installStateAfterSha256"], sha(self.state_path.read_bytes()))
        self.assertFalse((self.install / "app/.local/visual-refresh-patching.lock").exists())
        self.assert_untouched()

    def test_foreign_change_rejected_before_backup(self) -> None:
        plan = self.plan()
        foreign = self.install / "app" / FILES[0]
        foreign.write_bytes(b"independent user edit")
        result = self.run_patch("-Apply", "-ExpectedPlanSha256", plan["planSha256"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Independent installed change", result.stdout + result.stderr)
        self.assertEqual(foreign.read_bytes(), b"independent user edit")
        self.assertEqual(self.state_path.read_bytes(), self.state_before)
        self.assertFalse((self.install / "app/.local/patch-backups").exists())
        self.assert_untouched()

    def test_storybook_is_opt_in_and_bound_to_its_own_plan(self) -> None:
        name = 'mod/shaders/halveth_storybook.omwfx'
        (self.source / name).write_bytes(b'original storybook shader fixture')
        ordinary = self.plan()
        result = self.run_patch('-DryRun', '-Storybook')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        self.assertNotEqual(plan['planSha256'], ordinary['planSha256'])
        self.assertEqual(len(plan['contract']['files']), 6)
        refused = self.run_patch('-Apply', '-Storybook', '-ExpectedPlanSha256', ordinary['planSha256'])
        self.assertNotEqual(refused.returncode, 0)
        applied = self.run_patch('-Apply', '-Storybook', '-ExpectedPlanSha256', plan['planSha256'])
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual((self.install / 'app' / name).read_bytes(), b'original storybook shader fixture')
        state = json.loads(self.state_path.read_bytes())
        self.assertEqual(state['features']['storybookVisuals']['version'], '1.0.0')
        self.assert_untouched()

    def test_changed_source_invalidates_plan(self) -> None:
        plan = self.plan()
        (self.source / FILES[-1]).write_bytes(b"revised shader fixture")
        result = self.run_patch("-Apply", "-ExpectedPlanSha256", plan["planSha256"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Patch plan changed", result.stdout + result.stderr)
        self.assertEqual(self.state_path.read_bytes(), self.state_before)
        self.assertFalse((self.install / "app/.local/patch-backups").exists())

    def test_existing_unmanaged_new_file_is_preserved(self) -> None:
        plan = self.plan()
        existing = self.install / "app" / FILES[1]
        existing.write_bytes(b"existing unmanaged dialogue implementation")
        result = self.run_patch("-Apply", "-ExpectedPlanSha256", plan["planSha256"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists outside the manifest", result.stdout + result.stderr)
        self.assertEqual(existing.read_bytes(), b"existing unmanaged dialogue implementation")
        self.assertEqual(self.state_path.read_bytes(), self.state_before)
        self.assertFalse((self.install / "app/.local/patch-backups").exists())

    def test_failed_third_write_rolls_back_existing_and_new_files(self) -> None:
        plan = self.plan()
        result = self.run_patch("-Apply", "-ExpectedPlanSha256", plan["planSha256"], locked=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.state_path.read_bytes(), self.state_before)
        for name, raw in self.old.items():
            self.assertEqual((self.install / "app" / name).read_bytes(), raw)
        self.assertFalse((self.install / "app" / FILES[1]).exists())
        self.assertFalse((self.install / "app" / FILES[-1]).exists())
        receipts = list((self.install / "app/.local/patch-backups/visual-refresh").glob("*/receipt.json"))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_bytes())
        self.assertEqual(receipt["status"], "ROLLED_BACK")
        self.assertEqual(receipt["writtenPaths"], ["app/" + FILES[0], "app/" + FILES[1]])
        self.assertEqual(receipt["rollbackErrors"], [])
        self.assertFalse((self.install / "app/.local/visual-refresh-patching.lock").exists())
        self.assert_untouched()

    def test_apply_requires_digest_and_exact_version(self) -> None:
        result = self.run_patch("-Apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ExpectedPlanSha256", result.stdout + result.stderr)
        state = json.loads(self.state_before)
        state["version"] = "1.0.5-preview"
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_patch("-DryRun")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires Genesis 1.0.6-preview", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
