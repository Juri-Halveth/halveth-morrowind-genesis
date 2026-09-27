"""The local forward port must preserve private game state and reject drift."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import apply_1_0_5 as update


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        old = b'old companion code\n'
        self.target = self.root / 'app' / 'server.py'
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(old)
        inbox = self.root / 'app' / 'mod' / 'bridge' / 'inbox.json'
        inbox.parent.mkdir(parents=True)
        inbox.write_bytes(b'{"sequence":88}\n')
        save = self.root / 'app' / '.local' / 'profiles' / 'beauty' / 'saves' / 'hero.omwsave'
        save.parent.mkdir(parents=True)
        save.write_bytes(b'personal save bytes')
        self.save = save
        self.state = self.root / 'install-state.json'
        self.state.write_text(json.dumps({'version': update.BASE_VERSION, 'mode': 'local-engine',
            'files': [{'path': 'app/server.py', 'sha256': hashlib.sha256(old).hexdigest(),
                       'bytes': len(old)}]}), encoding='utf-8')
        self.source = {'server.py': b'new companion code\n',
                       'voice_input.py': b'new opt-in input code\n',
                       'mod/bridge/inbox.json': b'{"sequence":0}\n'}
        self.valid = patch.object(update, 'validate_files', return_value=None)
        self.valid.start()
        self.addCleanup(self.valid.stop)

    def test_dry_run_then_apply_preserves_save_and_mailbox(self):
        planned = update.apply(self.root, dry_run=True, source=self.source)
        self.assertEqual(planned['status'], 'READY')
        self.assertEqual(planned['changed'], ['app/server.py'])
        self.assertEqual(planned['added'], ['app/voice_input.py'])
        self.assertEqual(self.target.read_bytes(), b'old companion code\n')
        receipt = update.apply(self.root, source=self.source)
        self.assertEqual(receipt['status'], 'PATCHED_PREVIEW')
        self.assertEqual(self.target.read_bytes(), b'new companion code\n')
        self.assertEqual(self.save.read_bytes(), b'personal save bytes')
        self.assertEqual((self.root / 'app/mod/bridge/inbox.json').read_bytes(), b'{"sequence":88}\n')
        self.assertEqual(json.loads(self.state.read_text())['version'], update.VERSION)
        self.assertEqual((Path(receipt['backup']) / 'app/server.py').read_bytes(), b'old companion code\n')

    def test_modified_managed_file_blocks_patch(self):
        self.target.write_bytes(b'changed independently')
        with self.assertRaisesRegex(ValueError, 'unabhaengig'):
            update.apply(self.root, source=self.source)
        self.assertEqual(json.loads(self.state.read_text())['version'], update.BASE_VERSION)
        self.assertFalse((self.root / 'app/voice_input.py').exists())

    def test_running_recorded_game_blocks_patch(self):
        pid_path = self.root / 'app/.local/game.pid'
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text('42000', encoding='ascii')
        with patch.object(update.subprocess, 'run', return_value=subprocess.CompletedProcess(
                ['tasklist'], 0, b'"openmw.exe","42000","Console"\r\n', b'')):
            with self.assertRaisesRegex(RuntimeError, 'laeuft noch'):
                update.apply(self.root, source=self.source)
        self.assertEqual(json.loads(self.state.read_text())['version'], update.BASE_VERSION)

    def test_receipt_failure_restores_previous_app_and_manifest(self):
        actual_replace = os.replace

        def fail_receipt(source, target):
            if Path(target).name == 'receipt.json':
                raise OSError('simulated receipt failure')
            return actual_replace(source, target)

        with patch.object(update.os, 'replace', side_effect=fail_receipt):
            with self.assertRaisesRegex(OSError, 'receipt failure'):
                update.apply(self.root, source=self.source)
        self.assertEqual(self.target.read_bytes(), b'old companion code\n')
        self.assertFalse((self.root / 'app/voice_input.py').exists())
        self.assertEqual(json.loads(self.state.read_text())['version'], update.BASE_VERSION)
        self.assertEqual(self.save.read_bytes(), b'personal save bytes')


if __name__ == '__main__':
    unittest.main()
