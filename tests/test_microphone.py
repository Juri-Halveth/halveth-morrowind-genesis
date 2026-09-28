"""Consent and session boundaries without ever opening a test microphone."""
from pathlib import Path
import json
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Companion
from voice_input import VoiceInput


class FakeInput:
    def __init__(self):
        self.starts = []
        self.stops = 0

    def start(self, session):
        self.starts.append(session)
        return True

    def stop(self):
        self.stops += 1


class MicrophoneTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.app = Companion(root, inbox=root / 'inbox.json')
        self.mic = FakeInput()
        self.app.microphone = self.mic

    def tearDown(self):
        self.app.stopping.set()
        if self.app.thread:
            self.app.thread.join(timeout=2)
        self.directory.cleanup()

    def context(self, session='game-A'):
        self.app.event({'type': 'context', 'sessionId': session,
                        'context': {'player': {'name': 'Test', 'cell': 'Balmora'}}})

    def test_no_device_opened_by_constructor_or_context(self):
        with tempfile.TemporaryDirectory() as directory:
            input_device = VoiceInput(directory, runner=lambda *a, **k: self.fail('spawned'))
            self.assertIsNone(input_device.process)
            self.assertFalse((Path(directory) / 'microphone').exists())
        self.context()
        self.assertEqual(self.mic.starts, [])
        status = json.loads(self.app.microphone_status.read_text(encoding='utf-8'))
        self.assertEqual(status['state'], 'disabled')

    def test_only_current_session_yes_starts_and_no_stops(self):
        self.app.event({'type': 'microphone', 'sessionId': 'game-A', 'enabled': True})
        self.context()
        self.app.event({'type': 'microphone', 'sessionId': 'foreign', 'enabled': True})
        self.app.event({'type': 'microphone', 'sessionId': 'game-A', 'enabled': 'true'})
        self.assertEqual(self.mic.starts, [])
        self.app.event({'type': 'microphone', 'sessionId': 'game-A', 'enabled': True})
        self.assertEqual(self.mic.starts, ['game-A'])
        self.app.event({'type': 'microphone', 'sessionId': 'game-A', 'enabled': False})
        self.assertIsNone(self.app.microphone_session)
        self.assertEqual(self.mic.stops, 1)

    def test_new_game_and_lost_heartbeat_revoke_consent(self):
        self.context()
        self.app.event({'type': 'microphone', 'sessionId': 'game-A', 'enabled': True})
        self.context('game-B')
        self.assertEqual(self.mic.stops, 1)
        self.assertIsNone(self.app.microphone_session)
        self.app.event({'type': 'microphone', 'sessionId': 'game-B', 'enabled': True})
        self.app.last_microphone_heartbeat = time.monotonic() - 10
        self.app.start()
        for _ in range(20):
            if self.mic.stops >= 2:
                break
            time.sleep(.05)
        self.assertEqual(self.mic.stops, 2)
        self.assertIsNone(self.app.microphone_session)

    def test_heard_text_stays_in_game_and_requires_wake_word_for_model(self):
        self.context()
        self.app.on_heard('game-A', 'Nicht freigegeben', .9)
        self.assertEqual(len(self.app.reply_queue), 0)
        self.app.event({'type': 'microphone', 'sessionId': 'game-A', 'enabled': True})
        calls = []
        answered = threading.Event()

        def answer(question, *_args):
            calls.append(question)
            answered.set()
            return {'reply': 'Schriftliche Antwort'}

        self.app.chat = answer
        self.app.on_heard('game-A', 'Der Himmel ist rot', .8)
        self.assertEqual(calls, [])
        self.app.on_heard('game-A', 'Jarvis, warum ist der Himmel rot?', .8)
        self.assertTrue(answered.wait(2))
        self.assertEqual(calls, ['warum ist der Himmel rot?'])
        self.assertTrue(any(item['reply'] == 'Schriftliche Antwort' for item in self.app.reply_queue))


if __name__ == '__main__':
    unittest.main()
