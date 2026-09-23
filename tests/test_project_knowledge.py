import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_knowledge import ProjectKnowledge, MAX_CONTEXT_CHARS
from server import Companion, Handler, ThreadingHTTPServer


class ProjectKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = Companion(self.root, inbox=self.root / 'inbox.json')
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def model_transport(self, path, payload=None, timeout=4):
        self.calls.append((path, payload))
        if path == '/api/tags':
            return {'models': [{'name': self.app.model}]}
        if path == '/api/chat':
            return {'message': {'content': 'Als neue Spielidee könnte LOVE Blüten erzeugen.'}}
        self.fail('Unerwarteter Modellpfad: ' + path)

    def prompt_context(self):
        payload = next(data for path, data in self.calls if path == '/api/chat')
        system = payload['messages'][0]['content']
        return system, json.loads(system.split('\n', 1)[1])

    def test_eight_cards_have_commit_bound_design_provenance(self):
        cards = self.app.project_knowledge.all()
        self.assertEqual(len(cards), 8)
        for card in cards:
            self.assertEqual(card['type'], 'DESIGN_REFERENCE')
            self.assertIn(card['provenance']['commitSha'], card['url'])
            self.assertEqual(len(card['provenance']['gitBlobSha']), 40)
        cards[0]['summary'] = 'Changed caller copy'
        self.assertNotEqual(self.app.project_knowledge.all()[0]['summary'], 'Changed caller copy')

    def test_selection_is_relevant_bounded_and_deterministic(self):
        knowledge = self.app.project_knowledge
        love = knowledge.chat_references('LOVE mit Blumen und Herzen')
        self.assertEqual(love[0]['id'], 'scarlet-love-20260923')
        self.assertNotIn('all-scales-world-design-20260923', {card['id'] for card in love})
        self.assertEqual(knowledge.chat_references('Wo steht der Händler in Vivec?'), [])
        query = 'LOVE ASTER Gedächtnis Portal Persönlichkeit Ziel Lernstudio Pflanzen'
        selected = knowledge.chat_references(query)
        self.assertLessEqual(len(selected), 3)
        self.assertEqual(selected, knowledge.chat_references(query))
        self.assertLessEqual(len(json.dumps(selected, ensure_ascii=False)), MAX_CONTEXT_CHARS)

    def test_greeting_or_companion_name_does_not_select_design_cards(self):
        knowledge = self.app.project_knowledge
        for phrase in ('JARVIS', 'Hallo', 'Hallo JARVIS', 'JARVIS, wo steht der Händler in Vivec?'):
            self.assertEqual(knowledge.chat_references(phrase), [], phrase)
        self.assertEqual(knowledge.chat_references('Hallo JARVIS, LOVE'),
                         knowledge.chat_references('LOVE'))

    def test_matching_cards_reach_local_model_and_response_separately(self):
        with self.app.store.connect() as db:
            db.execute('INSERT INTO lore VALUES(?,?,?,?)',
                       ('love-local', 'Blumen', 'Eine vorhandene Lore-Notiz zu Blumen.', 'Lokale Test-Lore'))
        self.app.store.remember('other-persona', 'user', 'Andere private Begegnung')
        with patch('server.model_request', side_effect=self.model_transport):
            reply = self.app.chat('LOVE mit Blumen und Herzen')
        system, context = self.prompt_context()
        project = context['projektDesignReferenzen']
        self.assertEqual(reply['mode'], 'MODEL_LIVE')
        self.assertEqual(reply['projectSources'], project)
        self.assertIn('scarlet-love-20260923', {card['id'] for card in project})
        self.assertGreater(len(context['quellen']), 0)
        self.assertEqual(reply['sources'][0]['id'], 'love-local')
        self.assertIn('keine Morrowind-Lore', system)
        self.assertIn('DESIGN_REFERENCE', system)
        self.assertIn('Ideen, keine implementierten Spielfähigkeiten', system)
        self.assertIn('ausdrücklich als Vorschlag oder Entwurf', system)
        self.assertIn('OpenMW-Lua-Oberfläche mit F8', system)
        self.assertIn('kein uneingeschränkter Konsoleninterpreter', system)
        self.assertLessEqual(len(project), 3)
        self.assertNotIn('Andere private Begegnung', json.dumps(self.calls))
        self.assertEqual(self.app.store.counts()['lore'], 1)
        self.assertEqual(self.app.store.history('other-persona')[0]['content'], 'Andere private Begegnung')
        self.assertEqual([path for path, _ in self.calls], ['/api/tags', '/api/chat'])

    def test_unrelated_question_does_not_feed_entire_project_catalog(self):
        with patch('server.model_request', side_effect=self.model_transport):
            reply = self.app.chat('Wo steht der Händler in Vivec?')
        _, context = self.prompt_context()
        self.assertEqual(context['projektDesignReferenzen'], [])
        self.assertEqual(reply['projectSources'], [])
        self.assertNotIn('scarlet-love-20260923', json.dumps(self.calls))

    def test_offline_answer_does_not_claim_model_used_references(self):
        with patch('server.model_request', return_value={'models': []}) as transport:
            reply = self.app.chat('LOVE und Blumen')
        self.assertEqual(reply['mode'], 'OFFLINE')
        self.assertEqual(reply['projectSources'], [])
        transport.assert_called_once_with('/api/tags')

    def test_status_exposes_count_without_adding_lore_rows(self):
        with patch('server.model_request', return_value={'models': []}):
            status = self.app.status()
        self.assertEqual(status['projectKnowledgeCount'], 8)
        self.assertEqual(status['counts']['lore'], 0)

    def test_invalid_type_and_unbound_source_are_rejected(self):
        cards = self.app.project_knowledge.all()
        fixture = self.root / 'bad-knowledge.json'
        cards[0]['type'] = 'MORROWIND_FACT'
        fixture.write_text(json.dumps(cards), encoding='utf-8')
        with self.assertRaises(ValueError):
            ProjectKnowledge(fixture)
        cards[0]['type'] = 'DESIGN_REFERENCE'
        cards[0]['url'] = 'https://github.com/Juri-Halveth/halveth-scarlet/blob/main/README.md'
        fixture.write_text(json.dumps(cards), encoding='utf-8')
        with self.assertRaises(ValueError):
            ProjectKnowledge(fixture)

    def test_api_lists_or_searches_local_cards_without_model_transport(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        httpd.app = self.app
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{httpd.server_port}'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with patch('server.model_request', side_effect=AssertionError('No model needed')):
                with opener.open(origin + '/api/project-knowledge', timeout=3) as response:
                    self.assertEqual(len(json.load(response)), 8)
                with opener.open(origin + '/api/project-knowledge?q=LOVE', timeout=3) as response:
                    rows = json.load(response)
                    self.assertEqual([card['id'] for card in rows], ['scarlet-love-20260923'])
                with opener.open(origin + '/api/project-knowledge?q=Vivec', timeout=3) as response:
                    self.assertEqual(json.load(response), [])
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    opener.open(origin + '/api/project-knowledge?q=' + 'a' * 4001, timeout=3)
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)

    def test_provider_catalog_and_single_banner_route(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        httpd.app = self.app
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{httpd.server_port}'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with patch('server.ROOT', self.root):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    opener.open(origin + '/api/generation-providers', timeout=3)
                self.assertEqual(caught.exception.code, 503)
                self.assertIn('error', json.load(caught.exception))
                caught.exception.close()
                (self.root / 'data').mkdir()
                catalog = {'providers': [{'id': 'local-fixture', 'status': 'REFERENCE_ONLY'}]}
                (self.root / 'data' / 'generation-providers.json').write_text(json.dumps(catalog), encoding='utf-8')
                with opener.open(origin + '/api/generation-providers', timeout=3) as response:
                    self.assertEqual(json.load(response), catalog)
                banner = self.root / 'mod' / 'Textures' / 'halveth' / 'scarlet-love-banner.png'
                banner.parent.mkdir(parents=True)
                fixture = b'\x89PNG\r\n\x1a\nroute-fixture'
                banner.write_bytes(fixture)
                with opener.open(origin + '/assets/scarlet-love-banner.png', timeout=3) as response:
                    self.assertEqual(response.headers['Content-Type'], 'image/png')
                    self.assertEqual(response.read(), fixture)
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    opener.open(origin + '/assets/other.png', timeout=3)
                self.assertEqual(caught.exception.code, 404)
                caught.exception.close()
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
