import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from character_profile import profile
from server import Companion


class CharacterProfileTests(unittest.TestCase):
    def test_style_stays_stable_while_observed_state_changes(self):
        npc={'id':'actor-1','recordId':'merchant','worldId':'world-1','name':'A','kind':'npc',
             'disposition':20,'services':['Barter'],'health':{'current':20,'max':100}}
        a=profile(npc)
        b=profile({**npc,'disposition':80,'health':{'current':100,'max':100}})
        self.assertEqual(a['roleplayDirection']['voice'],b['roleplayDirection']['voice'])
        self.assertNotEqual(a['roleplayDirection']['attitudeFromDisposition'],b['roleplayDirection']['attitudeFromDisposition'])
        self.assertNotEqual(a['roleplayDirection']['currentConcern'],b['roleplayDirection']['currentConcern'])
        self.assertEqual(a['services'],['Handel'])
        self.assertEqual(npc['disposition'],20)

    def test_creature_does_not_inherit_human_biography(self):
        result=profile({'kind':'creature','recordId':'rat'},[{'role':'user','content':'Hi'},{'role':'assistant','content':'...'}])
        self.assertIn('beobachtbares Verhalten',result['roleplayDirection']['perspective'])
        self.assertEqual(result['conversationContinuity'],1)
        self.assertNotIn('health',result['runtimeFacts'])

    def test_npc_prompt_uses_exact_record_source_and_current_observations(self):
        with tempfile.TemporaryDirectory() as d:
            app=Companion(Path(d),inbox=Path(d)/'inbox.json')
            npc={'id':'a','worldId':'w','recordId':'merchant','name':'A','className':'Trader','disposition':75,'kind':'npc'}
            app.event({'type':'context','sessionId':'s','context':{'npc':npc}})
            with app.store.connect() as db:
                db.execute('INSERT INTO lore VALUES(?,?,?,?)',('actor:merchant','A','Exact actor record','fixture.esm'))
            requests=[]
            def model(path,payload=None,timeout=4):
                requests.append(payload)
                return {'message':{'content':'Was suchst du?'}}
            with patch.object(app,'models',return_value={'available':True}),patch('server.model_request',side_effect=model):
                result=app.chat('Hallo',app.ensure_npc(npc))
            self.assertEqual(result['mode'],'MODEL_LIVE')
            system=requests[0]['messages'][0]['content']
            data=json.loads(system[system.index('{'):])
            self.assertEqual(data['quellen'][0]['id'],'actor:merchant')
            self.assertEqual(data['charakterProfil']['runtimeFacts']['disposition'],75)
            self.assertIn('nicht als JARVIS',system)


if __name__=='__main__': unittest.main()
