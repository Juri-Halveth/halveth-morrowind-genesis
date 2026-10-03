"""MIT. Disposable publication boundary regressions; no engine execution."""
from pathlib import Path
import importlib.util,json,os,shutil,subprocess,tempfile,unittest,zipfile
from unittest import mock

SOURCE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('refinement_publication_tests',SOURCE/'scripts/package-refinements.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
PARENT=Path(os.environ.get('REFINEMENTS_PARENT_ROOT',str(SOURCE.parent/'leviath-workshop')))

class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='own-refinement-test-');self.addCleanup(temp.cleanup)
        self.temp=Path(temp.name);self.root=self.temp/'own-package'
        shutil.copytree(SOURCE,self.root)
        patch=mock.patch.object(package,'ROOT',self.root);patch.start();self.addCleanup(patch.stop)
        self.parent_before=(PARENT/'scripts/provision-world.py').read_bytes()

    def collect(self,names=('crown',),inspect=False):return package.collect(names,PARENT,inspect)

    def rewrite(self,name,change):
        p=self.root/name;data=json.loads(p.read_bytes());change(data)
        p.write_bytes((json.dumps(data,indent=2)+'\n').encode('utf8'))

    def test_crown_exact_selected_closure_and_native_asset_binding(self):
        files,selected=self.collect();self.assertEqual(selected,('crown',));self.assertEqual(len(files),21)
        self.assertNotIn('wildlife-0.1.1/mod/Veyra-Wildlife.omwscripts',files)
        self.assertEqual(files['crown-0.1.1/mod/Veyra-Crown-Refinement-011.esp'][:4],b'TES3')
        self.assertEqual((PARENT/'scripts/provision-world.py').read_bytes(),self.parent_before)

    def test_selected_unpassed_sibling_rejects_without_downgrade(self):
        self.rewrite('evidence/WILDLIFE_NATIVE.json',lambda d:d.update(status='PENDING',nativeInclusionGate='PENDING'))
        with self.assertRaisesRegex(ValueError,'native gate pending'):self.collect(('crown','wildlife'))
        files,names=self.collect();self.assertNotIn('evidence/WILDLIFE_NATIVE.json',files)

    def test_pending_inspection_is_explicit_and_archive_cli_rejects_it(self):
        files,names=self.collect(('wildlife',),True)
        self.assertEqual(package.manifest(files,names,True)['nativeInclusion'],'CANDIDATE_INSPECTION_ONLY')
        with self.assertRaisesRegex(ValueError,'Pending inspection'):
            package.archive(self.temp/'pending.zip',files,package.manifest(files,names,True))
        self.assertFalse((self.temp/'pending.zip').exists())

    def test_missing_native_receipt_rejects(self):
        (self.root/'evidence/CROWN_NATIVE.json').unlink()
        with self.assertRaisesRegex(ValueError,'Required bounded regular file'):self.collect()

    def test_old_native_source_label_cannot_bind_new_model(self):
        self.rewrite('evidence/CROWN_NATIVE.json',lambda d:d['moduleHashes'].update({next(iter(d['moduleHashes'])):'0'*64}))
        with self.assertRaisesRegex(ValueError,'different selected production'):self.collect()

    def test_false_preservation_flag_is_not_accepted(self):
        self.rewrite('evidence/CROWN_NATIVE.json',lambda d:d.update(configurationSettingsAndInputSaveRestored=False))
        with self.assertRaisesRegex(ValueError,'preservation predicate'):self.collect()

    def test_logged_and_distinct_assertion_counts_cannot_be_relabelled(self):
        self.rewrite('evidence/CROWN_NATIVE.json',lambda d:d.update(distinctAssertionNames=393))
        with self.assertRaisesRegex(ValueError,'logged/distinct'):self.collect()

    def test_parent_manifest_tamper_rejects_before_inputs(self):
        self.rewrite('PARENT_BINDINGS.json',lambda d:d['parentFiles'][0].update(sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'Fixed 215-file parent'):self.collect()

    def test_changed_parent_bytes_in_a_disposable_full_parent_are_rejected(self):
        copied=self.temp/'own-parent-copy';shutil.copytree(PARENT,copied)
        p=copied/'scripts/provision-world.py';p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'Bound parent bytes changed'):package.collect(('crown',),copied)
        self.assertEqual((PARENT/'scripts/provision-world.py').read_bytes(),self.parent_before)

    def test_changed_asset_and_license_cannot_self_grant(self):
        p=self.root/'crown-0.1.1/mod/Textures/veyra/crown_leaf_refined_011.dds';p.write_bytes(p.read_bytes()+b'OWN_CHANGE')
        with self.assertRaisesRegex(ValueError,'Fixed reviewed source'):self.collect()

    def test_separate_cc0_legal_text_remains_exact(self):
        p=self.root/'crown-0.1.1/bark-closure/CC0-1.0.txt';p.write_bytes(b'OWN_REPLACEMENT_NOT_CC0_LEGAL_TEXT')
        with self.assertRaisesRegex(ValueError,'license/provenance'):self.collect()

    def test_unknown_file_is_rejected_even_when_not_selected(self):
        (self.root/'unreviewed.esp').write_bytes(b'OWN_NOT_ALLOWED')
        with self.assertRaisesRegex(ValueError,'Unknown publication file'):self.collect()

    def test_private_path_and_token_in_public_document_reject(self):
        p=self.root/'README.md';before=p.read_bytes()
        drive='C'+chr(58)+chr(47)+'Users'+chr(47)+'private'
        p.write_text(drive,encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Private path/key/token'):self.collect()
        p.write_bytes(before+b'\n'+('gh'+'p_'+'A'*40).encode())
        with self.assertRaisesRegex(ValueError,'Private path/key/token'):self.collect()

    def test_linked_source_rejects(self):
        p=self.root/'README.md';original=self.temp/'owned-original.md';p.rename(original)
        try:p.symlink_to(original)
        except OSError:self.skipTest('Creating an owned local symlink is unavailable')
        with self.assertRaisesRegex(ValueError,'Linked'):self.collect()

    @unittest.skipUnless(os.name=='nt','Windows junction regression')
    def test_real_windows_junction_root_is_rejected(self):
        link=self.temp/'owned-junction'
        result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(self.root)],capture_output=True)
        if result.returncode:self.skipTest('Creating an owned local junction is unavailable')
        self.assertTrue(link.is_junction())
        with mock.patch.object(package,'ROOT',link):
            with self.assertRaisesRegex(ValueError,'Linked root'):self.collect()
        self.assertEqual((self.root/'README.md').read_bytes(),(SOURCE/'README.md').read_bytes())

    def test_exact_zip_roundtrip_and_no_overwrite(self):
        files,selected=self.collect();result=package.manifest(files,selected)
        target=self.temp/'own.zip';package.archive(target,files,result)
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(len(archive.namelist()),22)
            for name,raw in files.items():self.assertEqual(archive.read('leviath-refinements/'+name),raw)
        with self.assertRaisesRegex(ValueError,'Existing archive'):package.archive(target,files,result)

    def test_explicit_unit_input_and_local_only_build_route(self):
        for names in ((),('crown','crown'),('unknown',)):
            with self.assertRaises(ValueError):self.collect(names)
        self.rewrite('crown-0.1.1/SOURCE_BINDING.json',lambda d:d.update(sourceBuild='PUBLIC_REBUILD_PASS'))
        with self.assertRaisesRegex(ValueError,'Public rebuild claim'):self.collect()

if __name__=='__main__':unittest.main(verbosity=2)
