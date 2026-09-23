"""Launcher process checks with synthetic Windows output; never starts a game."""
from contextlib import ExitStack
import argparse
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
import io
import json
import os
from contextlib import redirect_stderr
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import launcher
from scripts import prepare_profile


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
        self.stack.enter_context(patch.object(launcher, 'BRIDGE_STATUS', self.state / 'bridge' / 'companion-status.json'))
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

    def test_companion_failure_starts_real_game_offline_and_preserves_error(self):
        (self.state / 'game.pid').unlink()
        with patch.object(launcher, 'companion', side_effect=RuntimeError('local service unavailable')), \
                patch.object(launcher, 'prepare', return_value={
                    'command': ['existing-openmw'], 'cwd': str(self.state),
                }) as prepare:
            self.assertEqual(launcher.start_game('beauty'), 43000)
        prepare.assert_called_once_with('beauty')
        self.assertEqual(self.spawn.call_args.args[0], ['existing-openmw'])
        self.assertIn('local service unavailable', (self.state / 'companion-start-errors.log').read_text())
        self.assertIn('"status": "offline"', (self.state / 'companion-availability.json').read_text())
        self.assertEqual(json.loads((self.state / 'bridge' / 'companion-status.json').read_text()),
                         {'status': 'offline'})

    def test_missing_game_inputs_still_fail_instead_of_faking_success(self):
        with patch.object(launcher, 'companion', side_effect=RuntimeError('service failed')), \
                patch.object(launcher, 'prepare', side_effect=FileNotFoundError('game assets missing')):
            with self.assertRaisesRegex(FileNotFoundError, 'game assets missing'):
                launcher.start_game('beauty')
        self.assert_no_launch_or_log_change()


class DirectEntryTests(unittest.TestCase):
    def test_play_enters_existing_game_without_tkinter_or_browser(self):
        with patch.object(launcher, 'start_game', return_value=1234) as start, \
                patch('webbrowser.open') as browser, \
                patch.dict(sys.modules, {'tkinter': None}):
            self.assertEqual(launcher.main(['--play']), 0)
        start.assert_called_once_with('beauty')
        browser.assert_not_called()


    def test_play_passes_each_supported_graphics_profile(self):
        for profile in ('original', 'beauty', 'cinematic'):
            with self.subTest(profile=profile), patch.object(launcher, 'start_game') as start:
                self.assertEqual(launcher.main(['--play', '--profile', profile]), 0)
                start.assert_called_once_with(profile)

    def test_companion_only_mode_cannot_be_combined_with_direct_play(self):
        with patch.object(launcher, 'start_game') as start, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                launcher.main(['--play', '--companion-only'])
        self.assertEqual(result.exception.code, 2)
        start.assert_not_called()

    def test_play_start_failure_is_visible_to_native_parent(self):
        with patch.object(launcher, 'start_game', side_effect=RuntimeError('startup failed')):
            with self.assertRaisesRegex(RuntimeError, 'startup failed'):
                launcher.main(['--play'])

    def test_default_entry_also_starts_game_without_browser_or_tk(self):
        with patch.object(launcher, 'start_game') as start, patch('webbrowser.open') as browser, \
                patch.dict(sys.modules, {'tkinter': None}):
            self.assertEqual(launcher.main([]), 0)
        start.assert_called_once_with('beauty')
        browser.assert_not_called()

    def test_companion_only_is_a_hidden_service_start(self):
        with patch.object(launcher, 'companion') as companion, patch.object(launcher, 'start_game') as game, \
                patch('webbrowser.open') as browser:
            self.assertEqual(launcher.main(['--companion-only']), 0)
        companion.assert_called_once_with('beauty')
        game.assert_not_called()
        browser.assert_not_called()


class InstalledProfileTests(unittest.TestCase):
    def test_direct_play_preparation_never_copies_existing_saves_by_default(self):
        with patch.dict(os.environ, {'HALVETH_MORROWIND_INSTALL_ROOT': ''}), \
                patch('scripts.prepare_profile.prepare', return_value={}) as prepare:
            launcher.prepare('beauty')
        self.assertFalse(prepare.call_args.args[0].copy_saves)

    def test_installer_can_bind_an_explicit_engine_root_without_changing_user_config(self):
        engine = Path(tempfile.gettempdir()) / 'halveth-openmw-engine-example'
        with patch.dict(os.environ, {'HALVETH_MORROWIND_INSTALL_ROOT': str(engine)}), \
                patch('scripts.prepare_profile.prepare', return_value={}) as prepare:
            launcher.prepare('beauty')
        self.assertEqual(prepare.call_args.args[0].install_root, engine.resolve())
        self.assertFalse(prepare.call_args.args[0].copy_saves)

    def test_bundled_engine_allows_only_its_own_app_state_inside_install_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            install = Path(temp) / 'bundle'
            app = install / 'app'
            engine = install / 'engine'
            engine.mkdir(parents=True)
            (engine / ('openmw.exe' if os.name == 'nt' else 'openmw')).write_bytes(b'fixture')
            args = argparse.Namespace(install_root=install, state_dir=app / '.local',
                                      profile='beauty', source_profile='max', smoke=False,
                                      copy_saves=False, reset_settings=False)
            with patch.object(prepare_profile, 'PROJECT', app):
                # Missing fixture profile is the next expected error: the state
                # guard itself must accept this exact bundled layout.
                with self.assertRaises(FileNotFoundError):
                    prepare_profile.prepare(args)
                args.state_dir = install / 'engine' / '.local'
                with self.assertRaisesRegex(ValueError, 'outside the original installation'):
                    prepare_profile.prepare(args)


if __name__ == '__main__':
    unittest.main()
