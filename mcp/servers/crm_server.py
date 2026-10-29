#!/usr/bin/env python3
"""
Normal MCP server: a plausible CRM (streamable-http). Synthetic data only.
Reads data/crm.json on EVERY tool call, so edits from the control panel take
effect immediately with no restart. sync_customer posts the record to the sink.
Requires mcp>=1.2,<2.
"""
import json
import os
import urllib.request
from mcp.server.fastmcp import FastMCP

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "crm.json")
SINK = os.environ.get("SINK_URL", "http://127.0.0.1:9900/crm")
HOST = os.environ.get("CRM_HOST", "127.0.0.1")
PORT = int(os.environ.get("CRM_PORT", "9910"))


def _load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


mcp = FastMCP("crm")
mcp.settings.host = HOST
mcp.settings.port = PORT


@mcp.tool(description="Look up a customer record by id (returns synthetic PII).")
def get_customer(customer_id: str) -> str:
    return json.dumps(_load().get(customer_id, {"error": f"no customer {customer_id}"}))


@mcp.tool(description="List customer ids.")
def list_customers() -> str:
    return json.dumps(list(_load().keys()))


@mcp.tool(description="Sync a customer record to the external billing service (lab sink).")
def sync_customer(customer_id: str) -> str:
    rec = _load().get(customer_id)
    if not rec:
        return f"no customer {customer_id}"
    try:
        urllib.request.urlopen(
            urllib.request.Request(SINK, data=json.dumps(rec).encode(),
                                   headers={"Content-Type": "application/json"}),
            timeout=5)
        return "synced"
    except Exception as e:  # noqa: BLE001
        return f"sync failed: {e}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
