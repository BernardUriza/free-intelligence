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
from backend.compat import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from backend.api.public.workflows.assistant_websocket import broadcast_new_message
from backend.logger import get_logger
from backend.policy.policy_loader import get_policy_loader
from backend.providers.llm import llm_generate
from backend.schemas.llm_audit_policy import require_audit_log
from backend.services.llm.conversation_memory import get_memory_manager
from backend.services.llm.persona_manager import PersonaManager

from .schemas import ChatRequest, ChatResponse

router = APIRouter()
logger = get_logger(__name__)
persona_mgr = PersonaManager()
policy_loader = get_policy_loader()


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
        # Auto-enable memory for Azure GPT-4 (infinite conversation policy)
        primary_provider = policy_loader.get_primary_provider()
        auto_memory_enabled = False
        effective_doctor_id = request.doctor_id

        if primary_provider == "azure":
            # Azure GPT-4: Enable memory by default
            auto_memory_enabled = True

            # Use provided doctor_id or default to "system"
            if not effective_doctor_id:
                effective_doctor_id = "system"
                logger.info(
                    "MEMORY_AUTO_ENABLED_AZURE",
                    provider=primary_provider,
                    doctor_id=effective_doctor_id,
                    message="Conversational memory enabled automatically for Azure GPT-4",
                )

        # Validate memory requirements (only if explicitly requested)
        if request.use_memory and not request.doctor_id and not auto_memory_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="doctor_id is required when use_memory=True",
            )

        # Intelligent persona routing (Two-Model Strategy)
        effective_persona = request.persona

        if request.persona == "auto" or not request.persona:
            # Use cheap routing to decide persona
            effective_persona = persona_mgr.route_persona(request.message)
            logger.info(
                "PERSONA_AUTO_ROUTED",
                user_message_preview=request.message[:50],
                routed_to=effective_persona,
                cost_pattern="Two-Model Strategy (Haiku routing + GPT-4 response)",
            )

        # Get persona configuration
        try:
            persona_config = persona_mgr.get_persona(effective_persona)
        except ValueError as e:
            logger.warning(
                "INTERNAL_LLM_INVALID_PERSONA",
                persona=effective_persona,
                available=persona_mgr.list_personas(),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

        # Build prompt with conversation memory if enabled (explicit or auto)
        memory_enabled = request.use_memory or auto_memory_enabled

        if memory_enabled and effective_doctor_id:
            # Get memory manager
            memory = get_memory_manager(effective_doctor_id)

            # Store user message
            user_timestamp = datetime.now(UTC).isoformat()
            memory.store_interaction(
                session_id=request.session_id or "unknown",
                role="user",
                content=request.message,
                persona=request.persona,
            )

            # Broadcast user message to all connected devices (WebSocket)
            await broadcast_new_message(
                doctor_id=effective_doctor_id,
                role="user",
                content=request.message,
                timestamp=user_timestamp,
                persona=request.persona,
            )

            # Get conversation context
            context = memory.get_context(
                current_message=request.message,
                session_id=request.session_id,
            )

            # Build enriched prompt with memory
            system_prompt = persona_mgr.build_system_prompt(effective_persona, request.context)
            prompt = memory.build_prompt(
                context=context,
                system_prompt=system_prompt,
                current_message=request.message,
            )

            logger.info(
                "INTERNAL_LLM_MEMORY_ENABLED",
                doctor_id=effective_doctor_id,
                session_id=request.session_id,
                recent_count=len(context.recent),
                relevant_count=len(context.relevant),
                total_interactions=context.total_interactions,
                auto_enabled=auto_memory_enabled,
            )
        else:
            # Build prompt without memory (original behavior)
            prompt = persona_mgr.build_system_prompt(effective_persona, request.context)

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

        # Store assistant response in memory if enabled
        if memory_enabled and effective_doctor_id:
            memory = get_memory_manager(effective_doctor_id)
            assistant_timestamp = datetime.now(UTC).isoformat()
            memory.store_interaction(
                session_id=request.session_id or "unknown",
                role="assistant",
                content=response_text,
                persona=request.persona,
            )

            # Broadcast assistant response to all connected devices (WebSocket)
            await broadcast_new_message(
                doctor_id=effective_doctor_id,
                role="assistant",
                content=response_text,
                timestamp=assistant_timestamp,
                persona=request.persona,
            )

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
            memory_enabled=memory_enabled,
            auto_memory_enabled=auto_memory_enabled,
            provider=primary_provider,
        )

        return ChatResponse(
            response=response_text,
            persona=effective_persona,  # Return effective persona (may differ if auto-routed)
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
