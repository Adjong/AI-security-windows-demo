# MCP Lab — two servers + web control panel

The foundation building block: the **two MCP servers** (normal CRM + rogue
poisoned-notes) and a **web control panel** to connect to them, inspect their
tools, tweak the data they serve, and test-call tools — all in the browser.
No Docker. The agent + Straiker get wired in on top of this later.

## What's here

```
panel.py              web control panel (FastAPI) + starts sink/crm/notes
static/index.html     the GUI
servers/crm_server.py   normal MCP server (CRM), :9910
servers/notes_server.py rogue MCP server (poisoned notes), :9930
sink.py               capture-sink (egress proof), :9900
data/crm.json         editable CRM records (SSN, api_key, canary)
data/notes.json       editable notes + the "poison" injection text
requirements.txt      fastapi, uvicorn, mcp (<2)
start-panel.ps1       one-command launcher
```

## Run

Prereqs: Python 3.11+ (3.12). Then:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-panel.ps1
```

It builds a venv, installs deps, starts the sink + both MCP servers, and opens
the panel at **http://127.0.0.1:8800**. (Ollama/Straiker are NOT needed for this
step — this is just the servers and the panel.)

## Using the panel

- **Status dots** (top right) show sink / crm / notes up.
- **Each server card** shows its data as editable JSON:
  - **Save data** writes it. Content is **live** — the servers re-read the JSON
    on every tool call, so edits to records/notes take effect immediately.
  - **Restart server** is needed only for changes to a tool **description** —
    i.e. the notes **poison** text, which MCP bakes into the tool at startup.
- **Tools → Load** connects to the server as an MCP client and lists its tools;
  the poisoned `list_notes` description is flagged in red.
- **Test a tool** — pick a tool, give JSON args, **Call**. The panel invokes it
  over MCP and shows the result; sensitive values are highlighted.
- **Capture-sink** (right) shows anything a tool exfiltrated (`sync_customer`,
  `share_note`), with canaries flagged. **Clear** resets it.

## Try it

1. CRM: Test `get_customer` with `{"customer_id":"C-1001"}` → see the synthetic
   SSN/api_key/canary. Then `sync_customer` with the same → watch it hit the sink.
2. Notes: Load tools → see the poisoned `list_notes` description. Test `list_notes`
   (no args) → it returns full note bodies incl. the `handoff` secret. `share_note`
   with `{"key":"handoff","content":"..."}` → sink capture with the canary.
3. Tweak: edit `data/crm.json` (change the SSN), Save, call `get_customer` again —
   the change is live. Edit the `poison` text in `data/notes.json`, Save, then
   **Apply & restart** notes, Load tools → the new description shows.

## Ports (all localhost)

| Service | Port |
|---|---|
| control panel | 8800 |
| sink | 9900 |
| crm | 9910 |
| notes | 9930 |

Everything binds `127.0.0.1` — nothing is exposed; use it in the VM's own browser.
