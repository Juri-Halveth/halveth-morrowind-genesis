"""Optional, nonblocking German speech for in-game companion replies.

Only voices installed on the player's own Windows system are used. The game
continues if speech is unavailable, slow, or fails.
"""
from __future__ import annotations

import base64
import hashlib
import os
import queue
import subprocess
import threading


SPEAK_SCRIPT = r'''
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $german = @($speaker.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'de-DE' } | ForEach-Object { $_.VoiceInfo.Name } | Select-Object -Unique)
    if ($german.Count -eq 0) { exit 2 }
    $seed = [int]$env:HALVETH_VOICE_SEED
    $rate = [int]$env:HALVETH_VOICE_RATE
    try { $speaker.SelectVoice($german[$seed % $german.Count]) }
    catch { $speaker.SelectVoice($german[0]) }
    $speaker.Rate = $rate
    $text = [Console]::In.ReadToEnd()
    if ($text.Length -gt 0) { $speaker.Speak($text) }
} finally { $speaker.Dispose() }
'''


def character_voice(speaker: str) -> tuple[int, int]:
    """Stable voice index and slight pace variation; no identity inference."""
    digest = hashlib.sha256(speaker.encode('utf-8')).digest()
    return int.from_bytes(digest[:2], 'big'), (digest[2] % 3) - 1


class VoiceOutput:
    def __init__(self, runner=None, available=None):
        self._runner = runner or subprocess.run
        self._available = os.name == 'nt' if available is None else available
        self._pending = queue.Queue(maxsize=4)
        self._worker = threading.Thread(target=self._loop, name='halveth-voice', daemon=True)
        self._worker.start()

    def say(self, speaker: str, text: str) -> bool:
        if not self._available or not isinstance(text, str) or not text.strip():
            return False
        # Spoken text has no command interpolation; it is passed through stdin.
        item = (str(speaker)[:120], text.strip()[:1200])
        try:
            self._pending.put_nowait(item)
            return True
        except queue.Full:
            return False

    def _loop(self):
        while True:
            speaker, spoken = self._pending.get()
            seed, rate = character_voice(speaker)
            env = dict(os.environ, HALVETH_VOICE_SEED=str(seed), HALVETH_VOICE_RATE=str(rate))
            try:
                self._runner(
                    ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
                     base64.b64encode(SPEAK_SCRIPT.encode('utf-16le')).decode('ascii')],
                    input=spoken, text=True, encoding='utf-8', capture_output=True,
                    timeout=45, env=env,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except (OSError, subprocess.TimeoutExpired):
                pass
            finally:
                self._pending.task_done()
