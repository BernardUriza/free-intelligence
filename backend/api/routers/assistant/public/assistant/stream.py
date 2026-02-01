from __future__ import annotations

import json
import uuid as _uuid
from collections.abc import AsyncGenerator

import httpx
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
        import traceback

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            try:
                print("[stream_proxy] 📤 Forwarding to internal endpoint...")
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
                            "response_mode": request.response_mode,  # concise vs explanatory
                        },
                        "session_id": request.session_id,
                        "doctor_id": request.user,
                        "use_memory": request.user is not None,
                    },
                ) as response:
                    print(f"[stream_proxy] ✅ Got response status: {response.status_code}")
                    response.raise_for_status()
                    # Preserve SSE format (data: ...\n\n and event: ...\n) by reading raw bytes
                    chunk_count = 0
                    async for chunk in response.aiter_bytes():
                        chunk_count += 1
                        decoded = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                        if chunk_count <= 3 or "event:" in decoded:
                            print(f"[stream_proxy] 📦 Chunk {chunk_count}: {decoded[:100]}...")
                        yield decoded
                    print(f"[stream_proxy] 🏁 Total chunks: {chunk_count}")
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                print(f"[stream_proxy] ❌ HTTP Error: {error_msg}")
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e!s}"
                print(f"[stream_proxy] ❌ Exception: {error_msg}")
                traceback.print_exc()
                yield f"data: {json.dumps({'error': error_msg})}\n\n"

    return StreamingResponse(
        stream_proxy(),
        media_type="text/event-stream; charset=utf-8",
    )
