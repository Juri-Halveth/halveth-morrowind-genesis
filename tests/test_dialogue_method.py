import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dialogue_method import dialogue_method, METHOD_ID, METHOD_VERSION
from server import Companion


class DialogueMethodTests(unittest.TestCase):
    def test_greetings_and_ordinary_conversation_keep_their_format(self):
        for message in ('Hallo Arrille!', 'Was verkaufst du?', 'Erzähl mir eine Geschichte.'):
            guidance, context = dialogue_method(message, npc=True)
            self.assertFalse(context['active'])
            self.assertEqual(context['presentation'], 'NPC_IN_CHARACTER')
            self.assertNotIn('Minimum-Evidenz', guidance)
            self.assertIn('ohne Hypothesenformular', guidance)
            self.assertIn('belegten Wissensrahmen', guidance)

    def test_inquiry_selects_a_bounded_method_without_action_authority(self):
        for message in ('Warum leuchtet dieser Stein?', 'Prüfe meine Hypothese.',
                        'Was wäre, wenn wir die Pflanze morgen besuchen?'):
            guidance, context = dialogue_method(message)
            self.assertTrue(context['active'])
            self.assertEqual((context['id'], context['version']), (METHOD_ID, METHOD_VERSION))
            self.assertEqual(context['authorityEffect'], 'NONE')
            for text in ('Gegenmodell', 'Minimum-Evidenz', 'Einschätzung ändern',
                         'offenen Rest', 'keine erfundene Messung', 'keine Aktion'):
                self.assertIn(text, guidance)

    def test_real_companion_prompt_wires_method_for_jarvis_and_npc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Companion(root, inbox=root / 'inbox.json')
            npc = {'id': 'actor', 'recordId': 'merchant', 'name': 'A', 'kind': 'npc'}
            app.event({'type': 'context', 'sessionId': 'world', 'context': {'npc': npc}})
            requests = []

            def model(path, payload=None, timeout=4):
                requests.append(payload)
                return {'message': {'content': 'Das müssten wir am Ort prüfen.'}}

            with patch.object(app, 'models', return_value={'available': True}), \
                    patch('server.model_request', side_effect=model):
                app.chat('Warum leuchtet die Pflanze?')
                app.chat('Hallo!', app.ensure_npc(npc))
            inquiry, greeting = [entry['messages'][0]['content'] for entry in requests]
            a, b = [json.loads(text[text.index('{'):]) for text in (inquiry, greeting)]
            self.assertTrue(a['gespraechsmethode']['active'])
            self.assertFalse(b['gespraechsmethode']['active'])
            self.assertEqual(b['gespraechsmethode']['presentation'], 'NPC_IN_CHARACTER')
            for text in (inquiry, greeting):
                self.assertIn('vergangene Ereignisse', text)
                self.assertIn('aktuelle beobachtete', text)
                self.assertIn('zukünftige Vorhersagen', text)
                self.assertIn('Nur ein bestätigtes Spiel-Receipt zählt.', text)
                self.assertIn('kein ausführbarer Code', text)
            with app.store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM actions').fetchone()[0], 0)

    def test_game_mailbox_preserves_actual_backend_result_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Companion(root, inbox=root / 'inbox.json')
            app.event({'type': 'context', 'sessionId': 'world', 'context': {}})
            request = {'sessionId': 'world', 'requestId': 'chat-1', 'text': 'Hallo'}
            for mode in ('MODEL_LIVE', 'OFFLINE', 'MODEL_UNAVAILABLE'):
                with patch.object(app, 'chat', return_value={'reply': 'Text', 'mode': mode}):
                    app.game_chat(request)
                reply = app.reply_queue.pop()
                self.assertEqual(reply['responseMode'], mode)
                self.assertEqual(reply['requestId'], request['requestId'])
            with patch.object(app, 'chat', side_effect=ValueError('fixture')):
                app.game_chat(request)
            self.assertEqual(app.reply_queue.pop()['responseMode'], 'ERROR')
            with patch.object(app, 'chat', return_value={'reply': 'Text', 'mode': 'MODEL_LIVE'}):
                app.game_chat({**request, 'sessionId': 'previous-world'})
            self.assertEqual(len(app.reply_queue), 0)


if __name__ == '__main__':
    unittest.main()
