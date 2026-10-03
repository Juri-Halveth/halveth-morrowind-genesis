"""Exercise configuration restoration and verified download failures without OpenMW/network."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get('WORKSHOP_BASH') or shutil.which('bash')


def path(value):
    return Path(value).as_posix()


class BashTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='leviath-workshop-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.profile = self.directory / 'Profile with spaces'
        (self.profile / 'runtime').mkdir(parents=True)
        self.original = b'content=Morrowind.esm\r\ncontent=world-test.omwscripts\r\n'
        (self.profile / 'openmw.cfg').write_bytes(self.original)
        (self.profile / 'play.cfg').write_text('content=Morrowind.esm\n', encoding='utf8')
        (self.profile / 'settings.cfg').write_text('[Video]\n', encoding='utf8')
        self.engine = self.profile / 'runtime' / 'engine-fixture.sh'
        self.engine.write_text(
            '#!/usr/bin/env bash\nset -eu\ncat ../openmw.cfg\n'
            'printf "ARGUMENT:%s\\n" "$@"\nexit "${ENGINE_EXIT:-0}"\n', encoding='utf8')
        self.engine.chmod(0o755)
        self.env = os.environ.copy()
        self.env['WORKSHOP_ENGINE'] = path(self.engine)
        self.fixture = self.directory / 'fixture.txt'
        self.fixture.write_bytes(b'owned source fixture\n')
        self.manifest = self.directory / 'sources.tsv'
        self.hash = hashlib.sha256(self.fixture.read_bytes()).hexdigest()
        self.manifest.write_text(
            f'fixture\t{self.hash}\thttps://example.test/fixture\tfixture.bin\tMIT\n', encoding='utf8')
        self.curl = self.directory / 'curl-fixture.sh'
        self.curl.write_text(
            '#!/usr/bin/env bash\nset -eu\noutput=""\n'
            'while [[ $# -gt 0 ]]; do\n'
            ' if [[ "$1" == --output ]]; then shift; output=$1; fi\n shift\ndone\n'
            'cp -- "$FIXTURE_CONTENT" "$output"\nexit "${CURL_EXIT:-0}"\n', encoding='utf8')
        self.curl.chmod(0o755)
        self.env.update(WORKSHOP_ASSET_MANIFEST=path(self.manifest),
                        WORKSHOP_CURL=path(self.curl), FIXTURE_CONTENT=path(self.fixture))
        self.destination = self.directory / 'Assets with spaces'

    def run_bash(self, script, *arguments):
        self.assertTrue(BASH, 'Bash is required for these tests')
        return subprocess.run([BASH, path(ROOT / 'scripts' / script), *map(str, arguments)],
                              env=self.env, text=True, capture_output=True, timeout=20)

    def assert_restored(self):
        self.assertEqual((self.profile / 'openmw.cfg').read_bytes(), self.original)
        self.assertFalse((self.profile / 'play.lock').exists())
        self.assertEqual(list(self.profile.glob('openmw.cfg.next.*')), [])

    def test_play_spaces_and_configuration_restoration(self):
        result = self.run_bash('workshop.sh', 'play', path(self.profile))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('content=Morrowind.esm', result.stdout)
        self.assertNotIn('world-test.omwscripts', result.stdout)
        self.assertNotIn('--load-savegame', result.stdout)
        self.assert_restored()

    def test_engine_failure_restores_configuration_and_returns_failure(self):
        self.env['ENGINE_EXIT'] = '73'
        result = self.run_bash('workshop.sh', 'play', path(self.profile))
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assert_restored()

    def test_failed_play_configuration_copy_restores_and_removes_lock(self):
        fake_cp = self.directory / 'copy-failure-fixture.bash'
        fake_cp.write_text(
            'cp() {\n'
            'for value in "$@"; do\n'
            ' if [[ "$value" == */play.cfg ]]; then return 72; fi\ndone\n'
            '"$REAL_CP" "$@"\n}\n', encoding='utf8')
        self.env['REAL_CP'] = path(shutil.which('cp'))
        self.env['BASH_ENV'] = path(fake_cp)
        result = self.run_bash('workshop.sh', 'play', path(self.profile))
        self.assertEqual(result.returncode, 72, result.stderr)
        self.assert_restored()

    def test_probe_configuration_is_rejected_before_lock(self):
        for line in ('content=world-test.omwscripts\n', 'content=courier-probe.omwscripts\n',
                     'script-run=commands.txt\n', 'skip-menu=true\n'):
            (self.profile / 'play.cfg').write_text(line, encoding='utf8')
            result = self.run_bash('workshop.sh', 'play', path(self.profile))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assert_restored()

    def test_existing_lock_is_retained(self):
        lock = self.profile / 'play.lock'
        lock.mkdir()
        result = self.run_bash('workshop.sh', 'play', path(self.profile))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(lock.is_dir())
        self.assertEqual((self.profile / 'openmw.cfg').read_bytes(), self.original)

    def test_explicit_save_is_forwarded_once(self):
        save = self.directory / 'manual save.omwsave'
        save.write_text('test fixture only', encoding='utf8')
        result = self.run_bash('workshop.sh', 'play', path(self.profile), path(save))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('ARGUMENT:--load-savegame'), 1)
        self.assertIn('manual save.omwsave', result.stdout)
        self.assert_restored()

    def test_plan_is_read_only_and_missing_profile_fails(self):
        result = self.run_bash('workshop.sh', 'plan', path(self.profile))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_restored()
        result = self.run_bash('workshop.sh', 'plan', path(self.directory / 'missing'))
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_unknown_command_is_not_success(self):
        self.assertEqual(self.run_bash('workshop.sh', 'unknown').returncode, 2)

    def test_download_is_verified_and_reused(self):
        result = self.run_bash('fetch-assets.sh', 'fetch', 'fixture', path(self.destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / 'fixture.bin').read_bytes(), self.fixture.read_bytes())
        self.env['CURL_EXIT'] = '22'
        result = self.run_bash('fetch-assets.sh', 'fetch', 'fixture', path(self.destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('VERIFIED EXISTING', result.stdout)

    def test_mismatched_download_is_removed(self):
        self.fixture.write_bytes(b'wrong bytes')
        result = self.run_bash('fetch-assets.sh', 'fetch', 'fixture', path(self.destination))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_failed_download_partial_is_removed(self):
        self.env['CURL_EXIT'] = '22'
        result = self.run_bash('fetch-assets.sh', 'fetch', 'fixture', path(self.destination))
        self.assertEqual(result.returncode, 22, result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_existing_wrong_bytes_are_retained(self):
        self.destination.mkdir()
        existing = self.destination / 'fixture.bin'
        existing.write_bytes(b'preserve for review')
        result = self.run_bash('fetch-assets.sh', 'fetch', 'fixture', path(self.destination))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(existing.read_bytes(), b'preserve for review')

    def test_unknown_asset_and_non_https_are_rejected_before_download(self):
        result = self.run_bash('fetch-assets.sh', 'fetch', 'unknown', path(self.destination))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.destination.exists())
        self.manifest.write_text(
            f'fixture\t{self.hash}\thttp://example.test/fixture\tfixture.bin\tMIT\n', encoding='utf8')
        result = self.run_bash('fetch-assets.sh', 'fetch', 'fixture', path(self.destination))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.destination.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
