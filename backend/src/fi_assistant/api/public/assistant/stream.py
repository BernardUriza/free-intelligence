from __future__ import annotations

import httpx
import json
import uuid as _uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..assistant_schemas import ChatCompletionRequest

router = APIRouter()


@router.post("/assistant/chat/stream")
async def stream_chat_with_assistant(request: ChatCompletionRequest) -> StreamingResponse:
    """OpenAI-style streaming chat completion endpoint.

    Pure HTTP proxy to /internal/llm/chat/stream.
    Workflows layer should NOT contain business logic.
    """
    if not request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set stream=true for this endpoint.",
        )

    if not request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one message is required.",
        )

    last_message = request.messages[-1]
    if last_message.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last message must be from user.",
        )

    # Extract system message
    system_message = None
    for msg in request.messages:
        if msg.role == "system":
            system_message = msg.content
            break

    # Forward to /internal/llm/chat/stream
    async def stream_proxy() -> AsyncGenerator[str]:
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    "http://localhost:7001/internal/llm/chat/stream",
                    json={
                        "persona": request.persona,
                        "message": last_message.content,
                        "context": {
                            "system_message": system_message,
                            "temperature": request.temperature,
                            "max_tokens": request.max_tokens,
                            "top_p": request.top_p,
                            "frequency_penalty": request.frequency_penalty,
                            "presence_penalty": request.presence_penalty,
                            "stop": request.stop,
                            "enable_thinking": request.enable_thinking,
                            "model": request.model,
                        },
                        "session_id": request.session_id,
                        "doctor_id": request.user,
                        "use_memory": request.user is not None,
                    },
                ) as response:
                    response.raise_for_status()
                    # Preserve SSE format (data: ...\n\n) by reading raw bytes
                    async for chunk in response.aiter_bytes():
                        yield chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_proxy(),
        media_type="text/event-stream; charset=utf-8",
    )
