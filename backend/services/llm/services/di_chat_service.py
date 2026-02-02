"""Chat Service - Dependency Injection version.

REFACTORED: Uses constructor injection instead of direct imports.
Extracted all business logic from chat.py router (935 lines → thin pattern).

Dependencies eliminated from direct imports:
- PersonaManager → Constructor injected (interface)
- AuditService → Constructor injected
- PolicyLoader → Constructor injected
- ConversationMemory → Via get_memory_manager (factory)
- EventBus → Stub (Phase 3)
- TraceStore → Stub (Phase 3)

Author: Claude Code (refactored from chat.py)
Created: 2026-01-28
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid as _uuid
from datetime import UTC, datetime
from typing import Any

import ulid
from backend.api.audit.services.audit_service import AuditService
from backend.infrastructure.observability.hooks import log_llm_call, log_llm_error
from backend.policy.policy_loader import PolicyLoader
from backend.providers.llm import llm_generate, sanitize_error_message
from backend.api.routers.assistant.public.assistant_websocket import broadcast_new_message
from backend.services.llm.services.conversation_memory import get_memory_manager
from backend.services.llm.services.persona_manager import PersonaManager
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger

# Stub trace store (Phase 3 will implement real trace storage)
class StubTraceStore:
    """Stub trace store - to be replaced in Phase 3."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def get(self, request_id: str) -> dict | None:
        return self._store.get(request_id)

    def put(self, request_id: str, data: dict) -> None:
        self._store[request_id] = data


class ChatProcessingResult:
    """Result of chat processing."""

    def __init__(
        self,
        request_id: str,
        trace_id: str,
        persona: str,
        response_text: str,
        tokens_used: int,
        latency_ms: int,
        model_name: str,
        cost_usd: float,
        memory_enabled: bool,
        auto_memory_enabled: bool,
        provider: str,
        prompt_hash: str,
        response_hash: str,
        voice: str,  # Azure TTS voice for persona
        thinking: str | None = None,  # Optional reasoning from model
        logged_at: str | None = None,  # ISO8601 timestamp
    ):
        self.request_id = request_id
        self.trace_id = trace_id
        self.persona = persona
        self.response_text = response_text
        self.tokens_used = tokens_used
        self.latency_ms = latency_ms
        self.model_name = model_name
        self.cost_usd = cost_usd
        self.memory_enabled = memory_enabled
        self.auto_memory_enabled = auto_memory_enabled
        self.provider = provider
        self.prompt_hash = prompt_hash
        self.response_hash = response_hash
        self.voice = voice
        self.thinking = thinking
        self.logged_at = logged_at or datetime.now(UTC).isoformat()


class DIChatService:
    """Chat service with Dependency Injection.

    Replaces inline logic in chat.py router (935 lines).
    All dependencies are explicit and testable.

    Dependencies eliminated from direct imports:
    - PersonaManager (injected)
    - AuditService (injected)
    - PolicyLoader (injected)
    - Logger (injected, optional)
    """

    def __init__(
        self,
        persona_manager: PersonaManager,
        audit_service: AuditService,
        policy_loader: PolicyLoader,
        logger: ILogger | None = None,
    ):
        """Initialize chat service with dependencies.

        Args:
            persona_manager: Persona configuration manager
            audit_service: Audit logging service
            policy_loader: Policy configuration loader
            logger: Logger instance (defaults to module logger)
        """
        self.persona_mgr = persona_manager
        self.audit_service = audit_service
        self.policy_loader = policy_loader
        self.logger = logger or get_logger(__name__)
        self.trace_store = StubTraceStore()  # Stub for Phase 3

    async def process_chat(
        self,
        message: str,
        persona: str,
        doctor_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        provider: str | None = None,
        use_memory: bool = False,
        request_id: str | None = None,
    ) -> ChatProcessingResult:
        """Process chat message with LLM (ASYNC pattern).

        Business logic (orchestration):
        1. Auto-enable memory for Azure GPT-4
        2. Validate memory requirements
        3. Route persona intelligently (Two-Model Strategy)
        4. Build prompt with/without conversation memory
        5. Call LLM via provider
        6. Store response in memory if enabled
        7. Broadcast to WebSocket if enabled
        8. Calculate cost and log metrics

        Args:
            message: User message
            persona: Persona to use (or "auto" for routing)
            doctor_id: Doctor identifier (required for memory)
            session_id: Session identifier (optional)
            context: Additional context dict
            provider: LLM provider override (or None for policy default)
            use_memory: Enable conversation memory
            request_id: Optional request ID (generated if not provided)

        Returns:
            ChatProcessingResult with response and metadata

        Raises:
            ValueError: If memory enabled but doctor_id missing
            HTTPException: If persona invalid or LLM fails
        """
        start_time = time.time()
        prompt = ""  # Initialize for exception handling

        # Generate request/trace IDs
        if not request_id:
            request_id = str(_uuid.uuid4())

        trace_id = ulid.new().str

        # Initialize trace entry (stub for Phase 3)
        trace_entry = {
            "request_id": request_id,
            "trace_id": trace_id,
            "persona": persona,
            "ts": int(time.time()),
            "events": [],
        }
        self.trace_store.put(request_id, trace_entry)

        self.logger.info(
            "CHAT_REQUEST",
            request_id=request_id,
            trace_id=trace_id,
            persona=persona,
            message_len=len(message),
        )

        try:
            # Auto-enable memory for Azure GPT-4 (infinite conversation policy)
            primary_provider = self.policy_loader.get_primary_provider()
            auto_memory_enabled = False
            effective_doctor_id = doctor_id

            if primary_provider == "azure":
                # Azure GPT-4: Enable memory by default
                auto_memory_enabled = True

                # Use provided doctor_id or default to "system"
                if not effective_doctor_id:
                    effective_doctor_id = "system"
                    self.logger.info(
                        "MEMORY_AUTO_ENABLED_AZURE",
                        provider=primary_provider,
                        doctor_id=effective_doctor_id,
                        message="Conversational memory enabled automatically for Azure GPT-4",
                    )

            # Validate memory requirements (only if explicitly requested)
            if use_memory and not doctor_id and not auto_memory_enabled:
                raise ValueError("doctor_id is required when use_memory=True")

            # Intelligent persona routing (Two-Model Strategy)
            effective_persona = persona

            if persona == "auto" or not persona:
                # Use cheap routing to decide persona
                effective_persona = self.persona_mgr.route_persona(message)
                self.logger.info(
                    "PERSONA_AUTO_ROUTED",
                    user_message_preview=message[:50],
                    routed_to=effective_persona,
                    cost_pattern="Two-Model Strategy (Haiku routing + GPT-4 response)",
                )

            # Get persona configuration
            persona_config = self.persona_mgr.get_persona(effective_persona)

            # Build prompt with conversation memory if enabled (explicit or auto)
            memory_enabled = use_memory or auto_memory_enabled

            if memory_enabled and effective_doctor_id:
                # Get memory manager (None if embeddings unavailable in production)
                memory = get_memory_manager(effective_doctor_id)

                # Skip memory features if embeddings unavailable
                if memory is None:
                    memory_enabled = False

            if memory_enabled and effective_doctor_id:
                prompt, context_info = await self._build_prompt_with_memory(
                    message=message,
                    persona=effective_persona,
                    doctor_id=effective_doctor_id,
                    session_id=session_id,
                    context=context,
                )

                self.logger.info(
                    "INTERNAL_LLM_MEMORY_ENABLED",
                    doctor_id=effective_doctor_id,
                    session_id=session_id,
                    recent_count=context_info.get("recent_count", 0),
                    relevant_count=context_info.get("relevant_count", 0),
                    total_interactions=context_info.get("total_interactions", 0),
                    auto_enabled=auto_memory_enabled,
                )
            else:
                # Build prompt without memory (original behavior)
                prompt = self._build_prompt_without_memory(
                    message=message,
                    persona=effective_persona,
                    context=context,
                )

            # Hash prompt for audit (ultra observable)
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

            self.logger.info(
                "INTERNAL_LLM_CHAT_START",
                persona=persona,
                message_length=len(message),
                context_keys=list(context.keys()) if context else [],
                prompt_hash=prompt_hash[:12],  # First 12 chars for logs
                prompt_length=len(prompt),
                session_id=session_id,
            )

            # Call LLM via router - use request provider or default from policy
            # Honrar override de modelo si viene en el contexto
            model_override = None
            enable_thinking = True  # Default: enable thinking for Qwen3 models
            if context:
                model_override = context.get("model")
                enable_thinking = context.get("enable_thinking", True)

            self.logger.info(
                "INTERNAL_LLM_MODEL_SELECTION",
                requested_model=model_override,
                provider=provider or self.policy_loader.get_primary_provider(),
                enable_thinking=enable_thinking,
            )

            llm_response = llm_generate(
                prompt,
                provider=provider,  # Use provider from request, or None to use policy default
                temperature=persona_config.temperature,
                max_tokens=persona_config.max_tokens,
                model=model_override if model_override else None,
                enable_thinking=enable_thinking,  # Toggle thinking/reasoning mode
            )

            self.logger.info(
                "INTERNAL_LLM_MODEL_EFFECTIVE",
                effective_model=getattr(llm_response, "model", "unknown"),
                provider=provider or self.policy_loader.get_primary_provider(),
            )

            # Record LLM_CALL in trace timeline (stub for Phase 3)
            try:
                llm_event = {
                    "event": "LLM_CALL",
                    "ts": int(time.time()),
                    "provider": self.policy_loader.get_primary_provider(),
                    "model": getattr(llm_response, "model", "unknown"),
                    "tokens_used": getattr(llm_response, "usage", {}).total_tokens
                    if hasattr(getattr(llm_response, "usage", None), "total_tokens")
                    else 0,
                    "latency_ms": int((time.time() - start_time) * 1000),
                }
                te = self.trace_store.get(request_id) or trace_entry
                te_events = te.get("events", [])
                te_events.append(llm_event)
                te["events"] = te_events
                self.trace_store.put(request_id, te)
            except Exception:
                pass

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
                await self._store_response_in_memory(
                    doctor_id=effective_doctor_id,
                    session_id=session_id,
                    persona=persona,
                    response_text=response_text,
                    model_name=model_name,
                )

            # Calculate cost estimate (rough approximation based on tokens)
            # Azure GPT-4: ~$0.03 per 1K input tokens, $0.06 per 1K output tokens
            # Simplified: average $0.045 per 1K tokens
            cost_usd = (tokens_used / 1000) * 0.045 if tokens_used > 0 else 0.0

            # Log to audit trail for persona metrics tracking
            try:
                self.audit_service.log_action(
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
                        "session_id": session_id,
                        "memory_enabled": memory_enabled,
                        "provider": primary_provider,
                    },
                )
            except Exception as audit_error:
                # Don't fail the request if audit fails
                self.logger.warning(
                    "AUDIT_LOG_FAILED",
                    error=str(audit_error),
                    persona=effective_persona,
                )

            # Append CHAT_RESPONSE event to trace (stub for Phase 3)
            try:
                resp_event = {
                    "event": "CHAT_RESPONSE",
                    "ts": int(time.time()),
                    "latency_ms": latency_ms,
                    "tokens_used": tokens_used,
                    "model": model_name,
                }
                te = self.trace_store.get(request_id) or trace_entry
                te_events = te.get("events", [])
                te_events.append(resp_event)
                te["events"] = te_events
                self.trace_store.put(request_id, te)
            except Exception:
                pass

            self.logger.info(
                "INTERNAL_LLM_CHAT_SUCCESS",
                persona=persona,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                model=model_name,
                prompt_hash=prompt_hash[:12],
                response_hash=response_hash[:12],
                response_length=len(response_text),
                session_id=session_id,
                memory_enabled=memory_enabled,
                auto_memory_enabled=auto_memory_enabled,
                provider=primary_provider,
                cost_usd=round(cost_usd, 6),
            )

            # Log to observability hooks
            log_llm_call(
                request_id=request_id,
                persona=effective_persona,
                tokens=tokens_used,
                latency_ms=latency_ms,
                model=model_name,
            )

            # Extract optional reasoning from provider metadata
            thinking = None
            try:
                meta = getattr(llm_response, "metadata", None)
                if isinstance(meta, dict):
                    t = meta.get("thinking")
                    if isinstance(t, str) and t.strip():
                        thinking = t.strip()
            except Exception:
                thinking = None

            return ChatProcessingResult(
                request_id=request_id,
                trace_id=trace_id,
                persona=effective_persona,
                response_text=response_text,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                model_name=model_name,
                cost_usd=cost_usd,
                memory_enabled=memory_enabled,
                auto_memory_enabled=auto_memory_enabled,
                provider=primary_provider,
                prompt_hash=prompt_hash[:12],
                response_hash=response_hash[:12],
                voice=persona_config.voice,  # Azure TTS voice for this persona
                thinking=thinking,
                logged_at=datetime.now(UTC).isoformat(),
            )

        except ValueError as e:
            # Business validation error (400)
            self.logger.warning("CHAT_VALIDATION_FAILED", error=str(e))
            raise

        except Exception as e:
            # Unexpected error (500)
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.error(
                "INTERNAL_LLM_CHAT_ERROR",
                error=str(e),
                latency_ms=latency_ms,
                persona=persona,
                session_id=session_id,
            )

            # Log error to observability hooks
            log_llm_error(
                request_id=request_id,
                persona=persona,
                error=sanitize_error_message(str(e)),
                latency_ms=latency_ms,
            )

            raise

    async def _build_prompt_with_memory(
        self,
        message: str,
        persona: str,
        doctor_id: str,
        session_id: str | None,
        context: dict[str, Any] | None,
    ) -> tuple[str, dict]:
        """Build prompt with conversation memory.

        Args:
            message: User message
            persona: Persona to use
            doctor_id: Doctor identifier
            session_id: Session identifier
            context: Additional context

        Returns:
            Tuple of (prompt string, context info dict)
        """
        memory = get_memory_manager(doctor_id)

        # Store user message
        user_timestamp = datetime.now(UTC).isoformat()
        memory.store_interaction(
            session_id=session_id or "unknown",
            role="user",
            content=message,
            persona=persona,
        )

        # Broadcast user message to all connected devices (WebSocket)
        await broadcast_new_message(
            doctor_id=doctor_id,
            role="user",
            content=message,
            timestamp=user_timestamp,
            persona=persona,
        )

        # Get conversation context
        context_obj = memory.get_context(
            current_message=message,
            session_id=session_id,
        )

        # Build enriched prompt with memory
        system_prompt = self.persona_mgr.build_system_prompt(persona, context)
        prompt = memory.build_prompt(
            context=context_obj,
            system_prompt=system_prompt,
            current_message=message,
        )

        context_info = {
            "recent_count": len(context_obj.recent),
            "relevant_count": len(context_obj.relevant),
            "total_interactions": context_obj.total_interactions,
        }

        return prompt, context_info

    def _build_prompt_without_memory(
        self,
        message: str,
        persona: str,
        context: dict[str, Any] | None,
    ) -> str:
        """Build prompt without memory (original behavior).

        Args:
            message: User message
            persona: Persona to use
            context: Additional context

        Returns:
            Prompt string
        """
        prompt = self.persona_mgr.build_system_prompt(persona, context)

        if context:
            prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        prompt += f"\n\nUser: {message}\n\nAssistant:"

        return prompt

    async def _store_response_in_memory(
        self,
        doctor_id: str,
        session_id: str | None,
        persona: str,
        response_text: str,
        model_name: str,
    ) -> None:
        """Store assistant response in memory.

        Args:
            doctor_id: Doctor identifier
            session_id: Session identifier
            persona: Persona used
            response_text: Assistant response
            model_name: LLM model that generated response
        """
        memory = get_memory_manager(doctor_id)
        assistant_timestamp = datetime.now(UTC).isoformat()
        memory.store_interaction(
            session_id=session_id or "unknown",
            role="assistant",
            content=response_text,
            persona=persona,
            model=model_name,  # LLM model that generated this response
        )

        # Broadcast assistant response to all connected devices (WebSocket)
        await broadcast_new_message(
            doctor_id=doctor_id,
            role="assistant",
            content=response_text,
            timestamp=assistant_timestamp,
            persona=persona,
            model=model_name,  # LLM model that generated this response
        )
