#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openagi_client import OpenAgiClient


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        body = b"{}"
        if path == "/health":
            body = b'{"ok":true}'
        elif path == "/proactive/suggestions":
            body = json.dumps(
                [{"id": "s1", "title": "Suggest A", "description": "do a"}]
            ).encode()
        elif path == "/pending-actions":
            body = json.dumps(
                {"actions": [{"id": "a1", "title": "Act B", "body": "details"}]}
            ).encode()
        elif path == "/skills/suggested":
            body = json.dumps([{"name": "skill-c", "description": "mine this"}]).encode()
        elif path == "/observations/search":
            body = json.dumps([{"id": "o1", "content": "act now"}]).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(length)
        if self.path == "/memory/remember":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"stored":true}')
            return
        self.send_response(404)
        self.end_headers()


def test_collect_signals() -> None:
    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        client = OpenAgiClient(f"http://127.0.0.1:{port}")
        assert client.health()
        signals = client.collect_signals(include_observations=True)
        sources = {s.get("_source") for s in signals}
        assert "proactive_suggestion" in sources
        assert "pending_action" in sources
        assert "skill_suggested" in sources
        assert "observation" in sources
        assert client.memory_remember("fact") == {"stored": True}
    finally:
        server.shutdown()
