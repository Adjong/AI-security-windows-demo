#!/usr/bin/env python3
"""
Gateway monitor: starts the LiteLLM proxy and serves a web page that shows every
request/response flowing through it (read from gateway-traffic.jsonl). Includes a
"send test prompt" box so you can generate traffic without an agent yet.

Run from the gateway venv:  python -m uvicorn monitor:app --host 127.0.0.1 --port 8820
(or start-gateway.ps1). Then open http://127.0.0.1:8820

No Straiker guardrail yet -- this is just the gateway + visibility.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
CONFIG = os.path.join(HERE, "litellm-config.yaml")
TRAFFIC = os.path.join(HERE, "gateway-traffic.jsonl")
GATEWAY_PORT = 4000
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "sk-lab-master")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")

_proc = {}


def _port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def _wait_port(port, timeout=40.0):
    end = time.time() + timeout
    while time.time() < end:
        if _port_open("127.0.0.1", port):
            return True
        time.sleep(0.4)
    return False


def _start_gateway():
    if _port_open("127.0.0.1", GATEWAY_PORT):
        print("[monitor] gateway already on 4000, reusing")
        return
    exe = os.path.join(os.path.dirname(PY), "litellm.exe")
    cmd = ([exe] if os.path.exists(exe) else ["litellm"]) + \
          ["--config", CONFIG, "--host", "127.0.0.1", "--port", str(GATEWAY_PORT)]
    env = dict(os.environ)
    env["PYTHONPATH"] = HERE + os.pathsep + env.get("PYTHONPATH", "")  # so gateway_logger imports
    print("[monitor] starting LiteLLM:", " ".join(cmd))
    _proc["gw"] = subprocess.Popen(cmd, cwd=HERE, env=env)
    if _wait_port(GATEWAY_PORT):
        print("[monitor] gateway up on 4000")
    else:
        print("[monitor] WARNING: gateway did not open 4000 in time")


def _stop_gateway():
    p = _proc.get("gw")
    if p:
        try:
            p.terminate()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app):
    _start_gateway()
    yield
    _stop_gateway()


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    oh, op = OLLAMA_HOST.split(":")
    return {"gateway": _port_open("127.0.0.1", GATEWAY_PORT),
            "ollama": _port_open(oh, int(op))}


@app.get("/api/traffic")
def traffic():
    items = []
    if os.path.exists(TRAFFIC):
        try:
            with open(TRAFFIC, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            items.append(json.loads(line))
                        except ValueError:
                            pass
        except OSError:
            pass
    return JSONResponse(items[-100:])


@app.get("/api/reset")
def reset():
    try:
        open(TRAFFIC, "w").close()
    except OSError:
        pass
    return {"reset": True}


@app.post("/api/test")
async def test(request: Request):
    body = await request.json()
    prompt = body.get("prompt") or "Say hello in one short sentence."
    payload = json.dumps({"model": "lab-model",
                          "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{GATEWAY_PORT}/v1/chat/completions",
                                 data=payload,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + MASTER_KEY},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode("utf-8"))
        msg = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return {"ok": True, "reply": msg}
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"{type(e).__name__}: {e}"}, status_code=502)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8820)
