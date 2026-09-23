import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Companion


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.app=Companion(root,inbox=root/'inbox.json')
        self.app.event({'type':'context','sessionId':'world-A','context':{'player':{'name':'Test','cell':'Vivec'}}})

    def tearDown(self):
        self.temp.cleanup()

    def test_memory_is_separate_and_persistent(self):
        self.app.store.remember('jarvis','user','Hallo')
        self.app.store.remember('other','user','Privates anderes Gespräch')
        second=Companion(Path(self.temp.name),inbox=Path(self.temp.name)/'inbox2.json')
        self.assertEqual([x['content'] for x in second.store.history('jarvis')],['Hallo'])

    def test_action_waits_for_game_receipt(self):
        action=self.app.offer('give_gold',{'amount':250},'250 Gold')
        result=self.app.dispatch(action['id'])
        self.assertEqual(result['status'],'queued')
        with self.app.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM actions WHERE id=?',(action['id'],)).fetchone()[0],'queued')
        self.app.event({'type':'result','sessionId':'world-A','actionId':action['id'],'success':True,'before':0,'after':250})
        self.assertEqual(self.app.receipts[-1]['status'],'executed')
        with self.assertRaises(ValueError):
            self.app.dispatch(action['id'])

    def test_old_world_action_does_not_replay(self):
        action=self.app.offer('give_gold',{'amount':250},'250 Gold')
        self.app.event({'type':'context','sessionId':'world-B','context':{}})
        with self.assertRaises(ValueError):
            self.app.dispatch(action['id'])

    def test_foreign_receipt_cannot_complete(self):
        action=self.app.offer('heal_player',{},'Heilen')
        self.app.dispatch(action['id'])
        self.app.event({'type':'result','sessionId':'foreign','actionId':action['id'],'success':True})
        self.assertEqual(len(self.app.receipts),0)
        self.assertIsNotNone(self.app.pending)

    def test_disconnected_world_does_not_mutate_mailbox(self):
        action=self.app.offer('heal_player',{},'Heilen')
        self.app.last_context=0
        with self.assertRaises(ValueError):
            self.app.dispatch(action['id'])
        self.assertFalse(self.app.inbox.exists())

    def test_amount_is_bounded_and_lore_search_is_data(self):
        action=self.app.suggestions('Gib mir 999999 Gold')[0]
        self.assertEqual(action['params']['amount'],100000)
        self.assertEqual(self.app.store.search('" OR * ; DELETE'),[])

    def test_unknown_action_rejected(self):
        action=self.app.offer('console',{'command':'anything'},'Nicht erlaubt')
        with self.assertRaises(ValueError):
            self.app.dispatch(action['id'])

    def test_mailbox_sequence_is_int32_and_survives_restart(self):
        action=self.app.offer('heal_player',{},'Heilen')
        self.app.dispatch(action['id'])
        message=json.loads(self.app.inbox.read_text(encoding='utf-8'))
        self.assertTrue(0<message['sequence']<=2147483647)
        restarted=Companion(Path(self.temp.name),inbox=self.app.inbox)
        self.assertGreater(restarted.next_sequence(),message['sequence'])

    def test_generic_actor_instances_keep_separate_memory(self):
        first=self.app.ensure_npc({'id':'actor-1','recordId':'rat','worldId':'campaign-1'})
        second=self.app.ensure_npc({'id':'actor-2','recordId':'rat','worldId':'campaign-1'})
        third=self.app.ensure_npc({'id':'actor-1','recordId':'rat','worldId':'campaign-2'})
        self.assertEqual(len({first,second,third}),3)

    def test_log_frames_preserve_large_multilingual_context(self):
        expected={'type':'context','sessionId':'new-session','context':{'book':'ÄÖß — 星 🌌 '*900}}
        raw=json.dumps(expected,ensure_ascii=False).encode('utf-8')
        chunks=[raw[i:i+384] for i in range(0,len(raw),384)]
        for i,chunk in reversed(list(enumerate(chunks,1))):
            line=f'[00:31:19.498 *] HALVETH_FRAME:frame1:{i}:{len(chunks)}:{chunk.hex()}\r'.encode('ascii')
            self.app.ingest_line(line)
        self.assertEqual(self.app.context,expected['context'])

    def test_incomplete_frame_never_becomes_context(self):
        before=self.app.context.copy()
        self.app.ingest_line(b'HALVETH_FRAME:partial:1:2:7b')
        self.assertEqual(self.app.context,before)


if __name__=='__main__':
    unittest.main()
