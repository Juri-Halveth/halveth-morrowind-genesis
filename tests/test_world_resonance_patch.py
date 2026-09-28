"""Exercise additive installation and rollback against disposable Windows files."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'scripts' / 'Apply-WorldResonance.ps1'
FILES = (
    'mod/halveth.omwscripts', 'mod/scripts/halveth/player.lua', 'server.py',
    'mod/scripts/halveth/resonance_rules.lua',
    'mod/scripts/halveth/world_resonance.lua',
    'mod/scripts/halveth/world_resonance_global.lua',
)


@unittest.skipUnless(os.name == 'nt', 'Windows installer contract')
class ResonancePatchTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which('powershell.exe')
        if not self.shell:
            self.skipTest('Windows PowerShell is not installed')
        self.scratch = ROOT / '.local' / 'resonance-patch-tests'
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.scratch)
        self.install = Path(self.temp.name).resolve()
        self.originals = {}
        records = []
        for relative in FILES[:3]:
            raw = ('original ' + relative + '\n').encode()
            path = self.install / 'app' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.originals[relative] = raw
            records.append(dict(path='app/' + relative, bytes=len(raw),
                                sha256=hashlib.sha256(raw).hexdigest()))
        (self.install / 'HALVETH Morrowind.exe').write_bytes(b'fixture; never executed')
        self.state = json.dumps(dict(version='1.0.6-preview', files=records)).encode()
        (self.install / 'install-state.json').write_bytes(self.state)

    def tearDown(self):
        if hasattr(self, 'temp'):
            # Only retire this test's verified, newly allocated directory.
            self.assertTrue(self.install.is_relative_to(self.scratch.resolve()))
            self.temp.cleanup()

    def run_patch(self, *, apply=False, lock_second=False):
        if lock_second:
            command = (
                "$held=[IO.File]::Open($env:RESONANCE_TEST_LOCK,'Open','Read','Read'); "
                "try { & $env:RESONANCE_TEST_SCRIPT -InstallRoot $env:RESONANCE_TEST_ROOT -Apply; exit 0 } "
                "catch { Write-Output $_.Exception.Message; exit 1 } finally { $held.Dispose() }"
            )
            args = [self.shell, '-NoProfile', '-NonInteractive', '-Command', command]
        else:
            args = [self.shell, '-NoProfile', '-NonInteractive', '-File', str(PATCH),
                    '-InstallRoot', str(self.install)] + (['-Apply'] if apply else [])
        env = dict(os.environ, RESONANCE_TEST_SCRIPT=str(PATCH),
                   RESONANCE_TEST_ROOT=str(self.install),
                   RESONANCE_TEST_LOCK=str(self.install / 'app' / FILES[1]))
        # Do not inject the parent PowerShell 7 module paths into Windows PowerShell.
        for key in list(env):
            if key.casefold() == 'psmodulepath':
                del env[key]
        return subprocess.run(args, env=env, capture_output=True, text=True, timeout=45)

    def assert_originals(self):
        self.assertEqual((self.install / 'install-state.json').read_bytes(), self.state)
        for relative, raw in self.originals.items():
            self.assertEqual((self.install / 'app' / relative).read_bytes(), raw)
        for relative in FILES[3:]:
            self.assertFalse((self.install / 'app' / relative).exists())

    def test_plan_then_apply_keeps_verified_backup_and_manifest(self):
        plan = self.run_patch()
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertEqual(json.loads(plan.stdout)['status'], 'PLAN')
        self.assert_originals()
        self.assertFalse((self.install / 'app' / '.local').exists())
        applied = self.run_patch(apply=True)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        receipt = json.loads(applied.stdout)
        self.assertEqual(receipt['status'], 'APPLIED')
        backup = Path(receipt['backup'])
        self.assertTrue(backup.is_relative_to(self.install))
        self.assertEqual((backup / 'install-state.json').read_bytes(), self.state)
        for relative, raw in self.originals.items():
            self.assertEqual((backup / 'app' / relative).read_bytes(), raw)
        state = json.loads((self.install / 'install-state.json').read_bytes())
        records = {entry['path']: entry for entry in state['files']}
        self.assertEqual(len(records), 6)
        self.assertEqual(state['features']['worldResonance']['version'], 1)
        for relative in FILES:
            raw = (self.install / 'app' / relative).read_bytes()
            self.assertEqual(raw, (ROOT / relative).read_bytes())
            self.assertEqual(records['app/' + relative]['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(records['app/' + relative]['bytes'], len(raw))

    def test_independent_edit_stops_before_any_patch(self):
        changed = self.install / 'app' / FILES[1]
        changed.write_bytes(b'independent edit')
        result = self.run_patch(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Independent installed change', result.stderr)
        self.assertEqual(changed.read_bytes(), b'independent edit')
        self.assertEqual((self.install / 'app' / FILES[0]).read_bytes(), self.originals[FILES[0]])
        self.assertEqual((self.install / 'install-state.json').read_bytes(), self.state)
        self.assertFalse((self.install / 'app' / '.local').exists())

    def test_second_file_write_failure_restores_first_file(self):
        result = self.run_patch(apply=True, lock_second=True)
        self.assertNotEqual(result.returncode, 0)
        receipts = list((self.install / 'app' / '.local').rglob('receipt.json'))
        self.assertEqual(len(receipts), 1, result.stderr + result.stdout)
        receipt = json.loads(receipts[0].read_bytes())
        self.assertEqual(receipt['status'], 'ROLLED_BACK', receipt)
        self.assertEqual(receipt['rollbackErrors'], [])
        self.assertEqual(receipt['writtenPaths'], ['app/' + FILES[0]])
        self.assert_originals()
        self.assertFalse((self.install / 'app' / '.local' / 'world-resonance-patching.lock').exists())


if __name__ == '__main__':
    unittest.main()
