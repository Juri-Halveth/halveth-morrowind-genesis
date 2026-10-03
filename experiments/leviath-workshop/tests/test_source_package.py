"""Exercise the publication boundary with synthetic private-content fixtures."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/package.py'
spec = importlib.util.spec_from_file_location('workshop_package_checks', SOURCE)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class SourcePackageChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workshop-package-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        previous = package.ROOT
        self.addCleanup(setattr, package, 'ROOT', previous)
        package.ROOT = self.directory
        for relative in package.REQUIRED:
            target = self.directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('MIT License\n' if relative == 'LICENSE' else 'owned source fixture\n', encoding='utf8')

    def test_unknown_game_data_and_private_files_are_not_collected(self):
        for name in ('game.omwsave', 'Morrowind.esm', 'engine.dll', 'secrets.env'):
            (self.directory / name).write_bytes(b'not publishable')
        self.assertEqual(set(package.collect()), package.REQUIRED)

    def test_private_machine_path_in_allowed_source_is_rejected(self):
        fake_path = 'C:' + '/' + 'Users' + '/' + 'FIXTURE' + '/' + 'original.cfg'
        (self.directory / 'README.md').write_text(fake_path, encoding='utf8')
        with self.assertRaises(ValueError):
            package.collect()

    def test_private_key_or_access_token_in_allowed_source_is_rejected(self):
        for value in ('-----BEGIN ' + 'PRIVATE KEY-----', 'gh' + 'p_' + 'x' * 35):
            (self.directory / 'README.md').write_text(value, encoding='utf8')
            with self.assertRaises(ValueError):
                package.collect()

    def test_binary_bytes_in_allowed_text_are_rejected(self):
        (self.directory / 'README.md').write_bytes(b'owned prefix\x00private binary')
        with self.assertRaises(ValueError):
            package.collect()


if __name__ == '__main__':
    unittest.main(verbosity=2)
