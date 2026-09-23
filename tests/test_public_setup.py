"""Public launcher preferences with temporary files; no installed game required."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import launcher


class PublicSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.root_patch=patch.object(launcher,'ROOT',self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.previous=launcher.LAUNCH_OPTIONS.copy()
        self.addCleanup(self.restore_options)

    def restore_options(self):
        launcher.LAUNCH_OPTIONS.clear()
        launcher.LAUNCH_OPTIONS.update(self.previous)

    def args(self,**values):
        data=dict(install_root=None,source_profile=None,model=None,copy_saves=False,save_config=False)
        data.update(values)
        return argparse.Namespace(**data)

    def test_first_run_does_not_copy_saves(self):
        result=launcher.configure(self.args())
        self.assertFalse(result['copy_saves'])
        self.assertFalse((self.root/'local-config.json').exists())

    def test_explicit_installation_roundtrips_but_copy_saves_does_not_persist(self):
        chosen=self.root/'owned-game'
        launcher.configure(self.args(install_root=chosen,source_profile='custom',model='local:model',copy_saves=True,save_config=True))
        result=launcher.configure(self.args())
        self.assertEqual(result['install_root'],str(chosen))
        self.assertEqual(result['source_profile'],'custom')
        self.assertEqual(result['model'],'local:model')
        self.assertFalse(result['copy_saves'])

    def test_unknown_configuration_is_not_silently_accepted(self):
        (self.root/'local-config.json').write_text(json.dumps({'secret':'not-a-preference'}),encoding='utf-8')
        with self.assertRaises(ValueError):
            launcher.configure(self.args())

    def test_profile_argument_cannot_be_a_path(self):
        with self.assertRaises(ValueError):
            launcher.configure(self.args(source_profile='../outside',save_config=True))
        self.assertFalse((self.root/'local-config.json').exists())

    def test_prepare_receives_selected_installation_and_opt_in(self):
        launcher.configure(self.args(install_root=self.root/'game',source_profile='own',copy_saves=True))
        with patch('scripts.prepare_profile.prepare',return_value={}) as prepare:
            launcher.prepare('beauty')
        passed=prepare.call_args.args[0]
        self.assertEqual(passed.install_root,self.root/'game')
        self.assertEqual(passed.source_profile,'own')
        self.assertTrue(passed.copy_saves)


if __name__=='__main__':
    unittest.main()
