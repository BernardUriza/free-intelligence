"""
Free-Intelligence Assistant Workflow - AURITY

OpenAI-compatible chat completion endpoints for Free-Intelligence AI personas.

Architecture:
  PUBLIC (this file) -> InternalLLMClient -> /internal/llm/* -> PersonaManager -> llm_generate

Endpoints:
- POST /workflows/aurity/assistant/introduction - Onboarding presentation
- POST /workflows/aurity/assistant/chat - OpenAI-style chat completions with AURITY extensions
- POST /workflows/aurity/assistant/chat/stream - OpenAI-style streaming chat completions

OpenAI Compatibility:
- Messages array with roles: system, user, assistant
- Standard parameters: temperature, max_tokens, top_p, etc.
- Response format: choices array with message objects
- Token usage statistics
- AURITY extensions: persona, emotional_analysis, behavior_metrics

Modules:
- assistant_schemas.py - Pydantic request/response models (OpenAI-compatible)
- emotional_analysis.py - Hybrid LLM + heuristic emotional detection

Author: Bernard Uriza Orozco
Created: 2025-11-18
Refactored: 2025-12-07 (OpenAI conventions)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import ulid
import uuid
import uuid as _uuid
from collections.abc import AsyncGenerator
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.clients import get_llm_client
from backend.logger import get_logger
from backend.observability import chat_events
from backend.observability.logging import CTX_REQUEST_ID
from backend.services.trace_store import get_trace_store
from backend.utils.redactor import redact_and_hash_once

# Import schemas from dedicated module
from .assistant_schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
    ChatCompletionUsage,
    IntroductionRequest,
    IntroductionResponse,
    Message,
)

# Import emotional analysis from dedicated module
from .emotional_analysis import analyze_emotional_state

logger = get_logger(__name__)
trace_store = get_trace_store()


def _make_log_entry(level: str, **kwargs):
    # ensure required keys exist with defaults
    base = {
        "ts": int(time.time()),
        "level": level,
        "request_id": kwargs.get("request_id"),
        "trace_id": kwargs.get("trace_id"),
        "user_id": kwargs.get("user_id"),
        "org_id": kwargs.get("org_id"),
        "persona_id": kwargs.get("persona_id"),
        "response_mode": kwargs.get("response_mode"),
        "model": kwargs.get("model"),
        "provider": kwargs.get("provider"),
        "prompt_chars": kwargs.get("prompt_chars", 0),
        "rag_chars": kwargs.get("rag_chars", 0),
        "token_in": kwargs.get("token_in", 0),
        "token_out": kwargs.get("token_out", 0),
        "latency_ms": kwargs.get("latency_ms", 0),
        "status": kwargs.get("status", "ok"),
    }
    base.update({k: v for k, v in kwargs.items() if k not in base})
    return base


router = APIRouter()


# ============================================================================
# Introduction Endpoint
# ============================================================================


@router.post("/assistant/introduction", response_model=IntroductionResponse)
async def get_introduction(request: IntroductionRequest) -> IntroductionResponse:
    """Get Free-Intelligence's introduction for onboarding.

    Free-Intelligence presents herself with her characteristic personality:
    - Obsessive with clinical details
    - Sharp empathy (direct, no marketing)
    - Focused on data sovereignty

    This endpoint is designed for the onboarding flow to introduce
    the AI resident that will accompany the physician throughout
    the clinical workflow lifecycle.

    Args:
        request: Optional physician/clinic context for personalization

    Returns:
        IntroductionResponse with Free-Intelligence's message

    Raises:
        500: If internal LLM call fails
    """
    try:
        logger.info(
            "ASSISTANT_INTRODUCTION_START",
            has_physician_name=request.physician_name is not None,
            has_clinic_name=request.clinic_name is not None,
        )

        # Build context for persona
        context = {}
        if request.physician_name:
            context["physician_name"] = request.physician_name
        if request.clinic_name:
            context["clinic_name"] = request.clinic_name

        # Build message for Free-Intelligence
        message = _build_introduction_message(request)

        # Extract doctor_id from context (Auth0 user.sub) if available
        doctor_id = context.get("doctor_id") if context else None

        # Call internal LLM endpoint via HTTP client
        llm_client = get_llm_client()

        result = await llm_client.chat(
            persona="onboarding_guide",
            message=message,
            context=context if context else None,
            session_id=None,  # No session context for onboarding
            doctor_id=doctor_id,  # Pass doctor_id for memory
            use_memory=doctor_id is not None,  # Enable memory if doctor_id present
        )

        logger.info(
            "ASSISTANT_INTRODUCTION_SUCCESS",
            tokens=result.get("tokens_used", 0),
            latency=result.get("latency_ms", 0),
            response_length=len(result.get("response", "")),
        )

        return IntroductionResponse(
            message=result["response"],
            persona=result["persona"],
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0),
        )

    except Exception as e:
        logger.error(
            "ASSISTANT_INTRODUCTION_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Free-Intelligence introduction: {e!s}",
        ) from e


def _build_introduction_message(request: IntroductionRequest) -> str:
    """Build the introduction prompt based on available context."""
    if request.physician_name and request.clinic_name:
        return (
            f"Present yourself to Dr. {request.physician_name} "
            f"from {request.clinic_name}. "
            "Explain who you are, where you reside (locally in their NAS), "
            "and how you'll help them with clinical documentation while "
            "ensuring their data sovereignty."
        )
    elif request.physician_name:
        return (
            f"Present yourself to Dr. {request.physician_name}. "
            "Explain who you are, where you reside (locally in their infrastructure), "
            "and how you'll help them with clinical workflows."
        )
    else:
        return (
            "Present yourself to a new physician who is onboarding. "
            "Explain who you are, where you reside (locally, not in the cloud), "
            "and how you help with clinical documentation while respecting data sovereignty."
        )


# ============================================================================
# Chat Endpoint
# ============================================================================


@router.post("/assistant/chat", response_model=ChatCompletionResponse)
async def chat_with_assistant(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """OpenAI-style chat completion endpoint for Free-Intelligence conversations.

    Follows OpenAI Chat Completions API conventions with AURITY-specific extensions.

    Supports:
    - Multi-turn conversations with message history
    - System messages for persona configuration
    - User and assistant message roles
    - AURITY-specific persona selection
    - Emotional analysis with behavior metrics
    - Memory persistence with doctor_id

    Args:
        request: OpenAI-style chat completion request with AURITY extensions

    Returns:
        OpenAI-style chat completion response with AURITY extensions

    Raises:
        400: Invalid request format
        500: Internal LLM processing failed
    """
    import time
    import uuid

    try:
        # Create and set request_id in contextvars for observability
        request_id = str(_uuid.uuid4())
        CTX_REQUEST_ID.set(request_id)

        # Extract the last user message for processing
        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last message must be from user",
            )

        # Extract system message if present
        system_message = None
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
                break

        # Extract doctor_id from user field
        # If not provided, use "anonymous" for public storage (still persists, but shared)
        is_anonymous = not request.user
        doctor_id = request.user if request.user else "anonymous"

        if is_anonymous:
            logger.warning(
                "ASSISTANT_CHAT_ANONYMOUS",
                message="No doctor_id provided, using anonymous storage. "
                "Messages will be saved but not tied to a specific user. "
                "Frontend should pass 'user' field with Auth0 user.sub for persistent history.",
                session_id=request.session_id,
            )

        # Build context for internal LLM client
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
            memory_enabled=True,  # Always enabled now (anonymous or authenticated)
        )

        llm_client = get_llm_client()

        # Log chat request event
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

        # Run emotional analysis if metrics provided
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

        # RAG: Search for relevant documents
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

        # Convert OpenAI messages to internal format
        # For now, we'll use the last user message and system context
        # Memory is ALWAYS enabled - uses "anonymous" storage if no doctor_id
        result = await llm_client.chat(
            persona=request.persona,
            message=last_message.content,
            context=context,
            session_id=request.session_id,
            doctor_id=doctor_id,
            use_memory=True,  # Always persist (anonymous or authenticated)
            request_id=request_id,
            caller="public",
        )

        # After LLM returns, log LLM_CALL
        usage = None
        try:
            usage = {
                "prompt_tokens": result.get("prompt_tokens", 0),
                "completion_tokens": result.get("completion_tokens", 0),
            }
        except Exception:
            usage = None
        chat_events.log_llm_call(chat_ctx, usage, llm_ms=result.get("latency_ms", 0))

        # Create OpenAI-style response
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created_timestamp = int(time.time())

        # Build assistant message
        assistant_message = Message(role="assistant", content=result["response"])

        choice = ChatCompletionChoice(index=0, message=assistant_message, finish_reason="stop")

        # Estimate token usage (simplified)
        prompt_tokens = len(last_message.content.split()) * 4  # Rough estimate
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

        # Build receptionist state if config provided
        receptionist_state = None
        if request.receptionist_config:
            # Basic receptionist state - in production this would be more sophisticated
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


# ============================================================================
# Diagnostic endpoints: dry-run and trace
# ============================================================================


@router.post("/assistant/chat/_dry-run")
async def assistant_chat_dry_run(
    request: ChatCompletionRequest,
    log_level: str = "DEBUG",
    trace_ttl_s: int = 600,
    enable_dry_run: bool = True,
    redact_rules: list[str] | None = None,
) -> dict:
    """Dry-run diagnostic endpoint.

    Resolves persona, response_mode (from messages/system), builds system prompt markers,
    and returns metadata without including user message text (only hash and length).
    """

    # Generate request id
    request_id = str(_uuid.uuid4())

    # Extract last user message length/hash only
    last_message = request.messages[-1]
    user_len = len(last_message.content) if last_message and last_message.content else 0
    user_hash = hashlib.sha256((last_message.content or "").encode()).hexdigest()[:8]

    # Resolve persona via PersonaManager
    try:
        from backend.services.llm.persona.manager import PersonaManager

        pm = PersonaManager()
        persona_cfg = pm.get_effective_persona(request.persona, user_id=request.user)
    except Exception as e:
        logger.warning("DRY_RUN_PERSONA_NOT_FOUND", persona=request.persona, error=str(e))
        raise HTTPException(status_code=400, detail="PersonaNotFound")

    # Build system prompt but redact rag_context
    context = {"response_mode": None, "rag_context": None}
    # Try to find response_mode in system messages
    response_mode = None
    for msg in request.messages:
        if msg.role == "system" and "MODE:" in msg.content:
            if "CONCISE" in msg.content.upper():
                response_mode = "concise"
            elif "EXPLANATORY" in msg.content.upper():
                response_mode = "explanatory"

    # Build a safe truncated system prompt
    full_prompt = pm.build_system_prompt(request.persona, context)
    max_rag_chars = 2048
    truncated_prompt = full_prompt[:max_rag_chars]
    redacted_prompt, meta = redact_and_hash_once(truncated_prompt, redact_rules)

    # Save trace entry
    trace_id = ulid.new().str
    trace = {
        "request_id": request_id,
        "trace_id": trace_id,
        "persona_id": persona_cfg.persona,
        "response_mode": response_mode or "explanatory",
        "model": request.model,
        "prompt_chars": len(truncated_prompt),
        "rag_chars": meta.get("length", 0),
        "dry_run": True,
        "ts": int(time.time()),
    }
    trace_store.put(request_id, trace)

    # Return safe metadata
    return {
        "request_id": request_id,
        "persona_id": persona_cfg.persona,
        "response_mode_resolved": response_mode or "explanatory",
        "system_markers": {
            "concise": "<!--MODE:CONCISE-->"
            if (response_mode or "").lower() == "concise"
            else None,
            "explanatory": "<!--MODE:EXPLANATORY-->"
            if (response_mode or "").lower() == "explanatory"
            else "<!--MODE:EXPLANATORY-->",
            "rag_begin": "<!--RAG:BEGIN-->",
            "rag_end": "<!--RAG:END-->",
        },
        "rag_bytes": meta.get("length", 0),
        "model": request.model,
        "timeouts": {"llm_timeout_s": 30},
        "user_message": {"hash8": user_hash, "length": user_len},
    }


@router.get("/assistant/chat/_trace/{request_id}")
async def assistant_chat_trace(request_id: str):
    trace = trace_store.get(request_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found or expired")
    return trace


# ============================================================================
# Streaming Chat Endpoint
# ============================================================================


@router.post("/assistant/chat/stream")
async def stream_chat_with_assistant(request: ChatCompletionRequest) -> StreamingResponse:
    """OpenAI-style streaming chat completion endpoint.

    Returns Server-Sent Events (SSE) stream following OpenAI streaming format.
    Each chunk contains partial response data that can be concatenated.

    Args:
        request: Chat completion request with stream=True

    Returns:
        StreamingResponse with SSE chunks

    Raises:
        400: Invalid request or streaming not supported
        500: Internal processing failed
    """
    if not request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /assistant/chat for non-streaming requests. Set stream=true for this endpoint.",
        )

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate SSE stream chunks."""
        try:
            # Validate request
            if not request.messages:
                yield f"data: {json.dumps({'error': 'At least one message is required'})}\n\n"
                return

            last_message = request.messages[-1]
            if last_message.role != "user":
                yield f"data: {json.dumps({'error': 'Last message must be from user'})}\n\n"
                return

            # Extract system message
            system_message = None
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                    break

            doctor_id = request.user if request.user else None

            # Build context
            context = {
                "persona": request.persona,
                "system_message": system_message,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stop": request.stop,
            }

            if doctor_id:
                context["doctor_id"] = doctor_id

            completion_id = f"chatcmpl-{uuid.uuid4().hex}"
            created_timestamp = int(time.time())

            llm_client = get_llm_client()

            # Set request id for stream
            request_id = str(_uuid.uuid4())
            CTX_REQUEST_ID.set(request_id)

            # Send initial chunk with role
            initial_chunk = ChatCompletionStreamResponse(
                id=completion_id,
                created=created_timestamp,
                model=request.model,
                choices=[{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            )
            yield f"data: {initial_chunk.model_dump_json()}\n\n"

            # For now, simulate streaming by sending the full response in chunks
            # In a real implementation, you'd need streaming support from the LLM provider
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

            # If backend provided reasoning, emit it first via meta
            thinking = result.get("thinking")
            if thinking:
                meta_event = {"thinking": thinking}
                yield f"event: meta\ndata: {json.dumps(meta_event)}\n\n"

            # Split response into chunks for streaming simulation
            response_text = result["response"]
            chunk_size = 10  # Characters per chunk

            for i in range(0, len(response_text), chunk_size):
                chunk_text = response_text[i : i + chunk_size]

                stream_chunk = ChatCompletionStreamResponse(
                    id=completion_id,
                    created=created_timestamp,
                    model=request.model,
                    choices=[{"index": 0, "delta": {"content": chunk_text}, "finish_reason": None}],
                )
                yield f"data: {stream_chunk.model_dump_json()}\n\n"

                # Small delay to simulate real streaming
                await asyncio.sleep(0.05)

            # Send final chunk with finish_reason
            final_chunk = ChatCompletionStreamResponse(
                id=completion_id,
                created=created_timestamp,
                model=request.model,
                choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"

            # Send [DONE] marker
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

            # Send [DONE] marker even on error
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Content-Type": "text/event-stream; charset=utf-8"},
    )


# ============================================================================
# RAG Helper Functions
# ============================================================================


async def _get_rag_context(
    query: str,
    persona: str,
    top_k: int = 5,
    min_similarity: float = 0.35,
) -> str | None:
    """Search documents and build RAG context for the LLM.

    Args:
        query: User's question/message
        persona: Current persona (for filtering documents)
        top_k: Number of chunks to retrieve
        min_similarity: Minimum similarity threshold

    Returns:
        Formatted context string or None if no relevant documents
    """
    try:
        from backend.api.public.workflows.documents import _get_embedding
        from backend.storage.document_repository import (
            get_document,
            search_documents_by_embedding,
        )

        # Generate embedding for query
        query_embedding = await _get_embedding(query)

        # Search documents
        results = search_documents_by_embedding(
            query_embedding=query_embedding,
            top_k=top_k,
            persona_filter=persona,
        )

        # Filter by minimum similarity
        relevant_results = [r for r in results if r[2] >= min_similarity]

        if not relevant_results:
            return None

        # Build context string with clear structure
        context_parts = []
        for idx, (doc_id, _chunk_id, similarity, chunk_text) in enumerate(relevant_results, 1):
            doc = get_document(doc_id)
            if doc:
                context_parts.append(
                    f"### Fragmento {idx} (Relevancia: {similarity:.0%})\n"
                    f"**Fuente:** {doc.metadata.title}\n"
                    f"**Contenido:**\n{chunk_text}"
                )

        if not context_parts:
            return None

        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.warning("RAG_CONTEXT_FAILED", error=str(e))
        return None
