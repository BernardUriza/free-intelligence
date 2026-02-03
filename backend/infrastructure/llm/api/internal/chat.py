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
Created: 2026-02-03 (Infrastructure Migration from routers/llm/internal/llm/chat.py)
"""

import contextlib
import hashlib
import json
import time
import uuid as _uuid
from datetime import UTC, datetime
from typing import Annotated

import ulid
from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.audit.services.audit_service import AuditService
from backend.api.routers.assistant.public.assistant_websocket import broadcast_new_message
from backend.config import CORPUS_PATH
from backend.infrastructure.common.policy_provider import get_policy_loader_dep
from backend.infrastructure.observability.hooks import log_llm_call, log_llm_error
from backend.policy.interfaces.ipolicy_loader import IPolicyLoader
from backend.providers import llm_generate, sanitize_error_message
from backend.repositories.audit_repository import AuditRepository
from backend.schemas.llm.audit_policy import require_audit_log
from backend.services.llm.dependencies import get_persona_manager
from backend.services.llm.services.conversation_memory import get_memory_manager
from backend.utils.common.logging.logger import get_logger

from .schemas import ChatRequest, ChatResponse

router = APIRouter()
logger = get_logger(__name__)
persona_mgr = get_persona_manager()
trace_store = None  # TraceStore planned for Phase 3

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

    trace_id = ulid.new().str

    trace_entry = {
        "request_id": incoming_request_id,
        "trace_id": trace_id,
        "persona": request.persona,
        "ts": int(time.time()),
        "events": [],
    }
    if trace_store is not None:
        trace_store.put(incoming_request_id, trace_entry)

    logger.info(
        "CHAT_REQUEST",
        request_id=incoming_request_id,
        trace_id=trace_id,
        persona=request.persona,
        message_len=len(request.message),
    )

    try:
        # Auto-enable memory for Azure GPT-4 (infinite conversation policy)
        primary_provider = policy_loader.get_primary_provider()
        auto_memory_enabled = False
        effective_doctor_id = request.doctor_id

        if primary_provider == "azure":
            auto_memory_enabled = True
            if not effective_doctor_id:
                effective_doctor_id = "system"
                logger.info(
                    "MEMORY_AUTO_ENABLED_AZURE",
                    provider=primary_provider,
                    doctor_id=effective_doctor_id,
                    message="Conversational memory enabled automatically for Azure GPT-4",
                )

        if request.use_memory and not request.doctor_id and not auto_memory_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="doctor_id is required when use_memory=True",
            )

        # Intelligent persona routing (Two-Model Strategy)
        effective_persona = request.persona

        if request.persona == "auto" or not request.persona:
            effective_persona = persona_mgr.route_persona(request.message)
            logger.info(
                "PERSONA_AUTO_ROUTED",
                user_message_preview=request.message[:50],
                routed_to=effective_persona,
                cost_pattern="Two-Model Strategy (Haiku routing + GPT-4 response)",
            )

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

        # Build prompt with conversation memory if enabled
        memory_enabled = request.use_memory or auto_memory_enabled

        memory = None
        if memory_enabled and effective_doctor_id:
            memory = get_memory_manager(effective_doctor_id)
            if memory is None:
                memory_enabled = False

        if memory_enabled and memory is not None:
            user_timestamp = datetime.now(UTC).isoformat()
            memory.store_interaction(
                session_id=request.session_id or "unknown",
                role="user",
                content=request.message,
                persona=request.persona,
            )

            await broadcast_new_message(
                doctor_id=effective_doctor_id,
                role="user",
                content=request.message,
                timestamp=user_timestamp,
                persona=request.persona,
            )

            context = memory.get_context(
                current_message=request.message,
                session_id=request.session_id,
            )

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
            prompt = persona_mgr.build_system_prompt(effective_persona, request.context)

            if request.context:
                prompt += f"\n\nContext:\n{json.dumps(request.context, indent=2)}"

            prompt += f"\n\nUser: {request.message}\n\nAssistant:"

        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        logger.info(
            "INTERNAL_LLM_CHAT_START",
            persona=request.persona,
            message_length=len(request.message),
            context_keys=list(request.context.keys()) if request.context else [],
            prompt_hash=prompt_hash[:12],
            prompt_length=len(prompt),
            session_id=request.session_id,
        )

        # Honor model override from context
        model_override = None
        enable_thinking = False
        try:
            if isinstance(request.context, dict):
                m = request.context.get("model")
                if isinstance(m, str) and m.strip():
                    model_override = m.strip()
                if "enable_thinking" in request.context:
                    enable_thinking = bool(request.context.get("enable_thinking", True))
        except Exception as e:
            logger.debug("MODEL_OVERRIDE_PARSE_FAILED", error=str(e))
            model_override = None

        logger.info(
            "INTERNAL_LLM_MODEL_SELECTION",
            requested_model=model_override,
            provider=request.provider or policy_loader.get_primary_provider(),
            enable_thinking=enable_thinking,
        )

        llm_response = llm_generate(
            prompt,
            provider=request.provider,
            temperature=persona_config.temperature,
            max_tokens=persona_config.max_tokens,
            model=model_override if model_override else None,
            enable_thinking=enable_thinking,
        )

        with contextlib.suppress(Exception):
            logger.info(
                "INTERNAL_LLM_MODEL_EFFECTIVE",
                effective_model=getattr(llm_response, "model", "unknown"),
                provider=request.provider or policy_loader.get_primary_provider(),
            )

        # Record LLM_CALL in trace timeline
        try:
            llm_event = {
                "event": "LLM_CALL",
                "ts": int(time.time()),
                "provider": policy_loader.get_primary_provider(),
                "model": getattr(llm_response, "model", "unknown"),
                "tokens_used": getattr(llm_response, "usage", {}).total_tokens
                if hasattr(getattr(llm_response, "usage", None), "total_tokens")
                else 0,
                "latency_ms": int((time.time() - start_time) * 1000),
            }
            te = trace_store.get(incoming_request_id) or trace_entry
            te_events = te.get("events", [])
            te_events.append(llm_event)
            te["events"] = te_events
            trace_store.put(incoming_request_id, te)
        except Exception as e:
            logger.debug("TRACE_LLM_CALL_FAILED", error=str(e))

        response_text = llm_response.content.strip()
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()

        latency_ms = int((time.time() - start_time) * 1000)

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
                model=model_name,
            )

            await broadcast_new_message(
                doctor_id=effective_doctor_id,
                role="assistant",
                content=response_text,
                timestamp=assistant_timestamp,
                persona=request.persona,
                model=model_name,
            )

        # Cost estimate
        cost_usd = (tokens_used / 1000) * 0.045 if tokens_used > 0 else 0.0

        # Log to audit trail
        try:
            audit_service.log_action(
                action="llm_call",
                user_id=effective_doctor_id or "anonymous",
                resource=f"persona:{effective_persona}",
                result="success",
                details={
                    "persona": effective_persona,
                    "latency_ms": latency_ms,
                    "tokens_used": tokens_used,
                    "cost_usd": round(cost_usd, 6),
                    "model": model_name,
                    "session_id": request.session_id,
                    "memory_enabled": memory_enabled,
                    "provider": primary_provider,
                },
            )
        except Exception as audit_error:
            logger.warning(
                "AUDIT_LOG_FAILED",
                error=str(audit_error),
                persona=effective_persona,
            )

        # Append CHAT_RESPONSE event to trace
        try:
            resp_event = {
                "event": "CHAT_RESPONSE",
                "ts": int(time.time()),
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "model": model_name,
            }
            te = trace_store.get(incoming_request_id) or trace_entry
            te_events = te.get("events", [])
            te_events.append(resp_event)
            te["events"] = te_events
            trace_store.put(incoming_request_id, te)
        except Exception:
            pass

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
            cost_usd=round(cost_usd, 6),
        )

        # Log to SQLite observability database
        log_llm_call(
            model=model_name,
            provider=primary_provider,
            latency_ms=latency_ms,
            prompt_tokens=tokens_used,
            completion_tokens=0,
            status="success",
            prompt_preview=prompt[:500] if prompt else "",
            response_preview=response_text[:500] if response_text else "",
            client_id=effective_doctor_id,
            session_id=request.session_id,
            persona=effective_persona,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            metadata={
                "memory_enabled": memory_enabled,
                "cost_usd": round(cost_usd, 6),
            },
        )

        # Optional reasoning from provider metadata
        thinking = None
        try:
            meta = getattr(llm_response, "metadata", None)
            if isinstance(meta, dict):
                t = meta.get("thinking")
                if isinstance(t, str) and t.strip():
                    thinking = t.strip()
        except Exception:
            thinking = None

        return ChatResponse(
            response=response_text,
            thinking=thinking,
            persona=effective_persona,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model=model_name,
            voice=persona_config.voice,
            prompt_hash=prompt_hash[:12],
            response_hash=response_hash[:12],
            logged_at=datetime.now(UTC).isoformat(),
        )

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

        log_llm_error(
            model="unknown",
            provider=policy_loader.get_primary_provider(),
            latency_ms=latency_ms,
            error_message=str(e),
            error_type=type(e).__name__,
            prompt_preview=prompt[:500] if prompt else "",
            client_id=request.doctor_id,
            session_id=request.session_id,
            persona=request.persona,
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
    import json

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
                doctor_id_present=bool(request.doctor_id),
                use_memory=request.use_memory,
            )

            memory_enabled = request.use_memory and request.doctor_id

            memory = None
            if memory_enabled:
                memory = get_memory_manager(request.doctor_id)
                if memory is None:
                    memory_enabled = False
                    logger.info(
                        "STREAM_MEMORY_DISABLED_NO_EMBEDDINGS",
                        request_id=stream_request_id,
                        doctor_id=request.doctor_id,
                    )

            if memory_enabled and memory is not None:
                logger.info(
                    "STREAM_MEMORY_ENABLED",
                    request_id=stream_request_id,
                    doctor_id=request.doctor_id,
                    session_id=request.session_id,
                )

                memory.store_interaction(
                    session_id=request.session_id or "unknown",
                    role="user",
                    content=request.message,
                    persona=request.persona,
                )
                logger.info(
                    "[STREAM] USER_MESSAGE_STORED",
                    request_id=stream_request_id,
                    doctor_id=request.doctor_id,
                )
                system_prompt = persona_mgr.build_system_prompt(request.persona, request.context)
                memory_context = memory.get_context(request.message, request.session_id)

                logger.info(
                    "[STREAM] MEMORY_CONTEXT_LOADED",
                    request_id=stream_request_id,
                    recent_interactions=len(memory_context.recent) if memory_context else 0,
                    relevant_interactions=len(memory_context.relevant) if memory_context else 0,
                )

                prompt = memory.build_prompt(
                    context=memory_context,
                    system_prompt=system_prompt,
                    current_message=request.message,
                )

                logger.debug(
                    "[STREAM] PROMPT_BUILT_WITH_MEMORY",
                    request_id=stream_request_id,
                    prompt_length=len(prompt),
                )
            else:
                logger.debug(
                    "[STREAM] BUILDING_PROMPT_WITHOUT_MEMORY",
                    request_id=stream_request_id,
                )
                prompt = persona_mgr.build_system_prompt(request.persona, request.context)
                if request.context:
                    prompt += f"\n\nContext:\n{json.dumps(request.context, indent=2)}"
                prompt += f"\n\nUser: {request.message}\n\nAssistant:"

                logger.debug(
                    "[STREAM] PROMPT_BUILT",
                    request_id=stream_request_id,
                    prompt_length=len(prompt),
                )

            provider_name = request.provider or policy_loader.get_primary_provider()

            logger.info(
                "[STREAM] PROVIDER_SELECTED",
                request_id=stream_request_id,
                provider=provider_name,
                is_override=bool(request.provider),
            )

            provider_config = policy_loader.get_provider_config(provider_name)
            if provider_config is None:
                provider_config = {}

            logger.debug(
                "[STREAM] PROVIDER_CONFIG_LOADED",
                request_id=stream_request_id,
                provider=provider_name,
                config_keys=list(provider_config.keys()),
            )

            from backend.providers import get_provider

            llm_provider = get_provider(provider_name, provider_config)

            logger.info(
                "[STREAM] PROVIDER_INSTANCE_CREATED",
                request_id=stream_request_id,
                provider=provider_name,
                provider_type=type(llm_provider).__name__,
            )

            if not hasattr(llm_provider, "generate_stream"):
                logger.warning(
                    "[STREAM] FALLBACK_NO_STREAM_METHOD",
                    request_id=stream_request_id,
                    provider=provider_name,
                    message="Provider doesn't support streaming, falling back to buffered response",
                )
                response = llm_provider.generate(
                    prompt,
                    model=request.context.get("model") if request.context else None,
                    temperature=request.context.get("temperature", 0.7) if request.context else 0.7,
                    max_tokens=request.context.get("max_tokens", 512) if request.context else 512,
                )
                logger.info(
                    "[STREAM] FALLBACK_RESPONSE_BUFFERED",
                    request_id=stream_request_id,
                    response_length=len(response.content),
                    model=response.model,
                    latency_ms=int((time.time() - start_time) * 1000),
                )
                yield f"data: {json.dumps({'content': response.content})}\n\n"
                return

            chunk_count = 0
            total_bytes = 0
            last_chunk_time = start_time

            model_name = (
                request.context.get("model") if request.context else None
            ) or provider_name

            logger.info(
                "[STREAM] STREAMING_START",
                request_id=stream_request_id,
                provider=provider_name,
                persona=request.persona,
                message_length=len(request.message),
                prompt_length=len(prompt),
                model_override=request.context.get("model") if request.context else None,
            )

            gen = await asyncio.to_thread(
                lambda: llm_provider.generate_stream(
                    prompt,
                    model=request.context.get("model") if request.context else None,
                    temperature=request.context.get("temperature", 0.7) if request.context else 0.7,
                    max_tokens=request.context.get("max_tokens", 512) if request.context else 512,
                    enable_thinking=request.context.get("enable_thinking", False)
                    if request.context
                    else False,
                )
            )

            thinking_buffer = ""
            content_buffer = ""
            thinking_emitted = False

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
                    chunk_size = len(chunk_text)
                    total_bytes += chunk_size
                    now = time.time()
                    time_since_last = (now - last_chunk_time) * 1000

                    if chunk_count % 5 == 1 or chunk_count <= 3:
                        logger.debug(
                            "[STREAM] CHUNK_YIELDED",
                            request_id=stream_request_id,
                            chunk_num=chunk_count,
                            chunk_type=chunk_type,
                            chunk_size=chunk_size,
                            total_bytes=total_bytes,
                            time_since_last_chunk_ms=round(time_since_last, 1),
                            preview=chunk_text[:30] + ("..." if len(chunk_text) > 30 else ""),
                        )

                    if chunk_type == "thinking":
                        thinking_buffer += chunk_text
                        meta_data = {"thinking": chunk_text, "model": model_name}
                        yield f"event: meta\ndata: {json.dumps(meta_data)}\n\n"
                        if not thinking_emitted:
                            thinking_emitted = True
                            logger.info(
                                "[STREAM] THINKING_STARTED",
                                request_id=stream_request_id,
                                model=model_name,
                            )
                    else:
                        content_buffer += chunk_text
                        yield format_content_chunk(chunk_text)

                    last_chunk_time = now

            if thinking_buffer:
                logger.info(
                    "[STREAM] THINKING_COMPLETE",
                    request_id=stream_request_id,
                    total_thinking_length=len(thinking_buffer),
                    model=model_name,
                )

            total_latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "[STREAM] STREAMING_COMPLETE",
                request_id=stream_request_id,
                provider=provider_name,
                persona=request.persona,
                total_chunks=chunk_count,
                total_bytes=total_bytes,
                total_latency_ms=total_latency_ms,
                avg_chunk_size=round(total_bytes / chunk_count, 1) if chunk_count > 0 else 0,
            )

            if memory_enabled and content_buffer:
                try:
                    memory = get_memory_manager(request.doctor_id)
                    memory.store_interaction(
                        session_id=request.session_id or "unknown",
                        role="assistant",
                        content=content_buffer,
                        persona=request.persona,
                        model=model_name,
                    )
                    logger.info(
                        "STREAM_ASSISTANT_MESSAGE_STORED",
                        request_id=stream_request_id,
                        doctor_id=request.doctor_id,
                        content_length=len(content_buffer),
                        model=model_name,
                    )
                except Exception as store_err:
                    logger.error(
                        "STREAM_ASSISTANT_STORE_FAILED",
                        request_id=stream_request_id,
                        error=str(store_err),
                    )

            yield f"data: {json.dumps({'done': True, 'persona': request.persona, 'model': model_name})}\n\n"

        except Exception as e:
            error_latency_ms = int((time.time() - start_time) * 1000)
            sanitized_error = sanitize_error_message(str(e))

            logger.error(
                "STREAM_FAILED",
                request_id=stream_request_id,
                error=sanitized_error,
                error_type=type(e).__name__,
                persona=request.persona,
                message_length=len(request.message),
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
    but responds with minimal fields for inspection: response and metadata.thinking.

    Args:
        request: Chat request
        policy_loader: PolicyLoader singleton (FastAPI Depends injection)
    """
    try:
        try:
            persona_config = persona_mgr.get_persona_config(request.persona)
        except Exception:

            class _Cfg:
                temperature = 0.7
                max_tokens = 512

            persona_config = _Cfg()
        effective_persona = request.persona

        start_time = time.time()

        prompt = persona_mgr.build_system_prompt(effective_persona, request.context)
        if request.context:
            prompt += f"\n\nContext:\n{json.dumps(request.context, indent=2)}"
        prompt += f"\n\nUser: {request.message}\n\nAssistant:"

        model_override = None
        try:
            if isinstance(request.context, dict):
                m = request.context.get("model")
                if isinstance(m, str) and m.strip():
                    model_override = m.strip()
        except Exception:
            model_override = None

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
        )
