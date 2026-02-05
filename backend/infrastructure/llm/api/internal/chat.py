"""Internal LLM Chat Endpoint - Ultra Observable.

CRITICAL: This endpoint should only be accessible internally.
InternalOnlyMiddleware blocks external access.

Purpose:
- Centralize ALL conversational LLM interactions
- Ultra-detailed logging (full prompt, full response, tokens, timing)
- Meticulous observability of each call
- Complete audit trail with hashes

Endpoints:
- POST /chat - Main chat with full observability
- POST /chat/stream - Server-Sent Events streaming
- POST /chat/debug - Debug endpoint for introspection

Note: Do NOT use `from __future__ import annotations` here.
FastAPI needs runtime access to type annotations for Request and Pydantic models.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Infrastructure Migration)
Updated: 2026-02-03 (SOLID refactor - extracted services)
"""

import json
import time
import uuid as _uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.config import CORPUS_PATH
from backend.infrastructure.common.policy_provider import get_policy_loader_dep
from backend.policy.interfaces.ipolicy_loader import IPolicyLoader
from backend.providers import get_provider, sanitize_error_message
from backend.repositories.audit_repository import AuditRepository
from backend.schemas.llm.audit_policy import require_audit_log
from backend.services.audit.services.audit_service import AuditService
from backend.services.llm.dependencies import get_persona_manager
from backend.services.llm.services.conversation_memory import get_memory_manager
from backend.utils.common.logging.logger import get_logger

from .schemas import ChatRequest, ChatResponse
from .services import ChatContext, ChatService

router = APIRouter()
logger = get_logger(__name__)
persona_mgr = get_persona_manager()

# DI for PolicyLoader via FastAPI Depends
PolicyLoaderDep = Annotated[IPolicyLoader, Depends(get_policy_loader_dep)]

# Initialize audit service for persona metrics tracking
audit_repo = AuditRepository(CORPUS_PATH)
audit_service = AuditService(audit_repo)


@router.post("/chat", response_model=ChatResponse)
@require_audit_log
async def internal_llm_chat(
    http_request: Request,
    request: ChatRequest,
    policy_loader: PolicyLoaderDep,
) -> ChatResponse:
    """INTERNAL: Conversation with Free-Intelligence (ultra observable).

    This endpoint provides ultra-detailed logging of ALL interactions:
    - Full prompt (hashed for audit)
    - Full response (hashed)
    - Tokens consumed
    - End-to-end latency
    - Model used
    - Call context

    Args:
        http_request: FastAPI request
        request: Message + persona + context
        policy_loader: PolicyLoader singleton (FastAPI Depends injection)

    Returns:
        Response with complete observability metadata

    Raises:
        403: If called from outside (middleware blocks)
        400: If persona doesn't exist
        500: If LLM fails
    """
    start_time = time.time()
    prompt = ""

    incoming_request_id = http_request.headers.get("x-fi-request-id")
    if not incoming_request_id:
        incoming_request_id = str(_uuid.uuid4())

    logger.info(
        "CHAT_REQUEST",
        request_id=incoming_request_id,
        persona=request.persona,
        message_len=len(request.message),
    )

    try:
        # Use ChatService for orchestration
        chat_service = ChatService(
            policy_loader=policy_loader,
            audit_service=audit_service,
        )

        ctx = ChatContext(
            message=request.message,
            persona=request.persona,
            session_id=request.session_id,
            doctor_id=request.doctor_id,
            use_memory=request.use_memory,
            provider=request.provider,
            context=request.context,
            messages=request.messages,
        )

        result = await chat_service.process_chat(ctx)

        return ChatResponse(
            response=result.response,
            thinking=result.thinking,
            persona=result.persona,
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
            model=result.model,
            voice=result.voice,
            prompt_hash=result.prompt_hash,
            response_hash=result.response_hash,
            logged_at=result.logged_at,
        )

    except ValueError as e:
        # Invalid persona or missing doctor_id for memory
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "INTERNAL_LLM_CHAT_FAILED",
            persona=request.persona,
            error=str(e),
            error_type=type(e).__name__,
            session_id=request.session_id,
            exc_info=True,
        )

        # Log error to observability
        chat_service = ChatService(policy_loader=policy_loader)
        chat_service.log_error(
            ctx=ChatContext(
                message=request.message,
                persona=request.persona,
                session_id=request.session_id,
                doctor_id=request.doctor_id,
            ),
            error=e,
            prompt=prompt,
            latency_ms=latency_ms,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM chat failed: {e!s}",
        ) from e


@router.post("/chat/stream")
async def internal_llm_chat_stream(
    request: ChatRequest,
    policy_loader: PolicyLoaderDep,
):
    """INTERNAL: Streaming chat endpoint for real-time response delivery.

    Ultra-observable streaming with:
    - Per-chunk timing and byte tracking
    - Memory context logging if enabled
    - Provider selection and config logging
    - Fallback detection and logging
    - Complete error context

    Args:
        request: Chat request with message and persona
        policy_loader: PolicyLoader singleton (FastAPI Depends injection)

    Returns Server-Sent Events (SSE) with streaming chunks from LLM.
    """
    import asyncio

    from fastapi.responses import StreamingResponse

    start_time = time.time()
    stream_request_id = str(_uuid.uuid4())

    async def stream_generator():
        """Generate SSE stream of LLM responses with real-time token delivery."""
        try:
            yield f"data: {json.dumps({'status': 'started'})}\n\n"

            if not request.message:
                logger.warning("STREAM_EMPTY_MESSAGE", request_id=stream_request_id)
                yield f"data: {json.dumps({'error': 'Message required'})}\n\n"
                return

            logger.info(
                "STREAM_REQUEST_RECEIVED",
                request_id=stream_request_id,
                persona=request.persona,
                message_length=len(request.message),
                session_id=request.session_id,
            )

            # Get persona config for response_format
            try:
                persona_config = persona_mgr.get_persona(request.persona)
                json_format = persona_config.response_format
            except Exception as persona_err:
                logger.warning(
                    "STREAM_PERSONA_CONFIG_FAILED",
                    request_id=stream_request_id,
                    error=str(persona_err),
                )
                json_format = None

            # Setup memory
            memory_enabled = request.use_memory and request.doctor_id
            memory = None
            if memory_enabled:
                memory = get_memory_manager(request.doctor_id)
                if memory is None:
                    memory_enabled = False

            # Build prompt
            if memory_enabled and memory is not None:
                memory.store_interaction(
                    session_id=request.session_id or "unknown",
                    role="user",
                    content=request.message,
                    persona=request.persona,
                )
                system_prompt = persona_mgr.build_system_prompt(request.persona, request.context)
                memory_context = memory.get_context(request.message, request.session_id)
                prompt = memory.build_prompt(
                    context=memory_context,
                    system_prompt=system_prompt,
                    current_message=request.message,
                )
            else:
                prompt = persona_mgr.build_system_prompt(request.persona, request.context)

                if request.messages and len(request.messages) > 0:
                    conversation_parts = []
                    for msg in request.messages:
                        if msg.role == "system":
                            continue
                        elif msg.role == "user":
                            conversation_parts.append(f"User: {msg.content}")
                        elif msg.role == "assistant":
                            conversation_parts.append(f"Assistant: {msg.content}")

                    if conversation_parts:
                        prompt += "\n\n" + "\n\n".join(conversation_parts)
                    prompt += "\n\nAssistant:"
                else:
                    if request.context:
                        prompt += f"\n\nContext:\n{json.dumps(request.context, indent=2)}"
                    prompt += f"\n\nUser: {request.message}\n\nAssistant:"

            # Get provider
            provider_name = request.provider or policy_loader.get_primary_provider()
            provider_config = policy_loader.get_provider_config(provider_name) or {}
            llm_provider = get_provider(provider_name, provider_config)

            # Check streaming support
            if not hasattr(llm_provider, "generate_stream"):
                logger.warning(
                    "STREAM_FALLBACK_NO_STREAM_METHOD",
                    request_id=stream_request_id,
                    provider=provider_name,
                )
                response = llm_provider.generate(
                    prompt,
                    model=request.context.get("model") if request.context else None,
                    temperature=request.context.get("temperature", 0.7) if request.context else 0.7,
                    max_tokens=request.context.get("max_tokens", 512) if request.context else 512,
                )
                yield f"data: {json.dumps({'content': response.content})}\n\n"
                return

            # Stream response
            chunk_count = 0
            total_bytes = 0
            model_name = (request.context.get("model") if request.context else None) or provider_name

            logger.info(
                "STREAM_STREAMING_START",
                request_id=stream_request_id,
                provider=provider_name,
                persona=request.persona,
            )

            gen = await asyncio.to_thread(
                lambda: llm_provider.generate_stream(
                    prompt,
                    model=request.context.get("model") if request.context else None,
                    temperature=request.context.get("temperature", 0.7) if request.context else 0.7,
                    max_tokens=request.context.get("max_tokens", 512) if request.context else 512,
                    enable_thinking=request.context.get("enable_thinking", False) if request.context else False,
                    format=json_format,
                )
            )

            thinking_buffer = ""
            content_buffer = ""

            def format_content_chunk(text: str) -> str:
                chunk_data = {
                    "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]
                }
                return f"data: {json.dumps(chunk_data)}\n\n"

            for chunk_data in gen:
                if isinstance(chunk_data, tuple) and len(chunk_data) == 2:
                    chunk_type, chunk_text = chunk_data
                else:
                    chunk_type, chunk_text = "content", str(chunk_data)

                if chunk_text:
                    chunk_count += 1
                    total_bytes += len(chunk_text)

                    if chunk_type == "thinking":
                        thinking_buffer += chunk_text
                        meta_data = {"thinking": chunk_text, "model": model_name}
                        yield f"event: meta\ndata: {json.dumps(meta_data)}\n\n"
                    else:
                        content_buffer += chunk_text
                        yield format_content_chunk(chunk_text)

            total_latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "STREAM_STREAMING_COMPLETE",
                request_id=stream_request_id,
                total_chunks=chunk_count,
                total_bytes=total_bytes,
                total_latency_ms=total_latency_ms,
            )

            # Store assistant response in memory
            if memory_enabled and content_buffer and request.doctor_id:
                try:
                    mem = get_memory_manager(request.doctor_id)
                    if mem:
                        mem.store_interaction(
                            session_id=request.session_id or "unknown",
                            role="assistant",
                            content=content_buffer,
                            persona=request.persona,
                            model=model_name,
                        )
                except Exception as store_err:
                    logger.error("STREAM_ASSISTANT_STORE_FAILED", error=str(store_err))

            yield f"data: {json.dumps({'done': True, 'persona': request.persona, 'model': model_name})}\n\n"

        except Exception as e:
            error_latency_ms = int((time.time() - start_time) * 1000)
            sanitized_error = sanitize_error_message(str(e))

            logger.error(
                "STREAM_FAILED",
                request_id=stream_request_id,
                error=sanitized_error,
                error_type=type(e).__name__,
                latency_ms=error_latency_ms,
                exc_info=True,
            )
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )


@router.post("/chat/debug")
async def internal_llm_chat_debug(
    request: ChatRequest,
    policy_loader: PolicyLoaderDep,
) -> dict:
    """INTERNAL: Debug chat flow. Returns response vs thinking.

    Builds same prompt and calls llm_generate like main endpoint,
    but responds with minimal fields for inspection.

    Args:
        request: Chat request
        policy_loader: PolicyLoader singleton (FastAPI Depends injection)
    """
    from backend.providers import llm_generate

    try:
        try:
            persona_config = persona_mgr.get_persona(request.persona)
        except Exception:

            class _Cfg:
                temperature = 0.7
                max_tokens = 512

            persona_config = _Cfg()

        start_time = time.time()

        prompt = persona_mgr.build_system_prompt(request.persona, request.context)
        if request.context:
            prompt += f"\n\nContext:\n{json.dumps(request.context, indent=2)}"
        prompt += f"\n\nUser: {request.message}\n\nAssistant:"

        model_override = None
        if isinstance(request.context, dict):
            m = request.context.get("model")
            if isinstance(m, str) and m.strip():
                model_override = m.strip()

        llm_response = llm_generate(
            prompt,
            provider=request.provider,
            temperature=persona_config.temperature,
            max_tokens=persona_config.max_tokens,
            model=model_override if model_override else None,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        thinking = None
        meta = getattr(llm_response, "metadata", None)
        if isinstance(meta, dict):
            t = meta.get("thinking")
            if isinstance(t, str) and t.strip():
                thinking = t.strip()

        return {
            "model": getattr(llm_response, "model", "unknown"),
            "provider": request.provider or policy_loader.get_primary_provider(),
            "latency_ms": latency_ms,
            "response": llm_response.content.strip(),
            "thinking": thinking,
            "metadata_keys": list((meta or {}).keys()),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM chat debug failed: {e!s}",
        ) from e
