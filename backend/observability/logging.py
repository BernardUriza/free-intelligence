from __future__ import annotations

import contextvars
import json
import os
import structlog
import time

CTX_REQUEST_ID = contextvars.ContextVar("request_id", default="-")
CTX_TRACE_ID = contextvars.ContextVar("trace_id", default="-")
FI_DEBUG = os.getenv("FI_DEBUG", "0") == "1"


def _iso_ts(_, __, event_dict):
    event_dict["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return event_dict


def _inject_ids(_, __, event_dict):
    event_dict.setdefault("request_id", CTX_REQUEST_ID.get() or "-")
    event_dict.setdefault("trace_id", CTX_TRACE_ID.get() or "-")
    return event_dict


def _redact_previews(_, __, event_dict):
    # Nunca exponer prompt/respuesta literal en prod
    if not FI_DEBUG:
        event_dict.pop("prompt_preview", None)
        event_dict.pop("rag_preview", None)
    else:
        # Limita a 200 chars si existiera
        for k in ("prompt_preview", "rag_preview"):
            if k in event_dict and isinstance(event_dict[k], str):
                event_dict[k] = event_dict[k][:200]
    return event_dict


def setup_json_logging():
    structlog.configure(
        processors=[
            _iso_ts,
            _inject_ids,
            _redact_previews,
            structlog.processors.add_log_level,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(serializer=json.dumps),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO default
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("chat")
