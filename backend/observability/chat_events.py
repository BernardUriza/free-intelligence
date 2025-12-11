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
            "event": ChatEvent.CHAT_REQUEST.value,
            **ctx,
        }
    )
    log.info(ChatEvent.CHAT_REQUEST.value, **payload)


def log_llm_call(ctx: dict, usage: dict, llm_ms: int, status: str = "ok"):
    payload = _ensure_fields(
        {
            "event": ChatEvent.LLM_CALL.value,
            "token_in": usage.get("prompt_tokens", 0),
            "token_out": usage.get("completion_tokens", 0),
            "latency_ms": llm_ms,
            "status": status,
            **ctx,
        }
    )
    log.info(ChatEvent.LLM_CALL.value, **payload)


def log_chat_response(ctx: dict, total_ms: int, truncated: bool = False, status: str = "ok"):
    payload = _ensure_fields(
        {
            "event": ChatEvent.CHAT_RESPONSE.value,
            "latency_ms": total_ms,
            "status": status,
            **ctx,
            "truncated": truncated,
        }
    )
    log.info(ChatEvent.CHAT_RESPONSE.value, **payload)


def log_chat_error(ctx: dict, err_kind: str, status_code: int):
    payload = _ensure_fields(
        {
            "event": ChatEvent.CHAT_ERROR.value,
            "status": str(status_code),
            **ctx,
            "error_kind": err_kind,
        }
    )
    log.error(ChatEvent.CHAT_ERROR.value, **payload)
