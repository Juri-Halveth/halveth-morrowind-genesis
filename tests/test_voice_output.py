import time
import unittest

from voice_output import VoiceOutput, character_voice


class VoiceOutputTests(unittest.TestCase):
    def test_german_speech_worker_does_not_hold_game_reply(self):
        calls = []

        def slow_speech(*args, **kwargs):
            calls.append((args, kwargs))
            time.sleep(0.2)

        voice = VoiceOutput(runner=slow_speech, available=True)
        start = time.monotonic()
        self.assertTrue(voice.say('Sera', 'Guten Abend.'))
        self.assertLess(time.monotonic() - start, 0.05)
        voice._pending.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]['input'], 'Guten Abend.')
        self.assertEqual(character_voice('Sera'), character_voice('Sera'))
        self.assertIn(calls[0][1]['env']['HALVETH_VOICE_RATE'], {'-1', '0', '1'})


if __name__ == '__main__':
    unittest.main()
