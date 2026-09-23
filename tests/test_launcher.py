"""Launcher process checks with synthetic Windows output; never starts a game."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import launcher


class LauncherProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        (self.state / 'game.pid').write_text('42000', encoding='ascii')
        (self.state / 'game.stdout.log').write_text('Existing log', encoding='utf-8')
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(launcher, 'STATE', self.state))
        self.stack.enter_context(patch.object(launcher, 'os', SimpleNamespace(name='nt')))
        self.stack.enter_context(patch.object(launcher.subprocess, 'CREATE_NO_WINDOW', 0, create=True))
        self.stack.enter_context(patch.object(launcher, 'companion', return_value={
            'command': ['synthetic-openmw'], 'cwd': str(self.state),
        }))
        self.run = self.stack.enter_context(patch.object(launcher.subprocess, 'run'))
        self.spawn = self.stack.enter_context(patch.object(launcher.subprocess, 'Popen', return_value=SimpleNamespace(pid=43000)))

    def output(self, stdout, returncode=0):
        self.run.return_value = subprocess.CompletedProcess(['tasklist'], returncode, stdout=stdout, stderr=b'')

    def assert_no_launch_or_log_change(self):
        self.spawn.assert_not_called()
        self.assertEqual((self.state / 'game.stdout.log').read_text(encoding='utf-8'), 'Existing log')

    def test_oem_no_process_message_allows_new_launch(self):
        # 0x81 is an OEM umlaut byte that cp1252 cannot decode. No decoding is needed.
        self.output(b'INFO: Es werden keine Aufgaben mit den angegebenen Kriterien ausgef\x81hrt.\r\n')
        self.assertEqual(launcher.start_game('beauty'), 43000)
        self.assertNotEqual(self.run.call_args.kwargs.get('text'), True)
        self.assertEqual((self.state / 'game.pid').read_text(encoding='ascii'), '43000')

    def test_null_stdout_reports_unavailable_process_status(self):
        self.output(None)
        with self.assertRaisesRegex(RuntimeError, 'keine verwertbare'):
            launcher.start_game('beauty')
        self.assert_no_launch_or_log_change()

    def test_empty_stdout_reports_unavailable_process_status(self):
        self.output(b'  \r\n')
        with self.assertRaisesRegex(RuntimeError, 'keine verwertbare'):
            launcher.start_game('beauty')
        self.assert_no_launch_or_log_change()

    def test_existing_openmw_pid_prevents_second_launch(self):
        self.output(b'"OpenMW.EXE","42000","Console","1","12.000 K"\r\n')
        with self.assertRaisesRegex(RuntimeError, 'l\u00e4uft bereits'):
            launcher.start_game('beauty')
        self.assert_no_launch_or_log_change()

    def test_unrelated_reused_pid_allows_new_launch(self):
        self.output(b'"other.exe","42000","Console","1","12.000 K"\r\n')
        self.assertEqual(launcher.start_game('beauty'), 43000)

    def test_openmw_with_different_pid_is_not_recorded_game(self):
        self.output(b'"openmw.exe","42001","Console","1","12.000 K"\r\n')
        self.assertEqual(launcher.start_game('beauty'), 43000)

    def test_failed_tasklist_does_not_start_another_process(self):
        self.output(None, returncode=1)
        with self.assertRaisesRegex(RuntimeError, 'fehlgeschlagen'):
            launcher.start_game('beauty')
        self.assert_no_launch_or_log_change()

    def test_first_start_needs_no_recorded_process_query(self):
        (self.state / 'game.pid').unlink()
        self.assertEqual(launcher.start_game('beauty'), 43000)
        self.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
