#!/usr/bin/env python3
"""Optional real OpenMW/HTTP/mailbox test. Starts a fresh, disposable game.

This verifies native actions with the deterministic tool path and deliberately
does not invoke an LLM. Run manually; not included in unit-test discovery.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import Companion, Handler, ThreadingHTTPServer
from scripts.prepare_profile import atomic_text, default_install, prepare

NATIVE_TEST = r'''local core=require('openmw.core')
local self=require('openmw.self')
local types=require('openmw.types')
local started=nil
return {engineHandlers={onFrame=function()
    if not self.cell then return end
    if not started then started=core.getRealTime() end
    local elapsed=core.getRealTime()-started
    local gold=types.Actor.inventory(self):countOf('gold_001')
    if elapsed>=10 and gold==250 then
        print('HALVETH_MAILBOX_PASS gold='..gold..' cell='..self.cell.name)
        core.quit()
    elseif elapsed>=40 then
        print('HALVETH_MAILBOX_FAIL gold='..gold)
        core.quit()
    end
end}}
'''


def run(install_root: Path, state_dir: Path, port: int) -> dict:
    args = argparse.Namespace(install_root=install_root, state_dir=state_dir,
                              source_profile="max", profile="beauty", smoke=True,
                              copy_saves=False, reset_settings=True)
    receipt = prepare(args)
    profile = Path(receipt["profile_dir"])
    data = profile / "data"
    atomic_text(data / "scripts" / "halveth_genesis_smoke.lua", NATIVE_TEST)
    inbox = data / "bridge" / "inbox.json"
    atomic_text(inbox, '{}\n')
    log_path = Path(receipt["stdout_log"])
    atomic_text(log_path, '')
    app = Companion(state_dir / "companion", log=log_path, inbox=inbox, model="genesis-integration-no-llm")
    http = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    http.app = app
    app.start()
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{http.server_port}"

    def request(path, payload=None, token=None):
        headers = {}
        if token:
            headers['X-Halveth-Token'] = token
        body = json.dumps(payload).encode() if payload is not None else None
        if body:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(base + path, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)

    process = None
    result = {"recorded_at": datetime.now(timezone.utc).isoformat(), "passed": False,
              "scope": "Real OpenMW context -> local HTTP chat action offer -> HTTP dispatch -> isolated VFS mailbox -> native inventory and result receipt. Deterministic tool path; no LLM call.",
              "profile_dir": str(profile), "log": str(log_path), "inbox": str(inbox)}
    try:
        with log_path.open('w', encoding='utf-8') as stdout:
            process = subprocess.Popen(receipt['command'], cwd=receipt['cwd'], stdout=stdout, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 35
            status = None
            while time.monotonic() < deadline:
                status = request('/api/status')
                if status['game']['connected']:
                    break
                if process.poll() is not None:
                    raise RuntimeError("Game exited before context arrived")
                time.sleep(.25)
            if not status or not status['game']['connected']:
                raise TimeoutError("Native context not received")
            result['initial_gold'] = status['game']['player']['gold']
            result['session_id'] = status['game']['sessionId']
            token = status['csrfToken']
            chat = request('/api/chat', {'message':'Gib mir 250 Gold', 'entityId':'jarvis'}, token)
            offered = next(action for action in chat['actions'] if action['kind']=='give_gold')
            result['chat_mode'] = chat['mode']
            result['dispatch'] = request('/api/action', {'id':offered['id']}, token)
            executed = None
            while time.monotonic() < deadline:
                status = request('/api/status')
                executed = next((action for action in status['actions'] if action['id']==offered['id']), None)
                if executed:
                    break
                if process.poll() is not None:
                    raise RuntimeError("Game exited before native acknowledgement")
                time.sleep(.25)
            if not executed or executed['status']!='executed':
                raise RuntimeError(f"Native action not completed: {executed}")
            result['receipt'] = executed
            result['exit_code'] = process.wait(timeout=40)
        text = log_path.read_text(encoding='utf-8', errors='replace')
        result['markers'] = [line for line in text.splitlines() if 'HALVETH_MAILBOX_' in line]
        result['errors'] = [line for line in text.splitlines() if ' E]' in line or 'Lua error' in line]
        result['passed'] = (result['initial_gold']==0 and executed['after']['gold']-executed['before']['gold']==250
                            and result['exit_code']==0 and any('HALVETH_MAILBOX_PASS' in line for line in result['markers'])
                            and not result['errors'])
    except Exception as exc:
        result['error'] = f"{type(exc).__name__}: {exc}"
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
        atomic_text(state_dir / 'result.json', json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-root', type=Path, default=default_install())
    parser.add_argument('--state-dir', type=Path, default=ROOT / '.local' / 'integration')
    parser.add_argument('--port', type=int, default=18766)
    args = parser.parse_args()
    result = run(args.install_root, args.state_dir.resolve(), args.port)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
