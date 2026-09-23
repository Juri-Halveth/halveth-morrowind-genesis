#!/usr/bin/env python3
"""Optional live OpenMW -> local LLM -> VFS -> native dialog receipt check.

Starts a disposable character with separate state. Does not read or write main
saves and does not invoke world-changing tools. Run manually, outside unit tests.
"""
from __future__ import annotations

import argparse
import configparser
from datetime import datetime, timezone
import json
import io
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import Companion, Handler, ThreadingHTTPServer, MODEL
from scripts.prepare_profile import atomic_text, default_install, prepare

REQUEST_TEXT='JARVIS, begrüße mich in einem kurzen deutschen Satz. Wir testen gerade unser freies Gespräch in Morrowind. Führe keine Spielaktion aus.'
NPC_REQUEST='Hallo Arrille. Was kannst du mir als Haendler hier anbieten? Antworte als du selbst in zwei kurzen deutschen Saetzen mit einer passenden Rueckfrage.'

NATIVE_CHAT = r'''local core=require('openmw.core')
local self=require('openmw.self')
local C=require('scripts.halveth.common')
local started,sent,finished=nil,false,false
return {
    engineHandlers={onFrame=function()
        if not self.cell or finished then return end
        if not started then started=core.getRealTime() end
        local elapsed=core.getRealTime()-started
        if elapsed>=4 and not sent then
            sent=true
            self:sendEvent('HALVETH_TestChat',{
                entityMode='jarvis',
                text='JARVIS, begrüße mich in einem kurzen deutschen Satz. Wir testen gerade unser freies Gespräch in Morrowind. Führe keine Spielaktion aus.'})
        end
        if elapsed>=170 then
            finished=true
            print('HALVETH_CHAT_FAIL no native reply receipt within 170 seconds')
            core.quit()
        end
    end},
    eventHandlers={HALVETH_ChatSubmitted=function(data)
        C.emit({type='chat_source',sessionId=data.sessionId,requestId=data.requestId,text=data.text,contextJson=data.contextJson})
    end,
    HALVETH_ReplyReceived=function(data)
        if finished then return end
        finished=true
        local ok=data.speaker=='JARVIS' and type(data.requestId)=='string' and #data.reply>0 and data.uiOpen==true
        print('HALVETH_CHAT_'..(ok and 'PASS' or 'FAIL')..' requestId='..tostring(data.requestId)..' speaker='..tostring(data.speaker)..' replyBytes='..#data.reply..' uiOpen='..tostring(data.uiOpen))
        core.quit()
    end}
}
'''


class WitnessCompanion(Companion):
    """Observe actual results without substituting the production chat path."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_witnesses = []
        self.observed_events = []

    def event(self, data):
        self.observed_events.append(data)
        return super().event(data)

    def chat(self, *args, **kwargs):
        started = time.monotonic()
        result = super().chat(*args, **kwargs)
        self.chat_witnesses.append({
            'mode': result['mode'], 'reply': result['reply'],
            'entityId': result['entityId'], 'actions': result['actions'],
            'elapsed_seconds': round(time.monotonic() - started, 3),
        })
        return result


def run(install_root: Path, state_dir: Path, port: int, model: str, npc_mode=False) -> dict:
    args = argparse.Namespace(install_root=install_root, state_dir=state_dir,
                              source_profile='max', profile='beauty', smoke=True,
                              copy_saves=False, reset_settings=True)
    prepared = prepare(args)
    native_chat=NATIVE_CHAT
    request_text=REQUEST_TEXT
    expected_speaker='JARVIS'
    if npc_mode:
        prepared['command'][-1]="Seyda Neen, Arrille's Tradehouse"
        request_text=NPC_REQUEST
        expected_speaker='Arrille'
        native_chat=native_chat.replace("local C=require('scripts.halveth.common')", "local C=require('scripts.halveth.common')\nlocal nearby=require('openmw.nearby')\nlocal I=require('openmw.interfaces')")
        native_chat=native_chat.replace('sent=true', "sent=true\n            local target\n            for _,actor in ipairs(nearby.actors) do if actor.recordId=='arrille' then target=actor end end\n            assert(target and I.HALVETH.talkTo(target),'Arrille targeting failed')")
        native_chat=native_chat.replace("entityMode='jarvis'", "entityMode='npc'").replace(REQUEST_TEXT,NPC_REQUEST)
        native_chat=native_chat.replace("data.speaker=='JARVIS'", "data.speaker=='Arrille'")
    profile = Path(prepared['profile_dir'])
    # This asynchronous model test must keep rendering while another app has
    # focus. Exclusive fullscreen can suspend OpenMW's frame callbacks on
    # Windows; only this disposable profile uses the windowed test setting.
    settings = configparser.ConfigParser(interpolation=None, strict=True)
    settings_path = profile / 'settings.cfg'
    settings.read(settings_path, encoding='utf-8-sig')
    settings['Video']['window mode'] = '0'
    settings['Video']['minimize on focus loss'] = 'false'
    settings_stream = io.StringIO()
    settings.write(settings_stream)
    atomic_text(settings_path, settings_stream.getvalue())
    data = profile / 'data'
    atomic_text(data / 'scripts' / 'halveth_genesis_smoke.lua', native_chat)
    inbox = data / 'bridge' / 'inbox.json'
    atomic_text(inbox, '{}\n')
    log_path = Path(prepared['stdout_log'])
    atomic_text(log_path, '')
    app = WitnessCompanion(state_dir / 'companion', log=log_path, inbox=inbox, model=model)
    http = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    http.app = app
    app.start()
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    process = None
    result = {
        'recorded_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
        'scope': 'Native OpenMW chat submission -> production companion -> live local model -> isolated VFS mailbox -> matching native dialog receipt. Fresh disposable character; no world-changing action.',
        'model': model, 'profile_dir': str(profile), 'log': str(log_path),
        'inbox': str(inbox), 'server_port': http.server_port,
        'test_window': {'mode': 'windowed', 'minimize_on_focus_loss': False},
        'npc_mode': npc_mode,
    }
    try:
        availability = app.models()
        result['model_availability'] = availability
        if not availability['available']:
            raise RuntimeError('Requested local model is not available; no offline answer will count as live model success')
        with log_path.open('w', encoding='utf-8') as stdout:
            process = subprocess.Popen(prepared['command'], cwd=prepared['cwd'],
                                       stdout=stdout, stderr=subprocess.STDOUT)
            result['exit_code'] = process.wait(timeout=190)
        text = log_path.read_text(encoding='utf-8', errors='replace')
        deadline=time.monotonic()+2
        while time.monotonic()<deadline and not any(event.get('type')=='reply_received' for event in app.observed_events):
            time.sleep(.05)
        events=app.observed_events
        sent = [event for event in events if event.get('type') == 'chat']
        received = [event for event in events if event.get('type') == 'reply_received']
        sources = [event for event in events if event.get('type') == 'chat_source']
        result['markers'] = [line for line in text.splitlines() if 'HALVETH_CHAT_' in line]
        result['errors'] = [line for line in text.splitlines() if ' E]' in line or 'Lua error' in line]
        result['sent_requests'] = [{k: event[k] for k in ('sessionId', 'requestId', 'entityMode', 'text')} for event in sent]
        result['received_replies'] = received
        result['model_witnesses'] = app.chat_witnesses
        result['exact_request_match']=len(sent)==1 and sent[0]['text']==request_text
        result['npc_profile_context'] = ({k:sent[0]['context']['npc'].get(k) for k in ('name','recordId','className','disposition','services')}
                                         if npc_mode and len(sent)==1 else None)
        result['exact_source_context_match']=(len(sent)==len(sources)==1 and
            sent[0]['requestId']==sources[0]['requestId'] and sent[0]['text']==sources[0]['text'] and
            sent[0]['context']==json.loads(sources[0]['contextJson']))
        with app.store.connect() as db:
            result['world_actions_recorded'] = db.execute('SELECT count(*) FROM actions').fetchone()[0]
        if len(sent) == len(received) == len(app.chat_witnesses) == 1:
            outgoing, incoming, model_reply = sent[0], received[0], app.chat_witnesses[0]
            result['passed'] = (
                result['exit_code'] == 0 and not result['errors']
                and any('HALVETH_CHAT_PASS' in marker for marker in result['markers'])
                and incoming['sessionId'] == outgoing['sessionId']
                and incoming['requestId'] == outgoing['requestId']
                and incoming['speaker'] == expected_speaker and incoming['uiOpen'] is True
                and incoming['reply'] == model_reply['reply']
                and model_reply['mode'] == 'MODEL_LIVE'
                and result['world_actions_recorded'] == 0
                and result['exact_request_match'] and result['exact_source_context_match']
            )
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        app.stopping.set()
        http.shutdown()
        http.server_close()
        atomic_text(state_dir / 'result.json', json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root', type=Path, default=default_install())
    parser.add_argument('--state-dir', type=Path, default=ROOT / '.local' / 'integration-chat')
    parser.add_argument('--port', type=int, default=18767)
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--npc', action='store_true')
    args = parser.parse_args()
    result = run(args.install_root, args.state_dir.resolve(), args.port, args.model, args.npc)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
