from __future__ import annotations

import structlog

from backend.observability.log_spec import REQUIRED_FIELDS, ChatEvent

log = structlog.get_logger("chat")


def _ensure_fields(base: dict) -> dict:
    # Rellena campos faltantes con valores neutros para cumplir contrato
    defaults = {
        "user_id": "-",
        "org_id": "-",
        "model": "-",
        "provider": "-",
        "prompt_chars": 0,
        "rag_chars": 0,
        "token_in": 0,
        "token_out": 0,
        "latency_ms": 0,
        "status": "ok",
        "response_mode": "-",
        "persona_id": "-",
    }
    out = {**defaults, **base}
    # Orden estable (opcional, útil para debugging humano)
    return {k: out.get(k, "") for k in REQUIRED_FIELDS if k in out or True} | out


def log_chat_request(ctx: dict):
    payload = _ensure_fields(
        {
            **ctx,
        }
    )
    # Note: event is passed as first arg to structlog, not in payload
    payload.pop("event", None)  # Remove if present to avoid duplicate
    log.info(ChatEvent.CHAT_REQUEST.value, **payload)


def log_llm_call(ctx: dict, usage: dict | None, llm_ms: int, status: str = "ok"):
    usage = usage or {}
    payload = _ensure_fields(
        {
            "token_in": usage.get("prompt_tokens", 0),
            "token_out": usage.get("completion_tokens", 0),
            "latency_ms": llm_ms,
            "status": status,
            **ctx,
        }
    )
    # Note: event is passed as first arg to structlog, not in payload
    payload.pop("event", None)  # Remove if present to avoid duplicate
    log.info(ChatEvent.LLM_CALL.value, **payload)


def log_chat_response(ctx: dict, total_ms: int, truncated: bool = False, status: str = "ok"):
    payload = _ensure_fields(
        {
            "latency_ms": total_ms,
            "status": status,
            **ctx,
            "truncated": truncated,
        }
    )
    # Note: event is passed as first arg to structlog, not in payload
    payload.pop("event", None)  # Remove if present to avoid duplicate
    log.info(ChatEvent.CHAT_RESPONSE.value, **payload)


def log_chat_error(ctx: dict, err_kind: str, status_code: int):
    payload = _ensure_fields(
        {
            "status": str(status_code),
            **ctx,
            "error_kind": err_kind,
        }
    )
    # Note: event is passed as first arg to structlog, not in payload
    payload.pop("event", None)  # Remove if present to avoid duplicate
    log.error(ChatEvent.CHAT_ERROR.value, **payload)
