"""
LiteLLM custom logger: records each request/response passing through the gateway
to gateway-traffic.jsonl, which the monitor web app reads and displays.

Referenced from litellm-config.yaml as:
    litellm_settings:
      callbacks: gateway_logger.proxy_handler_instance
"""
import datetime
import json
import os

try:
    from litellm.integrations.custom_logger import CustomLogger
except Exception:  # noqa: BLE001  # allow import without litellm (e.g. syntax checks)
    class CustomLogger:  # minimal stand-in
        pass

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gateway-traffic.jsonl")


def _jsonable(o):
    if o is None or isinstance(o, (dict, list, str, int, float, bool)):
        return o
    if hasattr(o, "model_dump"):
        try:
            return o.model_dump()
        except Exception:  # noqa: BLE001
            pass
    return str(o)


def _record(kwargs, response_obj, outcome):
    opt = kwargs.get("optional_params") or {}
    return {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "outcome": outcome,
        "model": kwargs.get("model"),
        "messages": _jsonable(kwargs.get("messages")),
        "tools": _jsonable(opt.get("tools")),
        "response": _jsonable(response_obj),
    }


def _write(rec):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except Exception:  # noqa: BLE001  # logging must never break the gateway
        pass


class GatewayLogger(CustomLogger):
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        _write(_record(kwargs, response_obj, "success"))

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        _write(_record(kwargs, response_obj, "success"))

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        _write(_record(kwargs, response_obj, "failure"))

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        _write(_record(kwargs, response_obj, "failure"))


proxy_handler_instance = GatewayLogger()
