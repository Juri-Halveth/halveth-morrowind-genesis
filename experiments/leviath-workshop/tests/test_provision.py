"""Exercise an installer only against disposable input fixtures, never OpenMW."""
from pathlib import Path
import importlib.util
import os
import tempfile
import subprocess
import sys
import json
import shutil
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/provision.py'
spec = importlib.util.spec_from_file_location('owned_provision_checks', SOURCE)
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


class ProvisionChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='workshop-provision-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.base = self.root / 'base profile with spaces'
        self.base.mkdir()
        self.engine_root = self.root / 'external runtime'
        self.engine_root.mkdir()
        resources = self.engine_root / 'resources'
        resources.mkdir()
        (resources / 'vfs-mw').mkdir()
        self.engine = self.engine_root / 'openmw.exe'
        self.engine.write_bytes(b'OWN_NON_EXECUTABLE_ENGINE_FIXTURE')
        self.bootstrap = self.engine_root / 'openmw.cfg'
        self.bootstrap.write_text('resources=./resources\ndata=./resources/vfs-mw\nfallback=Fixture_Default,1\nfallback=Fixture_Second,2\n', encoding='utf8')
        self.link = self.root / 'base runtime hardlink'
        os.link(self.bootstrap, self.link)
        for name in ('Data one', 'Data two'):
            (self.root / name).mkdir()
        (self.base / 'existing local assets').mkdir()
        self.base_config = self.base / 'openmw.cfg'
        self.base_config.write_text(
            'data="../Data one"\ncontent=Morrowind.esm\nfallback=Own_First,3\ndata="../Data two"\n'
            'content=Extra.esp\nfallback=Own_Second,4\nfallback-archive=Morrowind.bsa\nencoding=win1252\n'
            'data-local="existing local assets"\n', encoding='utf8')
        self.base_config_link = self.root / 'base profile hardlink.cfg'
        os.link(self.base_config, self.base_config_link)
        (self.base / 'settings.cfg').write_bytes(b'[Video]\r\nresolution x = 1920\r\n')
        self.destination = self.root / 'new own installation'
        self.bound_originals = {path: path.read_bytes() for path in
                                (self.base_config, self.base_config_link, self.base / 'settings.cfg', self.bootstrap, self.engine, self.link)}

    def plan(self, destination=None, modules=('courier', 'fieldwork')):
        return provision.make_plan(self.base, self.engine, destination or self.destination, modules)

    def assert_originals(self):
        for path, raw in self.bound_originals.items():
            self.assertEqual(path.read_bytes(), raw)
        self.assertTrue(os.path.samefile(self.bootstrap, self.link))
        self.assertTrue(os.path.samefile(self.base_config, self.base_config_link))

    def test_plan_is_read_only_and_apply_copies_dependency_closed_modules(self):
        plan = self.plan()
        self.assertFalse(self.destination.exists())
        self.assert_originals()
        receipt = provision.apply_plan(plan)
        self.assertEqual(receipt['nativeAcceptance'], 'NOT_RUN')
        cfg = (self.destination / 'profile/openmw.cfg').read_text()
        self.assertEqual(cfg, (self.destination / 'profile/play.cfg').read_text())
        self.assertLess(cfg.index('Data one'), cfg.index('Data two'))
        self.assertLess(cfg.index('content=Morrowind.esm'), cfg.index('content=Extra.esp'))
        self.assertIn('replace=fallback\n', cfg)
        self.assertLess(cfg.index('fallback=Fixture_Default,1'), cfg.index('fallback=Fixture_Second,2'))
        self.assertLess(cfg.index('fallback=Fixture_Second,2'), cfg.index('fallback=Own_First,3'))
        self.assertLess(cfg.index('fallback=Own_First,3'), cfg.index('data="' + (self.root / 'Data two').as_posix()))
        self.assertLess(cfg.index('content=Extra.esp'), cfg.index('fallback=Own_Second,4'))
        self.assertEqual(cfg.count('content=veyra-courier.omwscripts'), 1)
        self.assertEqual(cfg.count('content=veyra-fieldwork.omwscripts'), 1)
        self.assertIn((self.destination / 'profile/user').as_posix(), cfg)
        self.assertIn((self.destination / 'profile/data').as_posix(), cfg)
        self.assertIn('data="' + (self.base / 'existing local assets').as_posix() + '"', cfg)
        self.assertNotIn('data-local="' + (self.base / 'existing local assets').as_posix() + '"', cfg)
        for row in plan['payload']:
            copy = self.destination / row['destination']
            self.assertEqual(provision.digest(copy.read_bytes()), row['sha256'])
            self.assertFalse(os.path.samefile(copy, row['path']))
        self.assert_originals()

    def test_destination_existing_nested_or_aliased_is_rejected_before_writing(self):
        for forbidden in (self.base / 'nested', self.engine_root / 'nested', self.root,
                          self.root / 'Data one/new', provision.ROOT / 'OWN_BOUND_DESTINATION_TEST'):
            with self.assertRaises(ValueError):
                self.plan(forbidden)
        existing = self.root / 'already exists'
        existing.mkdir()
        marker = existing / 'retained'
        marker.write_bytes(b'KEEP')
        with self.assertRaises(ValueError):
            self.plan(existing)
        self.assertEqual(marker.read_bytes(), b'KEEP')
        alias = self.root / 'profile alias'
        try:
            os.symlink(self.base, alias, target_is_directory=True)
        except OSError:
            pass  # Some Windows test users lack symlink creation capability.
        else:
            with self.assertRaises(ValueError):
                self.plan(alias / 'new')
        self.assert_originals()

    def test_changed_input_between_plan_and_apply_is_rejected_without_output(self):
        plan = self.plan()
        self.base_config.write_text('content=changed.esm\n', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'bound input changed'):
            provision.apply_plan(plan)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob('*.stage-*')), [])

    def test_partial_copy_failure_removes_only_owned_stage(self):
        plan = self.plan()
        original_copy = provision.copy_owned_file
        calls = 0

        def fail_second(row, stage):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('OWN_SYNTHETIC_COPY_FAILURE')
            original_copy(row, stage)

        with mock.patch.object(provision, 'copy_owned_file', fail_second):
            with self.assertRaises(OSError):
                provision.apply_plan(plan)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob('*.stage-*')), [])
        self.assert_originals()

    def test_probe_nested_config_unknown_modules_and_unbuilt_audio_are_rejected(self):
        for content in ('content=own-probe.omwscripts\n', 'config=../another\n', 'script-run=commands.txt\n'):
            self.base_config.write_text(content, encoding='utf8')
            with self.assertRaises(ValueError):
                self.plan()
        self.base_config.write_bytes(self.bound_originals[self.base_config])
        with self.assertRaises(ValueError):
            self.plan(modules=('unknown',))
        # Supply only own source fixtures; no WAV or receipt has been generated.
        source_only = self.root / 'own source only'
        source_only.mkdir()
        (source_only / 'LICENSE').write_text('MIT License\n', encoding='utf8')
        folder, registration, scripts = provision.MODULES['audio']
        for relative in (registration, *scripts):
            if relative.endswith('.wav'):
                continue
            fixture = source_only / folder / 'mod' / relative
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text('OWN_SOURCE_FIXTURE\n', encoding='utf8')
        with mock.patch.object(provision, 'ROOT', source_only):
            with self.assertRaisesRegex(ValueError, 'Required regular input missing'):
                self.plan(modules=('audio',))

    def test_hud_build_happens_only_in_new_owned_module_copy(self):
        source_png = provision.ROOT / 'presentation/mod/Textures/veyra/white.png'
        before = source_png.read_bytes() if source_png.exists() else None
        provision.apply_plan(self.plan(modules=('hud',)))
        installed = self.destination / 'modules/hud/mod/Textures/veyra/white.png'
        self.assertEqual(provision.digest(installed.read_bytes()), provision.WHITE_SHA)
        after = source_png.read_bytes() if source_png.exists() else None
        self.assertEqual(before, after)
        self.assert_originals()

    def test_bash_wrapper_spaces_and_reviewed_plan_mismatch(self):
        bash = os.environ.get('WORKSHOP_BASH') or shutil.which('bash')
        if bash is None:
            self.skipTest('Bash is unavailable')
        wrapper = SOURCE.with_suffix('.sh')
        command = [str(bash), str(wrapper), 'plan', '--base-profile', str(self.base),
                   '--engine', str(self.engine), '--destination', str(self.destination),
                   '--modules', 'courier,fieldwork']
        env = {**os.environ, 'WORKSHOP_PYTHON': sys.executable}
        run = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        plan = json.loads(run.stdout)
        self.assertEqual(Path(plan['baseProfile']), self.base.resolve())
        self.assertEqual(Path(plan['engine']), self.engine.resolve())
        self.assertEqual(plan['engineExecution'], 'NOT_REQUESTED')
        command[2] = 'apply'
        rejected = subprocess.run(command + ['--expect-plan', '0' * 64],
                                  env=env, capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('differs from the reviewed digest', rejected.stderr)
        self.assertFalse(self.destination.exists())
        self.assert_originals()

    def test_optional_shader_and_key_bindings_are_distinct_bound_copies(self):
        shaders = self.base / 'shaders.yaml'
        bindings = self.base / 'input_v3.xml'
        shaders.write_bytes(b'chain:\n  - own_color\n')
        bindings.write_bytes(b'<OpenMW><KeyBinding fixture="owned" /></OpenMW>\n')
        alias = self.root / 'bindings hardlink.xml'
        os.link(bindings, alias)
        originals = {path: path.read_bytes() for path in (shaders, bindings, alias)}
        self.bound_originals.update(originals)
        for excluded in ('global_storage.bin', 'player_storage.bin', 'openmw.log', 'manual.omwsave'):
            (self.base / excluded).write_bytes(b'PRIVATE_NOT_FOR_AUTOMATIC_COPY')
        plan = self.plan()
        self.assertEqual(plan['optionalProfileCopies'], ['shaders.yaml', 'input_v3.xml'])
        provision.apply_plan(plan)
        for path in (shaders, bindings):
            copy = self.destination / 'profile' / path.name
            self.assertEqual(copy.read_bytes(), originals[path])
            self.assertFalse(os.path.samefile(copy, path))
        self.assertTrue(os.path.samefile(bindings, alias))
        for excluded in ('global_storage.bin', 'player_storage.bin', 'openmw.log', 'manual.omwsave'):
            self.assertFalse((self.destination / 'profile' / excluded).exists())
        self.assert_originals()


if __name__ == '__main__':
    unittest.main(verbosity=2)
