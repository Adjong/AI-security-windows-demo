#!/usr/bin/env python3
"""
MCP control panel (Windows-friendly, no Docker). One command brings up the
capture-sink and the two MCP servers, and serves a web GUI to:
  - see both servers' status and their tools (incl. the poisoned description),
  - edit the data each server serves (live) and restart for description changes,
  - test-call any tool (the panel is an MCP client) and watch the sink.

Run:  python -m uvicorn panel:app --host 127.0.0.1 --port 8800
(or start-panel.ps1). Then open http://127.0.0.1:8800
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket  # WebSocket imported for parity; unused
from fastapi.responses import HTMLResponse, JSONResponse

from mcp import ClientSession
try:
    from mcp.client.streamable_http import streamable_http_client as http_client
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client as http_client

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

SERVERS = {
    "sink":  {"path": os.path.join(HERE, "sink.py"),                 "port": 9900, "url": None},
    "crm":   {"path": os.path.join(HERE, "servers", "crm_server.py"),   "port": 9910, "url": "http://127.0.0.1:9910/mcp"},
    "notes": {"path": os.path.join(HERE, "servers", "notes_server.py"), "port": 9930, "url": "http://127.0.0.1:9930/mcp"},
}
DATA_FILES = {"crm": os.path.join(HERE, "data", "crm.json"),
              "notes": os.path.join(HERE, "data", "notes.json")}
SINK_CAPTURES = "http://127.0.0.1:9900/captures"
SINK_RESET = "http://127.0.0.1:9900/reset"

_procs = {}


def _port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_port(port, want_open=True, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        if _port_open(port) == want_open:
            return True
        time.sleep(0.3)
    return False


def _start(name):
    if _port_open(SERVERS[name]["port"]):
        return
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    _procs[name] = subprocess.Popen([PY, SERVERS[name]["path"]], cwd=HERE, env=env)
    _wait_port(SERVERS[name]["port"], True)


def _stop(name):
    p = _procs.get(name)
    if p:
        try:
            p.terminate()
            p.wait(timeout=10)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    _procs.pop(name, None)
    _wait_port(SERVERS[name]["port"], False, timeout=10)


@asynccontextmanager
async def lifespan(app):
    for n in ("sink", "crm", "notes"):
        _start(n)
    yield
    for n in list(_procs):
        _stop(n)


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    return {n: _port_open(SERVERS[n]["port"]) for n in SERVERS}


@app.get("/api/data/{name}")
def get_data(name: str):
    if name not in DATA_FILES:
        return JSONResponse({"error": "unknown"}, status_code=404)
    with open(DATA_FILES[name], encoding="utf-8") as f:
        return JSONResponse(json.load(f))


@app.post("/api/data/{name}")
async def set_data(name: str, request: Request):
    if name not in DATA_FILES:
        return JSONResponse({"error": "unknown"}, status_code=404)
    raw = (await request.body()).decode("utf-8")
    try:
        parsed = json.loads(raw)  # validate it's JSON before writing
    except ValueError as e:
        return JSONResponse({"error": f"invalid JSON: {e}"}, status_code=400)
    with open(DATA_FILES[name], "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    return {"saved": True, "note": "content is live; restart the server for tool-description/poison changes"}


@app.post("/api/restart/{name}")
def restart(name: str):
    if name not in ("crm", "notes"):
        return JSONResponse({"error": "unknown"}, status_code=404)
    _stop(name)
    _start(name)
    return {"restarted": name, "up": _port_open(SERVERS[name]["port"])}


@app.get("/api/tools/{name}")
async def tools(name: str):
    if name not in ("crm", "notes"):
        return JSONResponse({"error": "unknown"}, status_code=404)
    try:
        async with http_client(SERVERS[name]["url"]) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                ts = (await session.list_tools()).tools
                return {"tools": [{"name": t.name, "description": t.description or "",
                                   "schema": getattr(t, "inputSchema", None)} for t in ts]}
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=502)


@app.post("/api/call")
async def call(request: Request):
    body = await request.json()
    name = body.get("server")
    tool = body.get("tool")
    args = body.get("args") or {}
    if name not in ("crm", "notes"):
        return JSONResponse({"error": "unknown server"}, status_code=404)
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except ValueError as e:
            return JSONResponse({"error": f"args not JSON: {e}"}, status_code=400)
    try:
        async with http_client(SERVERS[name]["url"]) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, args)
                parts = [getattr(b, "text", None) for b in (result.content or [])]
                text = "\n".join(p for p in parts if p) or "(no textual result)"
                return {"result": text}
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=502)


@app.get("/api/captures")
def captures():
    import urllib.request
    try:
        raw = urllib.request.urlopen(SINK_CAPTURES, timeout=3).read().decode("utf-8")
        return JSONResponse(json.loads(raw))
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)


@app.get("/api/captures/reset")
def captures_reset():
    import urllib.request
    try:
        urllib.request.urlopen(SINK_RESET, timeout=3).read()
        return {"reset": True}
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8800)
