"""Exercise own generated-world dependency installation without starting a game."""
from pathlib import Path
import importlib.util,json,os,tempfile,unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('world_provision_tests',ROOT/'scripts/provision-world.py')
world=importlib.util.module_from_spec(spec);spec.loader.exec_module(world)


class WorldProvisionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='own-world-provision-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.base=self.root/'base profile';self.base.mkdir()
        self.runtime=self.root/'external runtime';self.runtime.mkdir()
        resources=self.runtime/'resources';resources.mkdir();(resources/'vfs-mw').mkdir()
        api_fixture=self.root/'own-api-contract.json'
        api_fixture.write_text(json.dumps({'schema':'veyra.workshop.engine-api-inputs.v1','resourcesFiles':{
            'lua_api/own_fixture.lua':world.digest(b'OWN_API_STRUCTURE_FIXTURE')}}),encoding='utf8')
        api_input=resources/'lua_api/own_fixture.lua';api_input.parent.mkdir();api_input.write_bytes(b'OWN_API_STRUCTURE_FIXTURE')
        api_mock=mock.patch.object(world,'ENGINE_API_BINDINGS',str(api_fixture));api_mock.start();self.addCleanup(api_mock.stop)
        self.engine=self.runtime/'openmw.exe';self.engine.write_bytes(b'OWN_NON_EXECUTABLE_ENGINE_FIXTURE')
        (self.runtime/'openmw.cfg').write_text('resources=./resources\ndata=./resources/vfs-mw\nfallback=Own_Default,1\nfallback=Own_Default2,2\n',encoding='utf8')
        data=self.root/'game refs';data.mkdir()
        for n in ('Morrowind.esm','OwnExtra.esp'):(data/n).write_bytes(b'OWN_READONLY_CONTENT_FIXTURE')
        (self.base/'openmw.cfg').write_text('data="../game refs"\ncontent=Morrowind.esm\ncontent=OwnExtra.esp\nfallback=Own_Base,3\n',encoding='utf8')
        (self.base/'settings.cfg').write_text('[Video]\nresolution x = 1920\n',encoding='utf8')
        self.link=self.root/'hardlinked.cfg';os.link(self.base/'openmw.cfg',self.link)
        self.before={p:p.read_bytes() for p in (self.base/'openmw.cfg',self.base/'settings.cfg',self.runtime/'openmw.cfg',self.engine,self.link)}
        self.destination=self.root/'new own world'

    def plan(self,names=('portal','construction')):
        return world.make_plan(self.base,self.engine,self.destination,names)

    def assert_originals(self):
        for p,raw in self.before.items():self.assertEqual(p.read_bytes(),raw)
        self.assertTrue(os.path.samefile(self.link,self.base/'openmw.cfg'))

    def test_real_own_plugin_and_geometry_dependency_copies_preserve_sources(self):
        plan=self.plan();self.assertEqual(plan['requestedModules'],['portal','construction'])
        self.assertEqual(plan['modules'],['frontier','portal','construction','panels'])
        self.assertFalse(self.destination.exists());self.assert_originals()
        receipt=world.apply_plan(plan);self.assertEqual(receipt['nativeAcceptance'],'NOT_RUN')
        cfg=(self.destination/'profile/openmw.cfg').read_text()
        self.assertLess(cfg.index('content=Morrowind.esm'),cfg.index('content=LEVIATH-Frontier.esp'))
        self.assertLess(cfg.index('content=LEVIATH-Frontier.esp'),cfg.index('content=veyra-portal.omwscripts'))
        self.assertEqual(cfg.count('content=veyra-panel-coordinator.omwscripts'),1)
        self.assertLess(cfg.index('/modules/construction/mod'),cfg.index('/modules/panels/mod'))
        self.assertNotIn('probe',cfg.lower());self.assertIn('replace=config',cfg)
        for row in plan['payload']:
            copy=self.destination/row['destination'];self.assertEqual(world.digest(copy.read_bytes()),row['sha256'])
            self.assertFalse(os.path.samefile(copy,row['path']))
        self.assert_originals()

    def test_plaza_closure_retains_ordered_own_texture_override_without_fake_content(self):
        plan=self.plan(('plaza',));self.assertEqual(plan['modules'],['frontier','frontier-textures','plaza'])
        world.apply_plan(plan);cfg=(self.destination/'profile/openmw.cfg').read_text()
        self.assertEqual(cfg.count('content=LEVIATH-Frontier.esp'),1)
        self.assertEqual(cfg.count('content=LEVIATH-Plaza.esp'),1)
        self.assertNotIn('content=None',cfg)
        self.assertLess(cfg.index('/modules/frontier/mod'),cfg.index('/modules/frontier-textures/mod'))
        self.assertLess(cfg.index('/modules/frontier-textures/mod'),cfg.index('/modules/plaza/mod'))
        self.assert_originals()

    def test_changed_manifest_or_asset_is_rejected_before_owned_destination(self):
        plan=self.plan(('frontier',))
        bindings=world.ROOT/world.OWN_ASSETS
        original=bindings.read_bytes()
        # Mutate an owned disposable manifest copy rather than accepted sources.
        copied=self.root/'owned fixture package';copied.mkdir()
        fixture=copied/world.OWN_ASSETS;fixture.parent.mkdir(parents=True);fixture.write_bytes(original)
        with mock.patch.object(world,'ROOT',copied):
            plan['inputs']=[{**r,'path':str(fixture)} if r['path']==str(bindings) else r for r in plan['inputs']]
            fixture.write_bytes(original+b'\n')
            with self.assertRaisesRegex(ValueError,'bound input changed'):world.apply_plan(plan)
        self.assertFalse(self.destination.exists());self.assertEqual(list(self.root.glob('*.stage-*')),[])
        self.assert_originals()

    def test_wrong_existing_vfs_module_is_rejected_without_silent_override(self):
        conflicting=self.root/'game refs/scripts/veyra_portal/global.lua'
        conflicting.parent.mkdir(parents=True);conflicting.write_text('OWN_INCOMPATIBLE_FIXTURE',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Existing VFS source differs'):self.plan(('portal',))
        self.assertFalse(self.destination.exists());self.assert_originals()

    def test_data_only_module_requires_a_bound_frontier_and_no_extra_binary_is_copied(self):
        self.assertEqual(world.resolve_modules(('frontier-textures',)),('frontier','frontier-textures'))
        with self.assertRaises(ValueError):world.resolve_modules(('frontier','frontier'))
        with self.assertRaises(ValueError):world.resolve_modules(('unknown',))
        self.assertTrue(all('Morrowind.esm' not in r['path'] for r in self.plan()['payload']))
        self.assert_originals()

    def test_missing_own_asset_binding_and_changed_generator_reject(self):
        package=world.ROOT/'presentation/frontier-candidate'
        with self.assertRaisesRegex(ValueError,'explicit source/license binding'):
            world.owned_asset_binding(package,'LEVIATH-Frontier.esp',{'assets':{}})
        bindings=json.loads((world.ROOT/world.OWN_ASSETS).read_bytes())
        row=bindings['assets']['presentation/frontier-candidate/mod/LEVIATH-Frontier.esp']
        row['sourceGeneratorSha256']='0'*64
        with self.assertRaisesRegex(ValueError,'generator changed'):
            world.owned_asset_binding(package,'LEVIATH-Frontier.esp',bindings)

    def test_allowed_old_hook_is_bound_and_changed_reference_rejected_at_apply(self):
        relative='scripts/veyra_portal/player.lua'
        p=self.root/'game refs'/relative;p.parent.mkdir(parents=True)
        source=world.ROOT/'gameplay/portal/mod'/relative;p.write_bytes(source.read_bytes())
        plan=self.plan(('portal',));self.assertIn(str(p),{r['path'] for r in plan['inputs']})
        p.write_bytes(b'OWN_CHANGED_EXISTING_SOURCE')
        with self.assertRaisesRegex(ValueError,'bound input changed'):world.apply_plan(plan)
        self.assertFalse(self.destination.exists());self.assert_originals()

    def test_base_content_changed_after_plan_is_bound_without_copy(self):
        plan=self.plan(('frontier',));p=self.root/'game refs/Morrowind.esm'
        self.assertIn(str(p),{r['path'] for r in plan['inputs']})
        self.assertNotIn(str(p),{r['path'] for r in plan['payload']})
        p.write_bytes(b'OWN_CHANGED_CONTENT_FIXTURE')
        with self.assertRaisesRegex(ValueError,'bound input changed'):world.apply_plan(plan)
        self.assertFalse(self.destination.exists());self.assert_originals()

    def test_current_hud_accepts_bound_old_base_and_footer_matches_courier_source(self):
        p=self.root/'game refs/scripts/veyra/hud.lua';p.parent.mkdir(parents=True)
        p.write_bytes((world.ROOT/'presentation/mod/scripts/veyra/hud.lua').read_bytes())
        plan=self.plan(('courier','hud'));self.assertEqual(plan['modules'],['courier','panels','hud'])
        world.apply_plan(plan)
        self.assertEqual((self.destination/'modules/hud/mod/Textures/veyra/white.png').read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
        self.assertEqual(p.read_bytes(),(world.ROOT/'presentation/mod/scripts/veyra/hud.lua').read_bytes())
        self.assert_originals()

    def test_changed_bound_engine_api_rejects_version_incompatibility(self):
        p=self.runtime/'resources/lua_api/own_fixture.lua';p.write_bytes(b'OWN_DIFFERENT_API_FIXTURE')
        with self.assertRaisesRegex(ValueError,'Engine API/interface bytes differ'):self.plan(('frontier',))
        self.assertFalse(self.destination.exists());self.assert_originals()

    def test_forest_closure_copies_separate_cc0_license_and_preserves_master_order(self):
        plan=self.plan(('scenery',))
        self.assertEqual(plan['modules'],['frontier','frontier-textures','bark','crown','scenery'])
        world.apply_plan(plan);cfg=(self.destination/'profile/openmw.cfg').read_text()
        self.assertLess(cfg.index('content=LEVIATH-Frontier.esp'),cfg.index('content=Veyra-Dense-Crown.esp'))
        self.assertLess(cfg.index('content=Veyra-Dense-Crown.esp'),cfg.index('content=LEVIATH-Frontier-Scenery.esp'))
        self.assertLess(cfg.index('/modules/bark/mod'),cfg.index('/modules/crown/mod'))
        self.assertEqual(cfg.count('content=LEVIATH-Frontier-Scenery.esp'),1)
        license=(self.destination/'modules/bark/CC0-1.0.txt').read_text()
        self.assertIn('CC0 1.0 Universal',license);self.assertIn('4. Limitations and Disclaimers.',license)
        self.assert_originals()

    def test_cc0_asset_cannot_silently_adopt_own_mit_license(self):
        bindings=json.loads((world.ROOT/world.OWN_ASSETS).read_bytes())
        relative='Textures/veyra/swamp_bark.dds'
        bindings['assets']['presentation/bark-materials/mod/'+relative]['license']='MIT'
        with self.assertRaisesRegex(ValueError,'explicit source/license binding'):
            world.owned_asset_binding(world.ROOT/'presentation/bark-materials',relative,bindings)

    def test_audio_selection_has_bound_cc0_derivative_and_license_without_download(self):
        plan=self.plan(('audio',));self.assertEqual(plan['modules'],['courier','panels','audio'])
        copied={r['destination']:r for r in plan['payload']}
        wav='modules/audio/mod/Sound/veyra/courier_bell_mono.wav'
        self.assertIn(wav,copied);self.assertEqual(copied[wav]['sha256'],'faa557bc6e4cd2c5c3c3b22ba8e78e9c7af35e7ab11e8cbaf5607f6ce177479c')
        world.apply_plan(plan)
        self.assertEqual(world.digest((self.destination/wav).read_bytes()),copied[wav]['sha256'])
        self.assertIn('Creative Commons Zero',(self.destination/'modules/audio/KENNEY-LICENSE.txt').read_text())
        self.assert_originals()


if __name__=='__main__':unittest.main(verbosity=2)
