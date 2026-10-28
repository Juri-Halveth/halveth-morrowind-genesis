import http.client
import json
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import BoundedHTTPServer, Handler


class FastHandler(Handler):
    timeout = 0.3
    body_deadline_seconds = 0.35
    header_deadline_seconds = 0.35


class TwoSlotServer(BoundedHTTPServer):
    max_active_requests = 2


class FakeApp:
    csrf = 'test-token'

    def __init__(self):
        self.calls = []

    def chat(self, message, entity_id):
        self.calls.append(('chat', message, entity_id))
        return {'reply': 'Hallo'}

    def dispatch(self, action_id):
        self.calls.append(('action', action_id))
        return {'status': 'queued'}


class HttpBodyTests(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.httpd = TwoSlotServer(('127.0.0.1', 0), FastHandler)
        self.httpd.app = self.app
        self.worker = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.worker.join(timeout=2)

    def raw_post(self, path='/api/action', body=b'', declared_length=None,
                 extra_headers='', half_close=False):
        if declared_length is None:
            declared_length = len(body)
        peer = socket.create_connection(('127.0.0.1', self.httpd.server_port), timeout=2)
        peer.settimeout(2)
        headers = (f'POST {path} HTTP/1.1\r\n'
                   f'Host: 127.0.0.1:{self.httpd.server_port}\r\n'
                   'X-Halveth-Token: test-token\r\n'
                   f'Content-Length: {declared_length}\r\n'
                   f'{extra_headers}\r\n').encode('ascii')
        peer.sendall(headers + body)
        if half_close:
            peer.shutdown(socket.SHUT_WR)
        return peer

    def response(self, peer):
        try:
            answer = http.client.HTTPResponse(peer)
            answer.begin()
            payload = json.loads(answer.read())
            return answer.status, payload
        finally:
            peer.close()

    def test_normal_chat_and_action_keep_their_response(self):
        base = f'http://127.0.0.1:{self.httpd.server_port}'
        for path, body, expected in (
            ('/api/chat', {'message': 'Hallo', 'entityId': 'jarvis'}, {'reply': 'Hallo'}),
            ('/api/action', {'id': 'a1'}, {'status': 'queued'}),
        ):
            request = urllib.request.Request(base + path,
                data=json.dumps(body).encode('utf-8'),
                headers={'X-Halveth-Token': 'test-token',
                         'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=2) as answer:
                self.assertEqual(answer.status, 200)
                self.assertEqual(json.load(answer), expected)
        self.assertEqual(self.app.calls, [('chat', 'Hallo', 'jarvis'), ('action', 'a1')])

    def test_incomplete_body_times_out_even_on_unknown_post_path(self):
        for path in ('/api/action', '/not-an-api'):
            with self.subTest(path=path):
                peer = self.raw_post(path, b'{', declared_length=100)
                status, _ = self.response(peer)
                self.assertEqual(status, 408)
        self.assertEqual(self.app.calls, [])

    def test_valid_json_prefix_with_short_eof_is_not_executed(self):
        body = b'{"id":"a1"}'
        peer = self.raw_post(body=body, declared_length=len(body) + 5, half_close=True)
        status, _ = self.response(peer)
        self.assertEqual(status, 400)
        self.assertEqual(self.app.calls, [])

    def test_trickle_cannot_extend_total_body_deadline(self):
        peer = self.raw_post(body=b'{', declared_length=100)
        try:
            time.sleep(0.12)
            peer.sendall(b'"')
            time.sleep(0.12)
            peer.sendall(b'i')
            status, _ = self.response(peer)
        finally:
            peer.close()
        self.assertEqual(status, 408)
        self.assertEqual(self.app.calls, [])

    def test_ambiguous_framing_and_wrong_token_are_rejected(self):
        for extra in ('Transfer-Encoding: chunked\r\n', 'Content-Length: 2\r\n'):
            with self.subTest(extra=extra):
                peer = self.raw_post(body=b'{}', extra_headers=extra)
                status, _ = self.response(peer)
                self.assertEqual(status, 400)
        base = f'http://127.0.0.1:{self.httpd.server_port}/api/action'
        request = urllib.request.Request(base, data=b'{"id":"a1"}',
                                         headers={'X-Halveth-Token': 'wrong'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()
        self.assertEqual(self.app.calls, [])

    def test_trickled_header_cannot_hold_a_worker_past_total_deadline(self):
        peer = socket.create_connection(('127.0.0.1', self.httpd.server_port), timeout=2)
        peer.settimeout(2)
        try:
            peer.sendall(b'POST /api/action HTTP/1.1\r\nX-Slow: ')
            for byte in (b'a', b'b'):
                time.sleep(0.12)
                peer.sendall(byte)
            try:
                self.assertEqual(peer.recv(1), b'')
            except ConnectionResetError:
                pass
        finally:
            peer.close()
        self.assertEqual(self.app.calls, [])

    def test_active_request_budget_rejects_excess_and_recovers(self):
        peers = []
        try:
            for _ in range(self.httpd.max_active_requests):
                peer = socket.create_connection(('127.0.0.1', self.httpd.server_port), timeout=2)
                peer.settimeout(2)
                peer.sendall(b'POST /api/action HTTP/1.1\r\nX-Slow: ')
                peers.append(peer)
            deadline = time.monotonic() + 0.2
            while self.httpd._request_slots._value:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            extra = socket.create_connection(('127.0.0.1', self.httpd.server_port), timeout=2)
            extra.settimeout(2)
            try:
                try:
                    self.assertEqual(extra.recv(1), b'')
                except ConnectionResetError:
                    pass
            finally:
                extra.close()
            peers[0].close()
            deadline = time.monotonic() + 1
            while self.httpd._request_slots._value == 0:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            valid = self.raw_post(body=b'{"id":"a1"}')
            status, payload = self.response(valid)
            self.assertEqual((status, payload), (200, {'status': 'queued'}))
        finally:
            for peer in peers:
                peer.close()


if __name__ == '__main__':
    unittest.main()
