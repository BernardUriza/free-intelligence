from __future__ import annotations

from enum import Enum


class ChatEvent(str, Enum):
    CHAT_REQUEST = "CHAT_REQUEST"
    LLM_CALL = "LLM_CALL"
    CHAT_RESPONSE = "CHAT_RESPONSE"
    CHAT_ERROR = "CHAT_ERROR"


# Orden y presencia obligatoria
REQUIRED_FIELDS = (
    "ts",
    "level",
    "event",
    "request_id",
    "trace_id",
    "user_id",
    "org_id",
    "persona_id",
    "response_mode",
    "model",
    "provider",
    "prompt_chars",
    "rag_chars",
    "token_in",
    "token_out",
    "latency_ms",
    "status",
)
