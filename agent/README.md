# Agent — MCP Lab (no Straiker yet)

A web interface for an LLM agent (Ollama) that **connects to the two MCP servers
the control panel is running**, decides which tools to call to carry out a task,
and streams every step to the browser. No Straiker monitoring at this stage —
this is just the agent driving the tools.

## Prereqs / run order

1. Start the **MCP control panel** first (so sink + crm + notes are up):
   `Code\mcp\start-panel.ps1`
2. Make sure **Ollama** is running with the model pulled (`ollama list` shows
   `qwen2.5:7b`).
3. Start the agent (separate window):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\start-agent.ps1
   ```
   Opens at **http://127.0.0.1:8810**.

(Python + packages come from your prereq script; this folder adds only `ollama`
to the list if it wasn't already installed.)

## Using it

- **Status dots:** ollama / crm / notes / sink — all green means you're ready.
- **Scenario A · CRM (exfil):** the agent looks up customer C-1001 and syncs it —
  watch it call `get_customer` then `sync_customer`, and the record (with the
  canary) land in the capture-sink.
- **Scenario B · Notes (poisoning):** the agent is asked only to summarise the
  standup note, but the poisoned `list_notes` description tries to hijack it into
  sharing notes — watch what it does and what reaches the sink.
- **Free task:** pick a server and type your own instruction, then Run custom.

The right panel shows the capture-sink after each run (canaries flagged).

## What this is / isn't

- **Is:** a real agent loop — Ollama chooses tools from the MCP server's schema,
  calls them over MCP, feeds results back, and answers. Temperature is pinned to
  0 so runs are repeatable.
- **Isn't (yet):** monitored. There's no in-agent Straiker hook and no gateway.
  The next step wires Straiker in so it flags the SSN / the poisoning.

## Ports (all localhost)

| Service | Port | Owned by |
|---|---|---|
| agent UI | 8810 | this app |
| control panel | 8800 | Code\mcp |
| crm / notes / sink | 9910 / 9930 / 9900 | Code\mcp |
| ollama | 11434 | Ollama |
