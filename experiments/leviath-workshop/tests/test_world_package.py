"""Check the own-world publication boundary against disposable exact file copies."""
from pathlib import Path
import importlib.util,json,tempfile,unittest

SOURCE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('world_package_tests',SOURCE/'scripts/package-world.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


class WorldPackageTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='own-world-package-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        names=package.legacy.REQUIRED|package.NEW_TEXT|package.ASSETS|package.NATIVE_FILES
        for n in names:
            p=SOURCE/n
            if p.is_file():
                q=self.root/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
        previous=package.ROOT;package.ROOT=self.root;self.addCleanup(setattr,package,'ROOT',previous)

    def test_exact_owned_asset_closure_does_not_collect_proprietary_or_unknown_data(self):
        for n in ('Morrowind.esm','original.omwsave','private.cfg','unknown-asset.dds'):(self.root/n).write_bytes(b'EXCLUDED_FIXTURE')
        files=package.collect(False)
        self.assertTrue(package.ASSETS<=files.keys())
        self.assertNotIn('Morrowind.esm',files);self.assertNotIn('unknown-asset.dds',files)
        self.assertEqual(package.manifest(files,False)['nativeInclusion'],'CANDIDATE_INSPECTION_NATIVE_GATES_NOT_ENFORCED')

    def test_changed_pinned_owned_dds_is_rejected(self):
        n='presentation/frontier-texture-candidate/mod/Textures/veyra/frontier/frontier_stone.dds'
        p=self.root/n;p.write_bytes(p.read_bytes()+b'CHANGED')
        with self.assertRaisesRegex(ValueError,'Owned asset bytes/license differ'):package.collect(False)

    def test_manifest_cannot_expand_binary_allowlist(self):
        p=self.root/'docs/OWN_ASSET_BINDINGS.json';j=json.loads(p.read_bytes())
        j['assets']['unknown-own-claim.dds']={'license':'MIT'};p.write_text(json.dumps(j),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'exact authored allowlist'):package.collect(False)

    def test_missing_generator_or_new_source_rejects_incomplete_package(self):
        p=self.root/'presentation/plaza-candidate/build-plaza.py';p.unlink()
        with self.assertRaisesRegex(ValueError,'Required regular publication file missing'):package.collect(False)

    def test_changed_overlay_requires_fresh_native_source_binding(self):
        p=self.root/'gameplay/panels/mod/scripts/veyra_panels/player.lua';p.write_text('OWN_UNTESTED_OVERLAY_CHANGE',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'native receipt/source binding differs|UI overlay closure differs'):
            package.collect(False)

    def test_missing_native_inclusion_cannot_be_an_accepted_release(self):
        p=self.root/'docs/HUD014_NATIVE.json'
        if p.exists():p.unlink()
        with self.assertRaisesRegex(ValueError,'Required regular publication file missing'):package.collect(True)
        self.assertEqual(list(self.root.glob('*.zip')),[])

    def test_separate_cc0_complete_legal_text_is_required_by_derivative_binding(self):
        p=self.root/'presentation/bark-materials/CC0-1.0.txt';p.write_text('OWN_REPLACEMENT_LICENSE_FIXTURE',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'CC0 license/provenance closure differs'):package.collect(False)

    def test_missing_new_profile_native_gate_blocks_release_despite_individual_units(self):
        p=self.root/'docs/PROVISION_WORLD_NATIVE.json'
        if p.exists():p.unlink()
        with self.assertRaisesRegex(ValueError,'Required regular publication file missing'):package.collect(True)
        self.assertTrue(package.ASSETS<=package.collect(False).keys())

    def test_native_status_cannot_default_to_accepted_for_a_structure_only_record(self):
        p=self.root/'docs/PROVISION_WORLD_NATIVE.json';p.parent.mkdir(parents=True,exist_ok=True)
        source='scripts/provision-world.py'
        j={'moduleHashes':{source:package.sha((self.root/source).read_bytes())}}
        p.write_text(json.dumps(j),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'native inclusion gate remains pending'):package.collect(True)

    def test_selected_cc0_audio_bytes_are_exactly_bound_and_mutation_rejected(self):
        p=self.root/'presentation/spatial-audio/mod/Sound/veyra/courier_bell_mono.wav'
        self.assertEqual(package.sha(p.read_bytes()),'faa557bc6e4cd2c5c3c3b22ba8e78e9c7af35e7ab11e8cbaf5607f6ce177479c')
        p.write_bytes(p.read_bytes()+b'OWN_CHANGED_AUDIO_FIXTURE')
        with self.assertRaisesRegex(ValueError,'Owned asset bytes/license differ'):package.collect(False)

    def test_wildlife_remains_separate_source_only_and_cannot_expand_to_models(self):
        files=package.collect(False)
        self.assertIn('prototypes/wildlife-source-only/build-creature.py',files)
        self.assertFalse(any(n.startswith('prototypes/wildlife-source-only/mod/Meshes/') for n in files))
        p=self.root/'prototypes/wildlife-source-only/SOURCE_BINDING.json';j=json.loads(p.read_bytes())
        j['installationModule']=True;p.write_text(json.dumps(j),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Prototype source-only/default-off scope differs'):package.collect(False)

    def test_new_normal_profile_record_cannot_silently_become_a_debug_probe(self):
        p=self.root/'docs/PROVISION_WORLD_NATIVE.json';j=json.loads(p.read_bytes())
        j['debugFixtureRegistered']=True;p.write_text(json.dumps(j),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'normal native run is incomplete or debug-derived'):package.collect(True)

    def test_core_keeps_logged_and_distinct_names_and_private_derivation_separate(self):
        p=self.root/'docs/CORE_NATIVE.json';j=json.loads(p.read_bytes())
        self.assertEqual(j['loggedPassCount'],149);self.assertEqual(j['distinctAssertionCount'],144)
        j['distinctAssertionCount']=149;p.write_text(json.dumps(j),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'logged/distinct counts differ'):package.collect(True)


if __name__=='__main__':unittest.main(verbosity=2)
