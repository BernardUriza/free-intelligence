from __future__ import annotations

import hashlib
import time
import uuid as _uuid

import ulid
from backend.utils.common.logging.logger import get_logger
from infrastructure.storage.services.trace_store import get_trace_store
from backend.utils.redactor import redact_and_hash_once
from fastapi import APIRouter, HTTPException

from ..assistant_schemas import ChatCompletionRequest

logger = get_logger(__name__)
trace_store = get_trace_store()

router = APIRouter()


@router.post("/assistant/chat/_dry-run")
async def assistant_chat_dry_run(
    request: ChatCompletionRequest,
    log_level: str = "DEBUG",
    trace_ttl_s: int = 600,
    enable_dry_run: bool = True,
    redact_rules: list[str] | None = None,
) -> dict:
    """Dry-run diagnostic endpoint.

    Resolves persona, response_mode (from messages/system), builds system prompt markers,
    and returns metadata without including user message text (only hash and length).
    """
    request_id = str(_uuid.uuid4())

    last_message = request.messages[-1]
    user_len = len(last_message.content) if last_message and last_message.content else 0
    user_hash = hashlib.sha256((last_message.content or "").encode()).hexdigest()[:8]

    try:
        from backend.core.services.llm.services.persona.manager import PersonaManager

        pm = PersonaManager()
        persona_cfg = pm.get_effective_persona(request.persona, user_id=request.user)
    except Exception as e:
        logger.warning("DRY_RUN_PERSONA_NOT_FOUND", persona=request.persona, error=str(e))
        raise HTTPException(status_code=400, detail="PersonaNotFound")

    context = {"response_mode": None, "rag_context": None}

    response_mode = None
    for msg in request.messages:
        if msg.role == "system" and "MODE:" in msg.content:
            if "CONCISE" in msg.content.upper():
                response_mode = "concise"
            elif "EXPLANATORY" in msg.content.upper():
                response_mode = "explanatory"

    full_prompt = pm.build_system_prompt(request.persona, context)
    max_rag_chars = 2048
    truncated_prompt = full_prompt[:max_rag_chars]
    _redacted_prompt, meta = redact_and_hash_once(truncated_prompt, redact_rules)

    trace_id = ulid.new().str
    trace = {
        "request_id": request_id,
        "trace_id": trace_id,
        "persona_id": persona_cfg.persona,
        "response_mode": response_mode or "explanatory",
        "model": request.model,
        "prompt_chars": len(truncated_prompt),
        "rag_chars": meta.get("length", 0),
        "dry_run": True,
        "ts": int(time.time()),
    }
    trace_store.put(request_id, trace)

    return {
        "request_id": request_id,
        "persona_id": persona_cfg.persona,
        "response_mode_resolved": response_mode or "explanatory",
        "system_markers": {
            "concise": "<!--MODE:CONCISE-->"
            if (response_mode or "").lower() == "concise"
            else None,
            "explanatory": "<!--MODE:EXPLANATORY-->"
            if (response_mode or "").lower() == "explanatory"
            else "<!--MODE:EXPLANATORY-->",
            "rag_begin": "<!--RAG:BEGIN-->",
            "rag_end": "<!--RAG:END-->",
        },
        "rag_bytes": meta.get("length", 0),
        "model": request.model,
        "timeouts": {"llm_timeout_s": 30},
        "user_message": {"hash8": user_hash, "length": user_len},
    }


@router.get("/assistant/chat/_trace/{request_id}")
async def assistant_chat_trace(request_id: str):
    trace = trace_store.get(request_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found or expired")
    return trace
