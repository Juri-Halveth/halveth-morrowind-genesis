"""Isolated transactional forward-patch tests; no personal install is changed."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import apply_1_0_6 as update


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class ForwardPatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.old = b'old owned app code\n'
        self.new = b'new owned app code\n'
        self.file = self.root / 'app' / 'server.py'
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(self.old)
        self.inbox = self.root / 'app/mod/bridge/inbox.json'
        self.inbox.parent.mkdir(parents=True)
        self.inbox.write_bytes(b'{"sequence":88}\n')
        self.sentinel = self.root / 'app/.local/graphics/third-party.dds'
        self.sentinel.parent.mkdir(parents=True)
        self.sentinel.write_bytes(b'licensed third-party graphic')
        self.save = self.root / 'app/.local/profiles/beauty/saves/hero.omwsave'
        self.save.parent.mkdir(parents=True)
        self.save.write_bytes(b'personal save')
        self.engine = self.root / 'engine/openmw.exe'
        self.engine.parent.mkdir(parents=True)
        self.engine.write_bytes(b'engine')
        self.profile = self.root / 'profiles/max/openmw.cfg'
        self.profile.parent.mkdir(parents=True)
        self.profile.write_bytes(b'profile')
        self.state_file = self.root / 'install-state.json'
        self.state_file.write_text(json.dumps({
            'version': update.BASE_VERSION, 'mode': 'local-engine',
            'engineRoot': str(self.root), 'files': [
                {'path': 'app/server.py', 'sha256': sha(self.old), 'bytes': len(self.old)},
                {'path': 'app/mod/bridge/inbox.json', 'sha256': sha(b'{"sequence":0}\n'),
                 'bytes': len(b'{"sequence":0}\n')},
                {'path': 'engine/openmw.exe', 'sha256': sha(b'engine'), 'bytes': 6},
                {'path': 'profiles/max/openmw.cfg', 'sha256': sha(b'profile'), 'bytes': 7},
            ]}, indent=2), encoding='utf-8')
        self.source = {'server.py': self.new, 'voice_input.py': b'new voice input\n',
                       'mod/bridge/inbox.json': b'{"sequence":0}\n',
                       'data/entities.json': b'[]\n'}
        self.valid = patch.object(update.build_release, 'validate_files', return_value=None)
        self.valid.start()
        self.addCleanup(self.valid.stop)
        self.process = patch.object(update, 'ensure_game_closed')
        self.process.start()
        self.addCleanup(self.process.stop)

    def state(self):
        return json.loads(self.state_file.read_text(encoding='utf-8'))

    def test_dry_run_and_patch_only_allowlisted_app_files(self):
        before = self.state_file.read_bytes()
        plan = update.apply(self.root, dry_run=True, source=self.source)
        self.assertEqual(plan['status'], 'READY')
        self.assertEqual(plan['changed'], ['app/server.py'])
        self.assertEqual(plan['added'], ['app/voice_input.py'])
        self.assertEqual(plan['managedAppFilesVerified'], 1)
        self.assertEqual(plan['changedDetails'][0]['observedSha256'], sha(self.old))
        self.assertEqual(plan['changedDetails'][0]['desiredSha256'], sha(self.new))
        self.assertFalse(Path(plan['backup']).exists())
        self.assertEqual(self.state_file.read_bytes(), before)
        receipt = update.apply(self.root, source=self.source)
        self.assertEqual(receipt['status'], 'PATCHED_PREVIEW')
        self.assertEqual(self.file.read_bytes(), self.new)
        self.assertEqual((self.root / 'app/voice_input.py').read_bytes(), b'new voice input\n')
        self.assertEqual(self.state()['version'], update.TARGET_VERSION)
        self.assertEqual((Path(receipt['backup']) / 'app/server.py').read_bytes(), self.old)
        self.assertEqual((Path(receipt['backup']) / 'install-state.json').read_bytes(), before)
        self.assertEqual(json.loads((Path(receipt['backup']) / 'receipt.json').read_text()), receipt)
        self.assertEqual(self.inbox.read_bytes(), b'{"sequence":88}\n')
        self.assertEqual(self.sentinel.read_bytes(), b'licensed third-party graphic')
        self.assertEqual(self.save.read_bytes(), b'personal save')
        self.assertEqual(self.engine.read_bytes(), b'engine')
        self.assertEqual(self.profile.read_bytes(), b'profile')

    def test_exact_desired_bytes_reconcile_manifest_only_with_three_hashes(self):
        self.file.write_bytes(self.new)
        plan = update.apply(self.root, dry_run=True, source=self.source)
        self.assertEqual(plan['changed'], [])
        expected = {'path': 'app/server.py', 'manifestSha256': sha(self.old),
                    'observedSha256': sha(self.new), 'desiredSha256': sha(self.new),
                    'bytes': len(self.new)}
        self.assertEqual(plan['alreadyApplied'], [expected])
        receipt = update.apply(self.root, source=self.source)
        self.assertEqual(self.file.read_bytes(), self.new)
        record = next(x for x in self.state()['files'] if x['path'] == 'app/server.py')
        self.assertEqual(record['sha256'], sha(self.new))
        self.assertEqual((Path(receipt['backup']) / 'app/server.py').read_bytes(), self.new)

    def test_one_pinned_prior_mic_overlay_replaced_with_receipt_and_backup(self):
        name = 'app/mod/scripts/halveth/microphone.lua'
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        observed = b'known previous microphone preview\n'
        desired = b'new hidden opt-in microphone\n'
        target.write_bytes(observed)
        old_manifest = b'older microphone baseline\n'
        state = self.state()
        state['files'].append({'path': name, 'sha256': sha(old_manifest),
                               'bytes': len(old_manifest)})
        self.state_file.write_text(json.dumps(state), encoding='utf-8')
        pinned = {name: {'manifestSha256': sha(old_manifest),
                         'manifestBytes': len(old_manifest),
                         'observedSha256': sha(observed), 'observedBytes': len(observed)}}
        with patch.object(update, 'PINNED_DRIFT', pinned):
            target.write_bytes(observed + b'!')
            with self.assertRaisesRegex(ValueError, 'unabhaengig'):
                update.apply(self.root, dry_run=True,
                             source={**self.source, 'mod/scripts/halveth/microphone.lua': desired})
            target.write_bytes(observed)
            plan = update.apply(self.root, dry_run=True,
                                source={**self.source, 'mod/scripts/halveth/microphone.lua': desired})
            self.assertEqual(plan['pinnedPriorDrift'], [{
                'path': name, 'manifestSha256': sha(old_manifest),
                'observedSha256': sha(observed), 'desiredSha256': sha(desired),
                'observedBytes': len(observed), 'desiredBytes': len(desired)}])
            receipt = update.apply(self.root,
                                   source={**self.source, 'mod/scripts/halveth/microphone.lua': desired})
        self.assertEqual(target.read_bytes(), desired)
        self.assertEqual((Path(receipt['backup']) / name).read_bytes(), observed)
        record = next(x for x in self.state()['files'] if x['path'] == name)
        self.assertEqual(record['sha256'], sha(desired))

    def test_arbitrary_drift_blocks_patch_without_manifest_change(self):
        self.file.write_bytes(b'locally modified but not target source')
        before = self.state_file.read_bytes()
        with self.assertRaisesRegex(ValueError, 'unabhaengig'):
            update.apply(self.root, source=self.source)
        self.assertEqual(self.state_file.read_bytes(), before)
        self.assertFalse((self.root / 'app/voice_input.py').exists())

    def test_untracked_collision_and_manifest_duplicate_block(self):
        (self.root / 'app/voice_input.py').write_bytes(b'pre-existing untracked')
        with self.assertRaisesRegex(FileExistsError, 'belegt'):
            update.apply(self.root, source=self.source)
        (self.root / 'app/voice_input.py').unlink()
        state = self.state()
        state['files'].append(dict(state['files'][0], path='APP/SERVER.PY'))
        self.state_file.write_text(json.dumps(state), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'doppelte'):
            update.apply(self.root, source=self.source)

    def test_source_case_collision_and_managed_local_state_block(self):
        with self.assertRaisesRegex(ValueError, 'doppelte Windows-Pfade'):
            update.apply(self.root, source={**self.source,
                                            'VOICE_INPUT.PY': b'different spelling'})
        state = self.state()
        state['files'].append({'path': 'app/.local/saves/hero.omwsave',
                               'sha256': sha(b'personal save'), 'bytes': len(b'personal save')})
        self.state_file.write_text(json.dumps(state), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Nutzerzustand'):
            update.apply(self.root, source=self.source)

    def test_linked_target_or_parent_blocks(self):
        linked = self.root / 'app/linked.py'
        try:
            linked.symlink_to(self.file)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        with self.assertRaisesRegex(ValueError, 'reparse'):
            update.apply(self.root, source={**self.source, 'linked.py': b'owned'})

    def test_reparse_component_blocks_without_symlink_privilege(self):
        actual = update.is_reparse
        marked = self.file.parent.resolve(strict=True)

        def mark_parent(path):
            # Windows CI may create %TEMP% with an 8.3 ancestor (RUNNER~1),
            # while preflight has canonicalized it to runneradmin.
            return path.resolve(strict=False) == marked or actual(path)

        with patch.object(update, 'is_reparse', side_effect=mark_parent):
            with self.assertRaisesRegex(ValueError, 'reparse'):
                update.apply(self.root, source=self.source)
        self.assertEqual(self.file.read_bytes(), self.old)

    def test_receipt_failure_rolls_back_bytes_and_manifest(self):
        before = self.state_file.read_bytes()
        real_replace = os.replace

        def fail_receipt(source, target):
            if Path(target).name == 'receipt.json':
                raise OSError('simulated receipt failure')
            return real_replace(source, target)

        with patch.object(update.os, 'replace', side_effect=fail_receipt):
            with self.assertRaisesRegex(OSError, 'receipt failure'):
                update.apply(self.root, source=self.source)
        self.assertEqual(self.file.read_bytes(), self.old)
        self.assertFalse((self.root / 'app/voice_input.py').exists())
        self.assertEqual(self.state_file.read_bytes(), before)
        self.assertEqual(self.save.read_bytes(), b'personal save')

    def test_second_file_failure_rolls_back_first(self):
        before = self.state_file.read_bytes()
        real_replace = os.replace

        def fail_second(source, target):
            if Path(target).name == 'voice_input.py':
                raise OSError('simulated second file failure')
            return real_replace(source, target)

        with patch.object(update.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'second file failure'):
                update.apply(self.root, source=self.source)
        self.assertEqual(self.file.read_bytes(), self.old)
        self.assertFalse((self.root / 'app/voice_input.py').exists())
        self.assertEqual(self.state_file.read_bytes(), before)

    def test_manifest_race_blocks_before_any_replacement(self):
        real_staged = update._write_staged
        changed = False

        def mutate_manifest_after_staging(target, raw):
            nonlocal changed
            staged = real_staged(target, raw)
            if not changed:
                changed = True
                self.state_file.write_bytes(self.state_file.read_bytes() + b' ')
            return staged

        with patch.object(update, '_write_staged', side_effect=mutate_manifest_after_staging):
            with self.assertRaisesRegex(RuntimeError, 'Manifest|manifest'):
                update.apply(self.root, source=self.source)
        self.assertEqual(self.file.read_bytes(), self.old)
        self.assertFalse((self.root / 'app/voice_input.py').exists())

    def test_source_version_gate_before_collection(self):
        with patch.object(update.build_release, 'VERSION', '1.0.5'):
            with self.assertRaisesRegex(ValueError, 'Version 1.0.6'):
                update.apply(self.root, dry_run=True)

    @unittest.skipUnless(os.name == 'nt', 'Windows process enumeration')
    def test_failed_process_enumeration_is_not_treated_as_closed(self):
        self.process.stop()
        with patch.object(update, '_windows_processes', side_effect=RuntimeError('WMI unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'WMI unavailable'):
                update.apply(self.root, dry_run=True, source=self.source)

    @unittest.skipUnless(os.name == 'nt', 'Windows process enumeration')
    def test_live_game_and_exact_companion_block_even_without_pid_file(self):
        self.process.stop()
        with patch.object(update, '_windows_processes', return_value=[
            {'Name': 'openmw.exe', 'ProcessId': 42, 'ExecutablePath': r'C:\OpenMW\openmw.exe'}]):
            with self.assertRaisesRegex(RuntimeError, 'OpenMW laeuft'):
                update.apply(self.root, dry_run=True, source=self.source)
        server = str(self.root / 'app/server.py')
        with patch.object(update, '_windows_processes', return_value=[
            {'Name': 'python.exe', 'ProcessId': 43, 'ExecutablePath': r'C:\Python314\python.exe',
             'CommandLine': f'python.exe "{server}" --log out.log'}]):
            with self.assertRaisesRegex(RuntimeError, 'Begleiter laeuft'):
                update.apply(self.root, dry_run=True, source=self.source)


if __name__ == '__main__':
    unittest.main()
