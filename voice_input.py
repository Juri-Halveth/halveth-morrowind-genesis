"""Opt-in, local German speech recognition for the current game session.

Constructing this object does not inspect or open an audio device. A recognizer
process is started only by a current-session in-game consent event. We store
recognized text after consent, never raw audio, and have no network path here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'scripts' / 'speech_recognizer.ps1'


class VoiceInput:
    def __init__(self, state_dir, on_text=None, on_state=None, runner=None):
        self.state_dir = Path(state_dir)
        self.on_text = on_text or (lambda session, text, confidence: None)
        self.on_state = on_state or (lambda session, state: None)
        self.runner = runner or subprocess.Popen
        self.lock = threading.RLock()
        self.process = None
        self.session = None
        self.thread = None
        self.transcript_path = None

    def start(self, session):
        """Open the device only after a valid, current-session Yes event."""
        if not isinstance(session, str) or not 0 < len(session) <= 160:
            return False
        with self.lock:
            if self.process and self.session == session and self.process.poll() is None:
                return True
            self.stop()
            executable = shutil.which('powershell.exe') if os.name == 'nt' else None
            if not executable or not SCRIPT.is_file():
                self.on_state(session, 'unavailable')
                return False
            directory = self.state_dir / 'microphone'
            directory.mkdir(parents=True, exist_ok=True)
            # Random-looking session IDs are never inserted in a file path.
            digest = hashlib.sha256(session.encode('utf-8')).hexdigest()[:20]
            self.transcript_path = directory / f'transcript-{digest}.jsonl'
            command = [executable, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                       '-File', str(SCRIPT)]
            try:
                self.process = self.runner(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except OSError:
                self.process = None
                self.on_state(session, 'unavailable')
                return False
            self.session = session
            process = self.process
            self.on_state(session, 'starting')
            self.thread = threading.Thread(target=self._read, args=(session, process), daemon=True)
            self.thread.start()
            return True

    def stop(self):
        with self.lock:
            process, session = self.process, self.session
            self.process = None
            self.session = None
            self.transcript_path = None
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            if process.stdout:
                process.stdout.close()
        if session:
            self.on_state(session, 'disabled')

    def _read(self, session, process):
        if process.stdout is None:
            return
        try:
            for raw in process.stdout:
                if len(raw) > 8192:
                    continue
                try:
                    record = json.loads(raw.decode('utf-8-sig'))
                except (UnicodeError, ValueError):
                    continue
                recognized = None
                with self.lock:
                    if self.process is not process or self.session != session:
                        break
                    if record.get('status') == 'ready':
                        self.on_state(session, 'listening')
                        continue
                    if record.get('status') == 'unavailable':
                        self.on_state(session, 'unavailable')
                        continue
                    if record.get('type') != 'recognized':
                        continue
                    text = record.get('text')
                    confidence = record.get('confidence')
                    if not isinstance(text, str) or not 0 < len(text) <= 1000 \
                            or not isinstance(confidence, (float, int)) or isinstance(confidence, bool) \
                            or not 0.60 <= confidence <= 1.0:
                        continue
                    text = text.strip()
                    if not text:
                        continue
                    with self.transcript_path.open('a', encoding='utf-8') as output:
                        output.write(json.dumps({'recordedAt': time.time(), 'text': text,
                                                 'confidence': round(confidence, 3)},
                                                ensure_ascii=False) + '\n')
                    recognized = (text, confidence)
                # Never call the companion while holding the process lock: a
                # simultaneous in-game opt-out must be able to stop the child.
                if recognized:
                    self.on_text(session, *recognized)
        except (OSError, ValueError):
            # Closing stdout while revoking consent can interrupt iteration.
            pass
        finally:
            with self.lock:
                if self.process is process and self.session == session:
                    self.process = None
                    self.session = None
                    self.transcript_path = None
                    self.on_state(session, 'unavailable')
