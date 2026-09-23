import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'build_release.py'
SPEC = importlib.util.spec_from_file_location('genesis_source_release', SCRIPT)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class SourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(release, 'ROOT', self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temporary.cleanup()

    def put(self, name, content=b'fixture'):
        destination = self.root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    def test_only_exact_owned_art_assets_are_included(self):
        owned = {
            'mod/Textures/halveth/scarlet-love-banner.png',
            'mod/Textures/halveth/love-astrolabe-0.7.png',
            'installer/love-astrolabe-icon-0.8.png',
            'assets/ScarletLoveBanner/Textures/Tx_de_tapestry_02.tga',
            'assets/ScarletLoveBanner/Textures/Tx_de_tapestry_02.dds',
        }
        unexpected = {
            'mod/Textures/halveth/other-banner.png',
            'mod/Textures/halveth/scarlet-love-banner.dds',
            'mod/Textures/halveth/scarlet-love-banner.png.bak',
            'assets/ScarletLoveBanner/Textures/Tx_de_tapestry_03.dds',
            'assets/ScarletLoveBanner/Textures/Tx_de_tapestry_02.png',
            'assets/Other/Textures/Tx_de_tapestry_02.dds',
            'assets/ScarletLoveBanner/preview.png',
            'mod/Meshes/third-party.nif',
            'mod/third-party.esp',
            'mod/archive.bsa',
            'web/historical-screenshot.png',
            'web/downloaded-art.svg',
            'web/downloaded-font.woff2',
            'docs/historical-screenshot.jpeg',
        }
        for name in owned | unexpected:
            self.put(name, name.encode('utf-8'))
        packaged = release.collect_files()
        self.assertTrue(owned.issubset(packaged))
        self.assertFalse(unexpected.intersection(packaged))
        for name in owned:
            self.assertEqual(packaged[name], name.encode('utf-8'))

    def test_owned_data_code_and_optional_receipts_are_included(self):
        allowed = {
            'project_knowledge.py',
            'character_profile.py',
            'mod/Fonts/MysticCards.omwfont',
            'data/projects.json',
            'data/project-knowledge.json',
            'data/generation-providers.json',
            'data/native-content.json',
            'native/GenesisEntry.cs',
            'scripts/build_native_entry.py',
            'scripts/build_native_content.py',
            'mod/scripts/halveth/content_catalog.lua',
            'mod/scripts/halveth/content.lua',
            'mod/scripts/halveth/knowledge.lua',
            'mod/scripts/halveth/paths.lua',
            'mod/scripts/halveth/visuals.lua',
            'mod/scripts/halveth/perspective.lua',
            'mod/scripts/halveth/fieldcraft.lua',
            'mod/scripts/halveth/worldlife.lua',
            'mod/scripts/halveth/actor_life.lua',
            'mod/scripts/halveth/actor_life_global.lua',
            'tests/integration_actor_life.py',
            'tests/integration_perspective.py',
            'tests/integration_installer.py',
            'installer/GenesisSetup.csproj',
            'installer/Program.cs',
            'installer/build_installer.py',
            'installer/README.md',
            'installer/openmw-0.51.0-runtime-files.txt',
            'mod/shaders/halveth_atmosphere.omwfx',
            'scripts/convert-banner.mjs',
            'docs/GENERATION-PIPELINE.md',
            'docs/NATIVE-VERIFICATION-0.4.0.json',
            'docs/NATIVE-VERIFICATION-0.5.0.json',
            'docs/NATIVE-VERIFICATION-0.6.0.json',
            'docs/NATIVE-VERIFICATION-0.7.0.json',
            'docs/NATIVE-VERIFICATION-0.8.0.json',
            'docs/NATIVE-VERIFICATION-0.8.1.json',
            'docs/NATIVE-VERIFICATION-0.9.0.json',
            'PUBLIC-STATUS.json',
            'LICENSE',
            'LICENSES/CC0-1.0.txt',
            '.github/workflows/test.yml',
            'ASSET-PROVENANCE.json',
        }
        for name in allowed:
            self.put(name)
        self.assertTrue(allowed.issubset(release.collect_files()))
        (self.root / 'PUBLIC-STATUS.json').unlink()
        (self.root / 'ASSET-PROVENANCE.json').unlink()
        packaged = release.collect_files()
        self.assertNotIn('PUBLIC-STATUS.json', packaged)
        self.assertNotIn('ASSET-PROVENANCE.json', packaged)

    def test_only_the_original_native_shader_path_is_included(self):
        allowed = release.OWNED_SHADER
        unexpected = {
            'mod/shaders/downloaded.omwfx',
            'mod/shaders/halveth_atmosphere.omwfx.bak',
            'mod/other/halveth_atmosphere.omwfx',
            'assets/third-party.omwfx',
        }
        for name in {allowed} | unexpected:
            self.put(name, name.encode('utf-8'))
        packaged = release.collect_files()
        self.assertEqual(packaged[allowed], allowed.encode('utf-8'))
        self.assertFalse(unexpected.intersection(packaged))

    def test_private_runtime_and_unapproved_data_stay_out(self):
        private = {
            '.local/session.json',
            '.local/project_knowledge.py',
            'data/private-cards.json',
            'data/entity-sources.json',
            'data/graphics-install.json',
            'data/local-config.json',
            'mod/bridge/companion-status.json',
            'native/genesis-entry.json',
            'native/Morrowind-Workshop.exe',
            'docs/screenshots/history.md',
            'mod/saves/current.ess',
            'mod/profiles/user.omwscripts',
            'scripts/__pycache__/builder.pyc',
            'scripts/logs.log',
            'docs/logs/private-chat.md',
            'runtime/server.py',
            'assets/.local/ScarletLoveBanner/Textures/Tx_de_tapestry_02.dds',
            'BUILD-0.2.0.json',
            'BUILD-0.3.0.json',
            'BUILD-0.4.0.json',
            'BUILD-RESULT.json',
            'GRAPHICS-RESULT.json',
            'dist/scripts/old-source.py',
        }
        for name in private:
            self.put(name, b'PRIVATE_FIXTURE')
        self.put('data/entities.json', b'PRIVATE_ENTITY_FIXTURE')
        self.put('mod/bridge/inbox.json', b'PRIVATE_LIVE_COMMAND_FIXTURE')
        packaged = release.collect_files()
        self.assertFalse(private.intersection(packaged))
        self.assertEqual(json.loads(packaged['data/entities.json']), release.STARTER)
        self.assertEqual(json.loads(packaged['mod/bridge/inbox.json']),
                         {'sequence': 0, 'sessionId': ''})
        self.assertFalse(any(b'PRIVATE_' in value for value in packaged.values()))

    def test_version_and_release_note_describe_owned_additions(self):
        self.assertEqual(release.VERSION, '0.9.0')
        self.assertEqual(release.DEST.name, 'HALVETH-Morrowind-Genesis-0.9.0-public-source.zip')
        note = release.collect_files()['RELEASE-NOTE.txt'].decode('utf-8')
        self.assertIn('8 original paraphrased cards', note)
        self.assertIn('original generated Scarlet Love banner', note)
        self.assertIn('no copied source registry, Bethesda assets', note)
        self.assertIn('Only the 5 exact owned art asset paths and the one original shader source path', note)
        self.assertIn('six original native books', note)
        self.assertIn('three native spells', note)
        self.assertIn('native exploration paths', note)
        self.assertIn('alchemy recipe planner', note)
        self.assertIn('native Sammelatlas', note)
        self.assertIn('native observed-NPC worldlife journal', note)
        self.assertIn('native first-person, third-person and free-look camera panel', note)
        self.assertIn('MIT',note)
        self.assertIn('CC0-1.0',note)
        self.assertNotIn('LICENSE-DECISION',note)


class PublicValidationTests(unittest.TestCase):
    def test_current_public_tree_has_bound_assets_and_licenses(self):
        files=release.collect_files()
        result=release.validate_files(files)
        self.assertEqual(result['assetCount'],5)
        self.assertNotIn('BUILD-RESULT.json',files)

    def test_changed_asset_bytes_fail_provenance_check(self):
        files=release.collect_files()
        files['mod/Textures/halveth/scarlet-love-banner.png']+=b'changed'
        with self.assertRaisesRegex(ValueError,'provenance mismatch'):
            release.validate_files(files)

    def test_missing_license_stops_release(self):
        files=release.collect_files()
        del files['LICENSES/CC0-1.0.txt']
        with self.assertRaisesRegex(ValueError,'Missing public release'):
            release.validate_files(files)

    def test_machine_path_in_document_stops_release(self):
        files=release.collect_files()
        files['README.md']=('C:'+chr(92)+'Users'+chr(92)+'private-user'+chr(92)+'document').encode()
        with self.assertRaisesRegex(ValueError,'Machine-specific path'):
            release.validate_files(files)

    def test_missing_native_knowledge_code_stops_release(self):
        files=release.collect_files()
        del files['mod/scripts/halveth/knowledge.lua']
        with self.assertRaisesRegex(ValueError,'Missing public release'):
            release.validate_files(files)

    def test_missing_original_shader_stops_release(self):
        files=release.collect_files()
        del files[release.OWNED_SHADER]
        with self.assertRaisesRegex(ValueError,'Missing public release'):
            release.validate_files(files)

    def test_live_companion_status_cannot_be_added_to_public_snapshot(self):
        files=release.collect_files()
        files['mod/bridge/companion-status.json']=b'{"status":"available"}'
        with self.assertRaisesRegex(ValueError,'Runtime companion status'):
            release.validate_files(files)


if __name__ == '__main__':
    unittest.main()
