#!/usr/bin/env python3
"""
Capture-sink for the demo. Stands in for an "external" destination so the lab can
prove data egress without anything leaving the machine. Pure stdlib (no Docker).

- POST /<anything>  -> records the body, scans it for canary tokens, 200 "ok"
- GET  /captures    -> JSON list of captures (newest last), for the dashboard
- GET  /reset       -> clears captures (dashboard calls this at the start of a run)

Canary detection: the regex LAB-CANARY-[A-Z0-9]{8,} (synthetic tokens only).
Binds 127.0.0.1:9900 by default (SINK_HOST / SINK_PORT to override).
"""
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


def _now():
    return datetime.now(timezone.utc).isoformat()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep the console quiet; the dashboard shows captures

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
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        canaries = sorted(set(CANARY_RE.findall(raw)))
        rec = {"ts": _now(), "path": self.path, "client": self.client_address[0],
               "body": raw, "canaries_found": canaries}
        with _lock:
            _captures.append(rec)
        self._send(200, "ok")


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[sink] listening on http://{HOST}:{PORT}  (POST to capture, GET /captures)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
