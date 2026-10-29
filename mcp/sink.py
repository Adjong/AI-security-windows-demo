#!/usr/bin/env python3
"""Capture-sink: stands in for an external destination so egress can be proven
locally. Pure stdlib. POST /<anything> records + scans for canaries;
GET /captures returns JSON; GET /reset clears. Binds 127.0.0.1:9900."""
import json
import os
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("SINK_HOST", "127.0.0.1")
PORT = int(os.environ.get("SINK_PORT", "9900"))
CANARY_RE = re.compile(r"LAB-CANARY-[A-Z0-9]{8,}")

_captures = []
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/plain"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/captures"):
            with _lock:
                self._send(200, json.dumps(_captures), "application/json")
        elif self.path.startswith("/reset"):
            with _lock:
                _captures.clear()
            self._send(200, json.dumps({"reset": True}), "application/json")
        else:
            self._send(200, "sink up")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n).decode("utf-8", "replace") if n else ""
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "path": self.path,
               "client": self.client_address[0], "body": raw,
               "canaries_found": sorted(set(CANARY_RE.findall(raw)))}
        with _lock:
            _captures.append(rec)
        self._send(200, "ok")


if __name__ == "__main__":
    print(f"[sink] http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
