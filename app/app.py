#!/usr/bin/env python3
"""
Straiker lab demo dashboard (Windows-friendly, no Docker).

One command brings up everything:
  - the capture-sink (sink.py)
  - the CRM MCP server (servers/crm_server.py, scenario A)
  - the poisoned-notes MCP server (servers/notes_server.py, scenario B)
  - this web app, which drives the agent and streams each step + Straiker's
    inline verdict to the browser over a WebSocket.

Run:  python -m uvicorn app:app --host 127.0.0.1 --port 8800
(or use start-demo.ps1). Then open http://127.0.0.1:8800
"""
import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

SERVICES = [
    ("sink", os.path.join(HERE, "sink.py"), 9900),
    ("crm", os.path.join(HERE, "servers", "crm_server.py"), 9910),
    ("notes", os.path.join(HERE, "servers", "notes_server.py"), 9930),
]

_procs = []


def _port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def _wait_port(port, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        if _port_open("127.0.0.1", port):
            return True
        time.sleep(0.3)
    return False


def _start_services():
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    for name, path, port in SERVICES:
        if _port_open("127.0.0.1", port):
            print(f"[app] {name} already running on {port}, reusing")
            continue
        print(f"[app] starting {name}: {path}")
        p = subprocess.Popen([PY, path], cwd=HERE, env=env)
        _procs.append((name, p))
    for name, path, port in SERVICES:
        if not _wait_port(port):
            print(f"[app] WARNING: {name} did not open port {port} in time")
        else:
            print(f"[app] {name} is up on {port}")


def _stop_services():
    for name, p in _procs:
        try:
            p.terminate()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app):
    _start_services()
    yield
    _stop_services()


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    return {name: _port_open("127.0.0.1", port) for name, _, port in SERVICES}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    import runner  # imported lazily so service startup isn't blocked by model deps
    try:
        data = await websocket.receive_json()

        async def emit(ev):
            await websocket.send_json(ev)

        await runner.run(data.get("vantage", "agent"),
                         data.get("scenario", "A"),
                         data.get("task"),
                         emit)
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        try:
            await websocket.send_json({"type": "error", "message": f"{type(e).__name__}: {e}"})
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8800)
