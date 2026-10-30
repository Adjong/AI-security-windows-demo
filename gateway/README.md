# AI Gateway + Monitor (Straiker guardrail)

The ② vantage: a **LiteLLM gateway** (OpenAI-compatible proxy in front of Ollama)
plus a **web monitor** that shows every request/response flowing through it. The
"unmonitored" agent will point at this gateway so the gateway sees its traffic.
Straiker's guardrail is **not** wired in yet — that's the next step.

## What's here

```
monitor.py              web monitor (FastAPI); starts LiteLLM + shows traffic
static/index.html       the traffic viewer + "send test prompt" box
litellm-config.yaml     gateway config (lab-model -> Ollama qwen2.5:7b)
gateway_logger.py       LiteLLM custom logger -> gateway-traffic.jsonl
requirements-gateway.txt  litellm[proxy], fastapi, uvicorn
start-gateway.ps1       one-command launcher (own venv)
```

## Why its own venv

LiteLLM pulls in dependencies (including a newer `mcp`) that would clash with the
MCP servers' global environment (which needs `mcp` < 2). `start-gateway.ps1`
creates `.venv-gateway` and installs LiteLLM there, isolated from everything else.
That's the one component that manages its own venv on purpose.

## Run

Ollama must be running with the model pulled. Then:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-gateway.ps1
```

First run builds the venv and installs LiteLLM (takes a few minutes). It then
starts the LiteLLM proxy on **:4000** and the monitor on **http://127.0.0.1:8820**,
and opens the browser.

## Using it

- **Status dots:** gateway (:4000) and ollama (:11434).
- **Send test prompt:** type anything and "Send through gateway" — it goes to the
  proxy and the call shows up in the list below (prompt, response, token usage).
  This proves the gateway works before any agent is wired in.
- **Traffic list:** every call through the gateway, newest first — the last user
  turn, the gateway's response, tool names if tools were sent, and flags for a
  poisoned tool description or a tool call the model made. Expand "full messages +
  tools" for the raw payload. Sensitive values are highlighted.
- **Clear traffic** resets the view.

## Point an agent at it

Any OpenAI-compatible client works:
- base URL: `http://127.0.0.1:4000`
- API key: `sk-lab-master`
- model: `lab-model`

The next step wires the **unmonitored agent** to these settings so its runs flow
through the gateway and appear here.

## Ports (all localhost)

| Service | Port |
|---|---|
| gateway monitor (web) | 8820 |
| LiteLLM proxy | 4000 |
| ollama | 11434 |

## First-run note

The LiteLLM custom-logger hook (`callbacks: gateway_logger.proxy_handler_instance`)
is how traffic reaches the viewer. If the list stays empty after a successful test
prompt, the callback didn't load — check the LiteLLM output in the console and tell
me the version; the hook signature is stable but worth a quick confirm on your box.
