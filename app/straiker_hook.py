"""
Straiker Defend integration (in-agent) + verdict accessor for the demo UI.

Same /api/v3/detect contract as the lab's agents/common/straiker_hook.py, plus
an inspect() that RETURNS the verdict (so the web dashboard can show it inline).
guard() is kept for compatibility and is implemented on top of inspect().

Modes (STRAIKER_MODE): off | detect | block.
Key from STRAIKER_AGENT_API_KEY, else STRAIKER_API_KEY (loaded from .env).
"""
import os
import json
import uuid
import datetime
import urllib.request
import urllib.error


def _load_dotenv():
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.path.join(here, ".env"), os.path.join(os.getcwd(), ".env")):
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except OSError:
            pass
        break


_load_dotenv()

MODE = os.environ.get("STRAIKER_MODE", "detect").lower()
LOG = os.environ.get("STRAIKER_LOG", "straiker_hook.log")
API_KEY = os.environ.get("STRAIKER_AGENT_API_KEY") or os.environ.get("STRAIKER_API_KEY", "")
API_BASE = os.environ.get("STRAIKER_API_BASE", "https://api.prod.straiker.ai").rstrip("/")
AGENT_ID = os.environ.get("STRAIKER_AGENT_ID", "TC1_agent_mon")
MODEL = os.environ.get("STRAIKER_MODEL", os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"))
TIMEOUT = float(os.environ.get("STRAIKER_TIMEOUT", "8"))
VERBOSE = os.environ.get("STRAIKER_VERBOSE", "") not in ("", "0", "false", "False")
SESSION_ID = os.environ.get("STRAIKER_SESSION_ID") or ("lab-" + uuid.uuid4().hex[:16])

IS_V3 = API_KEY.startswith("sk_agt_")
V3_PATH = "/api/v3/detect"
V1_PATH = "/api/v1/detect/webhook"
BLOCK_DECISIONS = ("block", "deny")

_LAST_INPUT = {"text": ""}
_LAST_TOOLCALL = {"tool": "tool", "args": {}}
_CALL_ID = "call_lab"
_TOOLS = {"schema": None}


def set_tools(schema):
    _TOOLS["schema"] = schema or None


def new_session(session_id=None):
    """Reset per-run state so each demo run groups as its own Straiker session."""
    global SESSION_ID
    SESSION_ID = session_id or ("lab-" + uuid.uuid4().hex[:16])
    _LAST_INPUT["text"] = ""
    _LAST_TOOLCALL.update({"tool": "tool", "args": {}})
    return SESSION_ID


class Blocked(Exception):
    pass


def _log(event, detail):
    rec = {"ts": datetime.datetime.utcnow().isoformat() + "Z",
           "mode": MODE, "event": event, "detail": detail}
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def _headers():
    h = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}
    if IS_V3:
        if AGENT_ID:
            h["x-s6r-agent"] = AGENT_ID
        if SESSION_ID:
            h["x-claude-code-session-id"] = SESSION_ID
    else:
        h["X-Straiker-Webhook-Format"] = "litellm"
    return h


def _chat_completion(content=None, tool_name=None, tool_args=None):
    msg = {"role": "assistant", "content": content}
    if tool_name is not None:
        msg["tool_calls"] = [{"id": _CALL_ID, "type": "function",
                              "function": {"name": tool_name,
                                           "arguments": json.dumps(tool_args or {})}}]
        finish = "tool_calls"
    else:
        finish = "stop"
    return {"object": "chat.completion",
            "choices": [{"index": 0, "finish_reason": finish, "message": msg}]}


def _parse_json(payload):
    try:
        d = json.loads(payload)
        return d if isinstance(d, dict) else {}
    except (ValueError, TypeError):
        return {}


def _v3_body(stage, payload):
    tools = _TOOLS["schema"]
    if stage == "input":
        _LAST_INPUT["text"] = payload
        body = {"model": MODEL, "messages": [{"role": "user", "content": payload}],
                "session_id": SESSION_ID}
        if tools:
            body["tools"] = tools
        return body
    if stage == "tool_result":
        d = _parse_json(payload)
        name = d.get("tool") or _LAST_TOOLCALL["tool"]
        assistant_msg = {"role": "assistant", "content": None,
                         "tool_calls": [{"id": _CALL_ID, "type": "function",
                                         "function": {"name": name,
                                                      "arguments": json.dumps(_LAST_TOOLCALL.get("args") or {})}}]}
        tool_msg = {"role": "tool", "tool_call_id": _CALL_ID, "name": name,
                    "content": d.get("result", payload)}
        body = {"model": MODEL,
                "messages": [{"role": "user", "content": _LAST_INPUT["text"]},
                             assistant_msg, tool_msg],
                "session_id": SESSION_ID}
        if tools:
            body["tools"] = tools
        return body
    request_body = {"model": MODEL, "messages": [{"role": "user", "content": _LAST_INPUT["text"]}]}
    if tools:
        request_body["tools"] = tools
    if stage == "tool_call":
        d = _parse_json(payload)
        _LAST_TOOLCALL["tool"] = d.get("tool", "tool")
        _LAST_TOOLCALL["args"] = d.get("args", {})
        sse = _chat_completion(tool_name=d.get("tool", "tool"), tool_args=d.get("args", {}))
    else:
        sse = _chat_completion(content=payload)
    return {"straiker_phase": "response-sync", "model": MODEL, "request": request_body,
            "sse": json.dumps(sse), "session_id": SESSION_ID}


def _v1_body(stage, payload):
    is_request = stage in ("input", "tool_result")
    content = {"texts": [payload]}
    env = {"schema_version": "1",
           "event": {"type": "pre_call" if is_request else "post_call", "id": "lab:" + stage},
           "request": content if is_request else {"texts": []},
           "context": {"call_surface": "in_agent", "model": MODEL, "session_id": SESSION_ID},
           "identity": {}, "application": {"source": AGENT_ID}}
    if not is_request:
        env["response"] = content
    return env


def _decision(body):
    nested = body.get("straiker")
    verdict = nested if isinstance(nested, dict) else body
    decision = None
    hook = body.get("hookSpecificOutput")
    if isinstance(hook, dict):
        d = hook.get("permissionDecision")
        if isinstance(d, str) and d:
            decision = d.lower()
    if decision is None:
        a = verdict.get("action")
        if isinstance(a, str) and a:
            decision = a.lower()
    blocked_by = verdict.get("blocked_by") or []
    controls = ", ".join(str(c) for c in blocked_by) if blocked_by else ""
    blocked = (decision in BLOCK_DECISIONS) or (decision == "blocked") or bool(blocked_by)
    reason = (verdict.get("block_message") or verdict.get("deny_reason")
              or body.get("stopReason") or body.get("blocked_reason")
              or ("blocked: " + controls if controls else "policy"))
    # Surface any named findings/categories for the UI, when present.
    findings = verdict.get("findings") or verdict.get("categories") or []
    if isinstance(findings, list):
        findings = [str(x) for x in findings]
    else:
        findings = [str(findings)]
    return blocked, reason, controls, findings


def _call_straiker(stage, payload):
    url = API_BASE + (V3_PATH if IS_V3 else V1_PATH)
    body = _v3_body(stage, payload) if IS_V3 else _v1_body(stage, payload)
    data = json.dumps(body).encode("utf-8")
    if VERBOSE:
        _log("request", {"url": url, "body": body})
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    if VERBOSE:
        _log("response", {"body": parsed})
    if not isinstance(parsed, dict):
        return False, "", "", []
    return _decision(parsed)


def inspect(stage: str, payload: str) -> dict:
    """Relay one stage to Straiker and RETURN the verdict (for the UI).

    status: off | no_api_key | unreachable | ok
    Never raises; the caller decides whether to enforce (see guard()).
    """
    result = {"stage": stage, "status": "off", "blocked": False, "reason": "",
              "controls": "", "findings": [], "canary_present": "LAB-CANARY-" in (payload or "")}
    if MODE == "off":
        return result
    if not API_KEY:
        result["status"] = "no_api_key"
        _log(stage, {"straiker": "no_api_key", "canary_present": result["canary_present"]})
        return result
    try:
        blocked, reason, controls, findings = _call_straiker(stage, payload)
        result.update({"status": "ok", "blocked": blocked, "controls": controls,
                       "findings": findings, "reason": reason if blocked else ""})
        _log(stage, {"straiker": "ok", "blocked": blocked, "controls": controls,
                     "findings": findings, "reason": result["reason"],
                     "canary_present": result["canary_present"]})
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as e:
        result["status"] = "unreachable"
        result["error"] = type(e).__name__ + ": " + str(e)
        _log(stage, {"straiker": "unreachable", "error": result["error"],
                     "canary_present": result["canary_present"]})
    return result


def guard(stage: str, payload: str):
    """Compatibility wrapper: inspect + enforce in block mode."""
    r = inspect(stage, payload)
    if MODE == "block":
        enforce = r.get("blocked") or (
            r["status"] in ("no_api_key", "unreachable")
            and stage in ("tool_call", "output") and r["canary_present"])
        if enforce:
            _log("blocked", {"stage": stage, "by": r.get("controls") or "straiker"})
            raise Blocked("Straiker blocked " + stage + ": " + (r.get("reason") or "canary egress"))
    return payload
