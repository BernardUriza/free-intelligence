from __future__ import annotations

import time


def _make_log_entry(level: str, **kwargs):
    base = {
        "ts": int(time.time()),
        "level": level,
        "request_id": kwargs.get("request_id"),
        "trace_id": kwargs.get("trace_id"),
        "user_id": kwargs.get("user_id"),
        "org_id": kwargs.get("org_id"),
        "persona_id": kwargs.get("persona_id"),
        "response_mode": kwargs.get("response_mode"),
        "model": kwargs.get("model"),
        "provider": kwargs.get("provider"),
        "prompt_chars": kwargs.get("prompt_chars", 0),
        "rag_chars": kwargs.get("rag_chars", 0),
        "token_in": kwargs.get("token_in", 0),
        "token_out": kwargs.get("token_out", 0),
        "latency_ms": kwargs.get("latency_ms", 0),
        "status": kwargs.get("status", "ok"),
    }
    base.update({k: v for k, v in kwargs.items() if k not in base})
    return base
