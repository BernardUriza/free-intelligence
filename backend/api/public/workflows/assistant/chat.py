from __future__ import annotations

import time
import uuid as _uuid
from fastapi import APIRouter, HTTPException, status

from backend.clients import get_llm_client
from backend.logger import get_logger
from backend.observability import chat_events
from backend.observability.logging import CTX_REQUEST_ID

from ..assistant_schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    Message,
)
from ..emotional_analysis import analyze_emotional_state
from .rag import _get_rag_context

logger = get_logger(__name__)

router = APIRouter()


@router.post("/assistant/chat", response_model=ChatCompletionResponse)
async def chat_with_assistant(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """OpenAI-style chat completion endpoint for Free-Intelligence conversations.

    Follows OpenAI Chat Completions API conventions with AURITY-specific extensions.
    """
    try:
        request_id = str(_uuid.uuid4())
        CTX_REQUEST_ID.set(request_id)

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
                message=(
                    "No doctor_id provided, using anonymous storage. "
                    "Messages will be saved but not tied to a specific user. "
                    "Frontend should pass 'user' field with Auth0 user.sub for persistent history."
                ),
                session_id=request.session_id,
            )

        context = {
            "persona": request.persona,
            "system_message": system_message,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stop": request.stop,
            "doctor_id": doctor_id,
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

        llm_client = get_llm_client()

        chat_ctx = {
            "request_id": request_id,
            "trace_id": None,
            "persona": request.persona,
            "response_mode": None,
            "prompt_chars": len(last_message.content) if last_message.content else 0,
            "rag_chars": len(context.get("rag_context", "")) if context.get("rag_context") else 0,
            "model": request.model,
            "provider": None,
        }
        chat_events.log_chat_request(chat_ctx)

        emotional_analysis = None
        if request.behavior_metrics is not None:
            emotional_analysis = await analyze_emotional_state(
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
            receptionist_state = {
                "state": "active",
                "quick_replies": ["Yes", "No", "I need help"],
                "actions": [],
                "metadata": {
                    "clinic_id": request.receptionist_config.get("clinic_id"),
                    "clinic_name": request.receptionist_config.get("clinic_name"),
                    "session_id": request.session_id,
                },
            }

        # Extract thinking if available (Qwen3 thinking mode)
        thinking = result.get("thinking")
        if thinking and isinstance(thinking, str):
            thinking = thinking.strip() or None
        else:
            thinking = None

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
