# fi_observability/hooks.py
# Easy-to-use hooks for logging LLM calls from existing code

import logging
from typing import Optional

from .logger import get_llm_logger
from .models import CallStatus, LLMCallCreate

logger = logging.getLogger(__name__)


def log_llm_call(
    *,
    model: str,
    provider: str,
    latency_ms: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    status: str = "success",
    error_message: str | None = None,
    prompt_preview: str = "",
    response_preview: str = "",
    client_id: str | None = None,
    session_id: str | None = None,
    persona: str | None = None,
    prompt_hash: str | None = None,
    response_hash: str | None = None,
    metadata: dict | None = None,
) -> str | None:
    """
    Log an LLM call to the observability database.

    This is a simple hook function that can be called from anywhere
    without needing to import multiple classes.

    Returns the call ID if successful, None if logging fails.

    Example usage in existing code:
        from backend.infrastructure.observability.hooks import log_llm_call

        log_llm_call(
            model=model_name,
            provider=primary_provider,
            latency_ms=latency_ms,
            prompt_tokens=tokens_used,
            completion_tokens=0,
            status="success",
            prompt_preview=prompt[:500],
            response_preview=response_text[:500],
            client_id=effective_doctor_id,
            session_id=request.session_id,
            persona=effective_persona,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
        )
    """
    try:
        # Map status string to enum
        status_enum = CallStatus.SUCCESS
        if status == "error":
            status_enum = CallStatus.ERROR
        elif status == "timeout":
            status_enum = CallStatus.TIMEOUT
        elif status == "cancelled":
            status_enum = CallStatus.CANCELLED

        call = LLMCallCreate(
            model=model,
            provider=provider,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status=status_enum,
            error_message=error_message,
            prompt_preview=prompt_preview[:500] if prompt_preview else "",
            response_preview=response_preview[:500] if response_preview else "",
            client_id=client_id,
            session_id=session_id,
            persona=persona,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            metadata=metadata or {},
        )

        llm_logger = get_llm_logger()
        call_id = llm_logger.log_call(call)

        logger.debug(f"Observability: logged LLM call {call_id}")
        return call_id

    except Exception as e:
        # Never fail the main request due to observability logging
        logger.warning(f"Observability logging failed: {e}")
        return None


def log_llm_error(
    *,
    model: str,
    provider: str,
    latency_ms: int,
    error_message: str,
    error_type: str = "unknown",
    prompt_preview: str = "",
    client_id: str | None = None,
    session_id: str | None = None,
    persona: str | None = None,
) -> str | None:
    """
    Log a failed LLM call to the observability database.

    Convenience wrapper for logging errors.
    """
    return log_llm_call(
        model=model,
        provider=provider,
        latency_ms=latency_ms,
        status="error",
        error_message=f"{error_type}: {error_message}",
        prompt_preview=prompt_preview,
        client_id=client_id,
        session_id=session_id,
        persona=persona,
    )
