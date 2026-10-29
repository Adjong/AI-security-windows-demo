# AI Security Lab — Straiker Demo Dashboard (Windows)

A graphical, browser-based front end for the lab. One command brings up the
capture-sink, both MCP servers, and a web dashboard that drives the agent and
shows **each step with Straiker's verdict inline** — no Docker, no terminal
watching required.

It mirrors the Linux lab's scenarios:
- **A — Exfiltration:** agent reads a CRM record (synthetic PII + canary) and syncs it.
- **B — Tool-description poisoning:** a notes server with a poisoned tool description
  and an over-exposed `list_notes` that returns secret-bearing content.

Two vantage points:
- **In-agent ①** — the Straiker hook runs inside the agent (Ollama direct).
- **Gateway ②** — model calls route through a LiteLLM proxy (optional; see below).

Two modes:
- **Guided** — pick vantage + scenario, click **Run**.
- **Free chat** — type your own task and **Run custom**.

---

## Prerequisites (fresh Windows Server)

1. **Python 3.11+** on PATH — https://www.python.org/downloads/windows/
2. **Ollama** — https://ollama.com — then pull the model:
   ```
   ollama pull qwen2.5:7b
   ```
3. A **Straiker agent key** (`sk_agt_…`) for the in-agent hook.

No Docker required. The sink and both MCP servers run as native Python processes.

## Setup & run

1. Unzip this folder anywhere (e.g. `C:\straiker-demo-ui`).
2. Copy `.env.example` to `.env` and paste your key:
   ```
   STRAIKER_AGENT_API_KEY=sk_agt_...
   STRAIKER_MODE=detect
   ```
3. Double-click **`start-demo.ps1`** (or run it from PowerShell). It creates a
   virtual environment, installs dependencies, launches everything, and opens
   the browser at **http://127.0.0.1:8800**.

   If PowerShell blocks the script:
   ```
   powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
   ```

That's it — the top-right dots show the sink/crm/notes services as green when up.

## Using it

- **Guided:** choose **In-agent ①** or **Gateway ②**, choose **A** or **B**, click **Run**.
  Watch the timeline fill with the agent's tool calls and results, each followed by a
  Straiker verdict badge (green = clear, red = risk/blocked). Sensitive values
  (SSN, canary, API key) are highlighted. The right panel shows the tools offered
  (poisoned descriptions flagged) and anything that reached the capture-sink.
- **Free chat:** type any task and **Run custom** to drive the same agent live.
- **Block mode:** set `STRAIKER_MODE=block` in `.env` and restart to have Straiker
  actually stop the turn when it blocks (the timeline shows the BLOCK).

## Gateway (②) vantage — optional

The gateway vantage routes the model through a LiteLLM proxy. It only works if a
LiteLLM proxy is running and reachable (default `http://127.0.0.1:4000`, model
`lab-model`). Set `GATEWAY_URL` / `GATEWAY_KEY` / `GATEWAY_MODEL` in `.env`. If you
aren't running the gateway, just use the **In-agent ①** vantage.

## Ports

| Service | Port | What |
|---|---|---|
| dashboard | 8800 | the web UI |
| sink | 9900 | capture-sink (exfil proof) |
| crm | 9910 | scenario A MCP server |
| notes | 9930 | scenario B MCP server |

If a port is already in use, the app reuses whatever is already listening there.

## Troubleshooting

- **A service dot stays red:** another process may hold its port, or `mcp`/deps
  didn't install. Check the PowerShell window for errors from `sink` / `crm` / `notes`.
- **`mcp.server.fastmcp` import error:** you have `mcp` 2.x. `requirements.txt` pins
  `mcp>=1.2,<2`; make sure the venv installed it (`pip show mcp`).
- **Agent hangs on first run:** Ollama is loading the model into memory — the first
  call after boot can take a bit. Pre-warm with `ollama run qwen2.5:7b ""`.
- **"no API key" verdicts:** your `.env` key isn't set or didn't load; confirm
  `STRAIKER_AGENT_API_KEY` (or `STRAIKER_API_KEY`) is in `.env` next to `app.py`.

## Notes

All data is synthetic; canaries (`LAB-CANARY-…`) authorize nothing; `share_note` /
`sync_customer` post only to the local capture-sink — nothing leaves the machine
except the Straiker detect calls the hook makes with your key.
