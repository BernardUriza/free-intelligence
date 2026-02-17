"""Chat Service - Orchestrates LLM chat operations.

Single Responsibility: Coordinate prompt building, LLM calls, memory, and observability.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor from chat.py monolith)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from backend.infrastructure.observability.hooks import log_llm_call, log_llm_error
from backend.providers import llm_generate
from backend.services.llm.dependencies import get_persona_manager
from backend.utils.common.logging.logger import get_logger

from .memory_handler import ChatMemoryHandler
from .prompt_builder import ChatPromptBuilder

if TYPE_CHECKING:
    from backend.policy.interfaces.ipolicy_loader import IPolicyLoader
    from backend.services.audit.services.audit_service import AuditService
    from backend.services.llm.models.persona import PersonaConfig

logger = get_logger(__name__)


@dataclass
class ChatContext:
    """Context for a chat request."""

    message: str
    persona: str
    session_id: str | None = None
    doctor_id: str | None = None
    use_memory: bool = False
    provider: str | None = None
    context: dict[str, Any] | None = None
    messages: list[Any] | None = None  # ChatMessage list


@dataclass
class ChatResult:
    """Result of a chat operation."""

    response: str
    thinking: str | None
    persona: str
    tokens_used: int
    latency_ms: int
    model: str
    voice: str
    prompt_hash: str
    response_hash: str
    logged_at: str
    memory_enabled: bool = False
    cost_usd: float = 0.0


@dataclass
class ChatState:
    """Internal state during chat processing."""

    start_time: float = field(default_factory=time.time)
    prompt: str = ""
    prompt_hash: str = ""
    effective_persona: str = ""
    effective_doctor_id: str | None = None
    memory_enabled: bool = False
    auto_memory_enabled: bool = False
    persona_config: "PersonaConfig | None" = None
    primary_provider: str = ""


class ChatService:
    """Orchestrates LLM chat operations.

    Coordinates:
    - Persona routing and configuration
    - Prompt building with/without memory
    - LLM provider calls
    - Memory persistence
    - Audit logging and observability
    """

    def __init__(
        self,
        policy_loader: "IPolicyLoader",
        audit_service: "AuditService | None" = None,
    ) -> None:
        self.policy_loader = policy_loader
        self.audit_service = audit_service
        self.persona_manager = get_persona_manager()
        self.prompt_builder = ChatPromptBuilder(self.persona_manager)
        self.memory_handler = ChatMemoryHandler()

    async def process_chat(self, ctx: ChatContext) -> ChatResult:
        """Process a chat request end-to-end.

        Args:
            ctx: Chat context with message, persona, options

        Returns:
            ChatResult with response and metadata

        Raises:
            ValueError: If persona is invalid or memory requires doctor_id
        """
        state = ChatState()
        state.primary_provider = self.policy_loader.get_primary_provider()

        # Step 1: Resolve effective persona
        state.effective_persona = self._resolve_persona(ctx)

        # Step 2: Get persona config
        state.persona_config = self.persona_manager.get_persona(state.effective_persona)

        # Step 3: Setup memory
        state.effective_doctor_id = ctx.doctor_id
        memory = self._setup_memory(ctx, state)

        # Step 4: Build prompt
        if state.memory_enabled and memory:
            await self.memory_handler.store_user_message(
                memory=memory,
                doctor_id=state.effective_doctor_id,
                session_id=ctx.session_id,
                message=ctx.message,
                persona=ctx.persona,
            )
            built = self.prompt_builder.build_with_memory(
                message=ctx.message,
                persona=state.effective_persona,
                context=ctx.context,
                memory=memory,
                session_id=ctx.session_id,
            )
        else:
            built = self.prompt_builder.build_without_memory(
                message=ctx.message,
                persona=state.effective_persona,
                context=ctx.context,
                messages=ctx.messages,
            )

        state.prompt = built.prompt
        state.prompt_hash = hashlib.sha256(state.prompt.encode()).hexdigest()
        state.memory_enabled = built.memory_enabled

        # Step 5: Call LLM
        model_override, enable_thinking = self._parse_model_options(ctx.context)

        logger.info(
            "CHAT_LLM_CALL",
            persona=state.effective_persona,
            provider=ctx.provider or state.primary_provider,
            model_override=model_override,
            prompt_length=len(state.prompt),
        )

        # Persona config is set in Step 2, guaranteed non-None here
        assert state.persona_config is not None

        llm_response = llm_generate(
            state.prompt,
            provider=ctx.provider,
            temperature=state.persona_config.temperature,
            max_tokens=state.persona_config.max_tokens,
            model=model_override,
            enable_thinking=enable_thinking,
            format=state.persona_config.response_format,
        )

        # Step 6: Extract response data
        response_text = llm_response.content.strip()
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()
        latency_ms = int((time.time() - state.start_time) * 1000)

        tokens_used = 0
        model_name = "unknown"
        if hasattr(llm_response, "usage") and llm_response.usage:
            tokens_used = llm_response.usage.total_tokens
        if hasattr(llm_response, "model"):
            model_name = llm_response.model

        # Step 7: Store assistant response in memory
        if state.memory_enabled and state.effective_doctor_id:
            memory = self.memory_handler.get_memory(state.effective_doctor_id)
            if memory:
                await self.memory_handler.store_assistant_message(
                    memory=memory,
                    doctor_id=state.effective_doctor_id,
                    session_id=ctx.session_id,
                    content=response_text,
                    persona=ctx.persona,
                    model=model_name,
                )

        # Step 8: Calculate cost and log
        cost_usd = (tokens_used / 1000) * 0.045 if tokens_used > 0 else 0.0

        self._log_success(
            state=state,
            ctx=ctx,
            response_text=response_text,
            response_hash=response_hash,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model_name=model_name,
            cost_usd=cost_usd,
        )

        # Step 9: Extract thinking if available
        thinking = self._extract_thinking(llm_response)

        return ChatResult(
            response=response_text,
            thinking=thinking,
            persona=state.effective_persona,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model=model_name,
            voice=state.persona_config.voice,
            prompt_hash=state.prompt_hash[:12],
            response_hash=response_hash[:12],
            logged_at=datetime.now(UTC).isoformat(),
            memory_enabled=state.memory_enabled,
            cost_usd=cost_usd,
        )

    def _resolve_persona(self, ctx: ChatContext) -> str:
        """Resolve effective persona using auto-routing if needed."""
        if ctx.persona == "auto" or not ctx.persona:
            effective = self.persona_manager.route_persona(ctx.message)
            logger.info(
                "PERSONA_AUTO_ROUTED",
                user_message_preview=ctx.message[:50],
                routed_to=effective,
            )
            return effective
        return ctx.persona

    def _setup_memory(
        self, ctx: ChatContext, state: ChatState
    ) -> "Any | None":
        """Setup memory based on context and provider policy."""
        # Auto-enable memory for Azure GPT-4
        if state.primary_provider == "azure":
            state.auto_memory_enabled = True
            if not ctx.doctor_id:
                state.effective_doctor_id = "system"
                logger.info(
                    "MEMORY_AUTO_ENABLED_AZURE",
                    provider=state.primary_provider,
                )

        # Validate memory requirements
        if ctx.use_memory and not ctx.doctor_id and not state.auto_memory_enabled:
            raise ValueError("doctor_id is required when use_memory=True")

        # Get memory manager
        memory_enabled = ctx.use_memory or state.auto_memory_enabled
        memory = None

        if memory_enabled and state.effective_doctor_id:
            memory = self.memory_handler.get_memory(state.effective_doctor_id)
            if memory is None:
                state.memory_enabled = False
                logger.info("MEMORY_DISABLED_NO_EMBEDDINGS")
            else:
                state.memory_enabled = True

        return memory

    def _parse_model_options(
        self, context: dict[str, Any] | None
    ) -> tuple[str | None, bool]:
        """Parse model override and thinking options from context."""
        model_override = None
        enable_thinking = False

        if isinstance(context, dict):
            m = context.get("model")
            if isinstance(m, str) and m.strip():
                model_override = m.strip()
            if "enable_thinking" in context:
                enable_thinking = bool(context.get("enable_thinking", True))

        return model_override, enable_thinking

    def _extract_thinking(self, llm_response: Any) -> str | None:
        """Extract reasoning from provider metadata if available."""
        try:
            meta = getattr(llm_response, "metadata", None)
            if isinstance(meta, dict):
                t = meta.get("thinking")
                if isinstance(t, str) and t.strip():
                    return t.strip()
        except Exception:
            pass
        return None

    def _log_success(
        self,
        state: ChatState,
        ctx: ChatContext,
        response_text: str,
        response_hash: str,
        tokens_used: int,
        latency_ms: int,
        model_name: str,
        cost_usd: float,
    ) -> None:
        """Log successful chat to audit and observability."""
        # Audit service
        if self.audit_service:
            try:
                self.audit_service.log_action(
                    action="llm_call",
                    user_id=state.effective_doctor_id or "anonymous",
                    resource=f"persona:{state.effective_persona}",
                    result="success",
                    details={
                        "persona": state.effective_persona,
                        "latency_ms": latency_ms,
                        "tokens_used": tokens_used,
                        "cost_usd": round(cost_usd, 6),
                        "model": model_name,
                        "session_id": ctx.session_id,
                        "memory_enabled": state.memory_enabled,
                        "provider": state.primary_provider,
                    },
                )
            except Exception as e:
                logger.warning("AUDIT_LOG_FAILED", error=str(e))

        # Observability database
        log_llm_call(
            model=model_name,
            provider=state.primary_provider,
            latency_ms=latency_ms,
            prompt_tokens=tokens_used,
            completion_tokens=0,
            status="success",
            prompt_preview=state.prompt[:500] if state.prompt else "",
            response_preview=response_text[:500] if response_text else "",
            client_id=state.effective_doctor_id,
            session_id=ctx.session_id,
            persona=state.effective_persona,
            prompt_hash=state.prompt_hash,
            response_hash=response_hash,
            metadata={
                "memory_enabled": state.memory_enabled,
                "cost_usd": round(cost_usd, 6),
            },
        )

        # Structured log
        logger.info(
            "CHAT_SUCCESS",
            persona=state.effective_persona,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model=model_name,
            prompt_hash=state.prompt_hash[:12],
            response_hash=response_hash[:12],
            memory_enabled=state.memory_enabled,
            cost_usd=round(cost_usd, 6),
        )

    def log_error(
        self,
        ctx: ChatContext,
        error: Exception,
        prompt: str,
        latency_ms: int,
    ) -> None:
        """Log chat error to observability."""
        log_llm_error(
            model="unknown",
            provider=self.policy_loader.get_primary_provider(),
            latency_ms=latency_ms,
            error_message=str(error),
            error_type=type(error).__name__,
            prompt_preview=prompt[:500] if prompt else "",
            client_id=ctx.doctor_id,
            session_id=ctx.session_id,
            persona=ctx.persona,
        )
