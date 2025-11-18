"""
Internal LLM Chat Endpoint - Ultra Observable

CRITICAL: Este endpoint solo debe ser accesible internamente.
Middleware InternalOnlyMiddleware bloquea acceso externo.

Propósito:
- Centralizar TODAS las interacciones conversacionales con LLMs
- Logging ultra detallado (prompt completo, response completo, tokens, timing)
- Observabilidad minuciosa de cada llamada
- Audit trail completo con hashes
"""

import hashlib
import json
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from backend.logger import get_logger
from backend.providers.llm import llm_generate
from backend.schemas.llm_audit_policy import require_audit_log
from backend.services.llm.persona_manager import PersonaManager

from .schemas import ChatRequest, ChatResponse

router = APIRouter()
logger = get_logger(__name__)
persona_mgr = PersonaManager()


@router.post("/chat", response_model=ChatResponse)
@require_audit_log
async def internal_llm_chat(request: ChatRequest) -> ChatResponse:
    """INTERNAL: Conversación con Free-Intelligence (ultra observable).

    Este endpoint provee logging ultra detallado de TODA interacción:
    - Prompt completo (hasheado para audit)
    - Response completa (hasheada)
    - Tokens consumidos
    - Latencia end-to-end
    - Modelo usado
    - Contexto de la llamada

    Args:
        request: Mensaje + persona + contexto

    Returns:
        Response con metadata completa de observabilidad

    Raises:
        403: Si se intenta llamar desde fuera (middleware bloquea)
        400: Si la persona no existe
        500: Si LLM falla
    """
    start_time = time.time()
    prompt = ""  # Initialize for exception handling

    try:
        # Get persona configuration
        try:
            persona_config = persona_mgr.get_persona(request.persona)
        except ValueError as e:
            logger.warning(
                "INTERNAL_LLM_INVALID_PERSONA",
                persona=request.persona,
                available=persona_mgr.list_personas(),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

        # Build prompt
        prompt = persona_config.system_prompt

        if request.context:
            prompt += f"\n\nContext:\n{json.dumps(request.context, indent=2)}"

        prompt += f"\n\nUser: {request.message}\n\nAssistant:"

        # Hash prompt for audit (ultra observable)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        logger.info(
            "INTERNAL_LLM_CHAT_START",
            persona=request.persona,
            message_length=len(request.message),
            context_keys=list(request.context.keys()) if request.context else [],
            prompt_hash=prompt_hash[:12],  # First 12 chars for logs
            prompt_length=len(prompt),
            session_id=request.session_id,
        )

        # Call LLM via router
        llm_response = llm_generate(
            prompt,
            temperature=persona_config.temperature,
            max_tokens=persona_config.max_tokens,
        )

        response_text = llm_response.content.strip()
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract tokens (handle different response formats)
        tokens_used = 0
        model_name = "unknown"

        if hasattr(llm_response, "usage") and llm_response.usage:
            tokens_used = llm_response.usage.total_tokens
        if hasattr(llm_response, "model"):
            model_name = llm_response.model

        # Ultra detailed logging
        logger.info(
            "INTERNAL_LLM_CHAT_SUCCESS",
            persona=request.persona,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model=model_name,
            prompt_hash=prompt_hash[:12],
            response_hash=response_hash[:12],
            response_length=len(response_text),
            session_id=request.session_id,
        )

        return ChatResponse(
            response=response_text,
            persona=request.persona,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model=model_name,
            prompt_hash=prompt_hash[:12],
            response_hash=response_hash[:12],
            logged_at=datetime.now(UTC).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "INTERNAL_LLM_CHAT_FAILED",
            persona=request.persona,
            error=str(e),
            error_type=type(e).__name__,
            session_id=request.session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM chat failed: {e!s}",
        ) from e
