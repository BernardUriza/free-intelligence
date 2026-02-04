"""Assistant Chat API - OpenAI-style chat completion.

Main chat endpoint with persona support, emotional analysis, and RAG.

Endpoints:
- POST /chat - Send message to AI assistant

Migrated from: backend/api/routers/assistant/public/assistant/chat.py
"""

from __future__ import annotations

import time
import uuid as _uuid
from typing import TYPE_CHECKING

from backend.clients.dependencies import get_llm_client_dep
from backend.infrastructure.auth.adapters.fastapi_adapter import User, get_current_user
from backend.observability import chat_events
from backend.observability.logging import CTX_REQUEST_ID
from backend.services.llm.dependencies import get_persona_manager
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status

from .schemas import (
    BehaviorMetrics,
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    EmotionalAnalysis,
    Message,
)

if TYPE_CHECKING:
    from backend.clients.internal_llm_client import InternalLLMClient

logger = get_logger(__name__)
router = APIRouter()

# Use centralized singleton from DI provider
_persona_manager = get_persona_manager()


async def _analyze_emotional_state(
    message: str,
    metrics: BehaviorMetrics,
    llm_client: "InternalLLMClient",
) -> EmotionalAnalysis | None:
    """Analyze emotional state from message and behavior metrics."""
    from .emotional_analysis import analyze_emotional_state

    return await analyze_emotional_state(message, metrics.model_dump(), llm_client)


async def _get_rag_context(
    query: str,
    persona: str,
    clinic_id: str | None,
) -> str | None:
    """Get RAG context for query using DocumentService.

    Searches knowledge base for relevant document chunks and formats
    them as context for the LLM.

    Args:
        query: User's question/message
        persona: Persona ID (not used currently, reserved for filtering)
        clinic_id: Clinic ID for multi-tenancy filtering

    Returns:
        Formatted context string or None if no relevant docs found
    """
    if not clinic_id:
        return None

    try:
        from backend.infrastructure.common.repository_singletons import (
            get_document_repository_singleton,
        )
        from backend.services.document.services.document_service import DocumentService

        repository = get_document_repository_singleton()
        doc_service = DocumentService(repository=repository)

        results = await doc_service.search(
            query=query,
            clinic_id=clinic_id,
            limit=3,  # Top 3 most relevant chunks
            min_score=0.5,  # Only include if relevance > 50%
        )

        if not results:
            return None

        # Format results as context
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Fuente {i}: {result.title}]\n{result.chunk_text}"
            )

        return "\n\n---\n\n".join(context_parts)

    except Exception:
        # RAG is optional - don't fail chat if it's unavailable
        return None


@router.post("/chat", response_model=ChatCompletionResponse)
async def chat_with_assistant(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
    llm_client: "InternalLLMClient" = Depends(get_llm_client_dep),
) -> ChatCompletionResponse:
    """OpenAI-style chat completion endpoint for Free-Intelligence conversations.

    SECURITY: JWT authentication required. RAG search respects user isolation (HIPAA).

    Follows OpenAI Chat Completions API conventions with AURITY-specific extensions.
    """
    try:
        request_id = str(_uuid.uuid4())
        CTX_REQUEST_ID.set(request_id)

        # Validate persona exists in the system
        valid_personas = _persona_manager.list_personas()
        if request.persona not in valid_personas:
            logger.warning(
                "INVALID_PERSONA_REJECTED",
                persona=request.persona,
                valid_personas=valid_personas,
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid persona '{request.persona}'. Valid: {', '.join(valid_personas)}",
            )

        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last message must be from user",
            )

        system_message = None
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
                break

        is_anonymous = not request.user
        doctor_id = request.user if request.user else "anonymous"

        if is_anonymous:
            logger.warning(
                "ASSISTANT_CHAT_ANONYMOUS",
                message="No doctor_id provided, using anonymous storage.",
                session_id=request.session_id,
            )

        context = {
            "persona": request.persona,
            "system_message": system_message,
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stop": request.stop,
            "doctor_id": doctor_id,
            "enable_thinking": request.enable_thinking,
            "response_mode": request.response_mode,
        }

        logger.info(
            "ASSISTANT_CHAT_START",
            message_count=len(request.messages),
            has_system=system_message is not None,
            has_behavior_metrics=request.behavior_metrics is not None,
            session_id=request.session_id,
            doctor_id=doctor_id,
            is_anonymous=is_anonymous,
            persona=request.persona,
            model=request.model,
            memory_enabled=True,
        )

        chat_ctx = {
            "request_id": request_id,
            "trace_id": None,
            "persona": request.persona,
            "response_mode": request.response_mode,
            "prompt_chars": len(last_message.content) if last_message.content else 0,
            "rag_chars": len(context.get("rag_context", "")) if context.get("rag_context") else 0,
            "model": request.model,
            "provider": None,
        }
        chat_events.log_chat_request(chat_ctx)

        emotional_analysis = None
        if request.behavior_metrics is not None:
            emotional_analysis = await _analyze_emotional_state(
                message=last_message.content,
                metrics=request.behavior_metrics,
                llm_client=llm_client,
            )
            logger.info(
                "EMOTIONAL_ANALYSIS_RESULT",
                state=emotional_analysis.state if emotional_analysis else "none",
                confidence=emotional_analysis.confidence if emotional_analysis else 0,
                suggested_tone=emotional_analysis.suggested_tone if emotional_analysis else "none",
            )

        rag_context = await _get_rag_context(
            query=last_message.content,
            persona=request.persona,
            clinic_id=current_user.clinic_id,
        )
        if rag_context:
            context["rag_context"] = rag_context
            logger.info(
                "RAG_CONTEXT_INJECTED",
                chunks_count=len(rag_context.split("---")),
            )

        result = await llm_client.chat(
            persona=request.persona,
            message=last_message.content,
            context=context,
            session_id=request.session_id,
            doctor_id=doctor_id,
            use_memory=True,
            request_id=request_id,
            caller="public",
        )

        usage_dict: dict[str, int] | None = None
        try:
            usage_dict = {
                "prompt_tokens": result.get("prompt_tokens", 0),
                "completion_tokens": result.get("completion_tokens", 0),
            }
        except Exception:
            usage_dict = None
        chat_events.log_llm_call(chat_ctx, usage_dict, llm_ms=result.get("latency_ms", 0))

        completion_id = f"chatcmpl-{_uuid.uuid4().hex}"
        created_timestamp = int(time.time())

        assistant_message = Message(role="assistant", content=result["response"])
        choice = ChatCompletionChoice(index=0, message=assistant_message, finish_reason="stop")

        prompt_tokens = len(last_message.content.split()) * 4
        completion_tokens = len(result["response"].split()) * 4
        total_tokens = prompt_tokens + completion_tokens

        usage = ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        chat_events.log_chat_response(
            chat_ctx, total_ms=result.get("latency_ms", 0), truncated=False
        )

        receptionist_state = None
        if request.receptionist_config:
            # SECURITY: Validate clinic_id matches user's clinic
            requested_clinic_id = request.receptionist_config.get("clinic_id")
            if requested_clinic_id and requested_clinic_id != current_user.clinic_id:
                logger.error(
                    "RECEPTIONIST_CLINIC_IMPERSONATION_BLOCKED",
                    requested_clinic_id=requested_clinic_id,
                    actual_clinic_id=current_user.clinic_id,
                    user_id=current_user.id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Cannot access clinic '{requested_clinic_id}'.",
                )

            receptionist_state = {
                "state": "active",
                "quick_replies": ["Yes", "No", "I need help"],
                "actions": [],
                "metadata": {
                    "clinic_id": current_user.clinic_id,
                    "clinic_name": request.receptionist_config.get("clinic_name"),
                    "session_id": request.session_id,
                },
            }

        # Extract thinking if available (Qwen3 thinking mode)
        thinking = result.get("thinking")
        thinking = thinking.strip() or None if thinking and isinstance(thinking, str) else None

        return ChatCompletionResponse(
            id=completion_id,
            created=created_timestamp,
            model=request.model,
            choices=[choice],
            usage=usage,
            persona=result["persona"],
            emotional_analysis=emotional_analysis,
            receptionist_state=receptionist_state,
            is_anonymous=is_anonymous,
            thinking=thinking,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "ASSISTANT_CHAT_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            session_id=request.session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat completion failed: {e!s}",
        ) from e
