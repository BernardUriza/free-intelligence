from __future__ import annotations

import asyncio
import json
import time
import uuid as _uuid
from collections.abc import AsyncGenerator

from backend.clients import get_llm_client
from backend.observability.logging import CTX_REQUEST_ID
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_llm.services.persona.manager import PersonaManager
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..assistant_schemas import ChatCompletionRequest, ChatCompletionStreamResponse

logger = get_logger(__name__)

router = APIRouter()

# Initialize persona manager for validation
_persona_manager = PersonaManager()


@router.post("/assistant/chat/stream")
async def stream_chat_with_assistant(request: ChatCompletionRequest) -> StreamingResponse:
    """OpenAI-style streaming chat completion endpoint.

    Returns Server-Sent Events (SSE) stream following OpenAI streaming format.
    """
    if not request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /assistant/chat for non-streaming requests. Set stream=true for this endpoint.",
        )

    # Validate persona exists in the system
    valid_personas = _persona_manager.list_personas()
    if request.persona not in valid_personas:
        logger.warning(
            "INVALID_PERSONA_REJECTED_STREAM",
            persona=request.persona,
            valid_personas=valid_personas,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid persona '{request.persona}'. Valid personas: {', '.join(valid_personas)}",
        )

    async def generate_stream() -> AsyncGenerator[str]:
        try:
            if not request.messages:
                yield f"data: {json.dumps({'error': 'At least one message is required'})}\n\n"
                return

            last_message = request.messages[-1]
            if last_message.role != "user":
                yield f"data: {json.dumps({'error': 'Last message must be from user'})}\n\n"
                return

            system_message = None
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                    break

            doctor_id = request.user if request.user else None

            context: dict[str, object] = {
                "persona": request.persona,
                "system_message": system_message,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stop": request.stop,
                "enable_thinking": request.enable_thinking,  # Toggle thinking/reasoning mode
            }

            if request.model:
                context["model"] = request.model

            try:
                if isinstance(request.model, str) and request.model.lower().startswith("qwen3"):
                    context["max_tokens"] = min(int(context.get("max_tokens") or 256), 256)
            except Exception:
                pass

            if doctor_id:
                context["doctor_id"] = doctor_id

            completion_id = f"chatcmpl-{_uuid.uuid4().hex}"
            created_timestamp = int(time.time())

            llm_client = get_llm_client()

            request_id = str(_uuid.uuid4())
            CTX_REQUEST_ID.set(request_id)

            initial_chunk = ChatCompletionStreamResponse(
                id=completion_id,
                created=created_timestamp,
                model=request.model,
                choices=[{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            )
            yield f"data: {initial_chunk.model_dump_json()}\n\n"

            try:
                timeout_seconds = 30  # Production timeout for slow models like Qwen3
                logger.info(
                    "SSE_TIMEOUT_START", timeout_seconds=timeout_seconds, model=request.model
                )
                # Use asyncio.timeout() context manager for more reliable cancellation
                async with asyncio.timeout(timeout_seconds):
                    result = await llm_client.chat(
                        persona=request.persona,
                        message=last_message.content,
                        context=context,
                        session_id=request.session_id,
                        doctor_id=doctor_id,
                        use_memory=doctor_id is not None,
                        request_id=request_id,
                        caller="public",
                    )
                logger.info(
                    "SSE_TIMEOUT_SUCCESS",
                    model=request.model,
                    response_length=len(result.get("response", "")),
                )
            except TimeoutError:
                logger.warning(
                    "SSE_TIMEOUT_FIRED", model=request.model, timeout_seconds=timeout_seconds
                )
                timeout_msg = "El modelo está tardando más de lo esperado. Intenta nuevamente o reduce la complejidad."
                stream_chunk = ChatCompletionStreamResponse(
                    id=completion_id,
                    created=created_timestamp,
                    model=request.model,
                    choices=[
                        {"index": 0, "delta": {"content": timeout_msg}, "finish_reason": None}
                    ],
                )
                yield f"data: {stream_chunk.model_dump_json()}\n\n"

                final_chunk = ChatCompletionStreamResponse(
                    id=completion_id,
                    created=created_timestamp,
                    model=request.model,
                    choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return

            thinking = result.get("thinking")
            if isinstance(thinking, str) and thinking.strip():
                meta_event = {"thinking": thinking.strip()}
                yield f"event: meta\ndata: {json.dumps(meta_event)}\n\n"

            response_text = result.get("response", "")

            if not response_text:
                final_chunk = ChatCompletionStreamResponse(
                    id=completion_id,
                    created=created_timestamp,
                    model=request.model,
                    choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return

            chunk_size = 60
            for i in range(0, len(response_text), chunk_size):
                chunk_text = response_text[i : i + chunk_size]
                stream_chunk = ChatCompletionStreamResponse(
                    id=completion_id,
                    created=created_timestamp,
                    model=request.model,
                    choices=[{"index": 0, "delta": {"content": chunk_text}, "finish_reason": None}],
                )
                yield f"data: {stream_chunk.model_dump_json()}\n\n"

            final_chunk = ChatCompletionStreamResponse(
                id=completion_id,
                created=created_timestamp,
                model=request.model,
                choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(
                "STREAM_CHAT_FAILED",
                error=str(e),
                error_type=type(e).__name__,
                session_id=request.session_id,
                exc_info=True,
            )
            error_chunk = json.dumps(
                {"error": {"message": f"Stream failed: {e!s}", "type": "internal_error"}}
            )
            yield f"data: {error_chunk}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Content-Type": "text/event-stream; charset=utf-8"},
    )
