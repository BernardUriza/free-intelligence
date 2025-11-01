"""
Free Intelligence - Claude Provider

Anthropic Claude API adapter.

File: backend/providers/claude.py
Created: 2025-10-28
"""

import os
import time
from collections.abc import Iterator
from typing import Optional

from backend.llm_adapter import (
    BudgetExceededError,
    LLMAdapter,
    LLMBudget,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
)
from backend.logger import get_logger
from backend.policy_enforcer import PolicyViolation, get_policy_enforcer
from backend.utils.token_counter import TokenCounter

logger = get_logger(__name__)
policy = get_policy_enforcer()


class ClaudeAdapter(LLMAdapter):
    """
    Anthropic Claude API adapter.

    Supports:
    - generate(): Single response with optional JSON schema
    - stream(): Streaming response
    - summarize(): Text summarization

    Features:
    - Timeout handling
    - Budget tracking
    - Retries with exponential backoff
    - Local logging (PHI redacted)
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        api_key: Optional[str] = None,
        budget: Optional[LLMBudget] = None,
        max_retries: int = 3,
        token_counter: Optional[TokenCounter] = None,
        base_delay_ms: int = 100,
        max_delay_ms: int = 2000,
    ):
        super().__init__(
            provider_name="claude",
            model=model,
            budget=budget,
            max_retries=max_retries,
        )

        # Inject token counter (create default if not provided)
        self.token_counter = token_counter or TokenCounter()
        # Retry backoff configuration
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms

        # Get API key from env if not provided
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Claude API key required. Set CLAUDE_API_KEY env var or pass api_key parameter."
            )

        # Import anthropic here to avoid import errors if not installed
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a single response.

        Supports JSON schema via response_format parameter.
        """
        # Check budget
        if not self.budget.can_make_request(request.max_tokens):
            raise BudgetExceededError(
                f"Budget exceeded: {self.budget.requests_made}/{self.budget.max_requests_per_hour} requests, "
                f"{self.budget.tokens_used}/{self.budget.max_tokens_per_hour} tokens"
            )

        # Log request (PHI redacted)
        logger.info(
            "LLM_REQUEST_STARTED",
            provider=self.provider_name,
            model=self.model,
            prompt_preview=self.redact_phi(request.prompt[:100]),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            has_schema=request.schema is not None,
        )

        start_time = time.time()

        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Build messages
                messages = [{"role": "user", "content": request.prompt}]

                # Build request kwargs
                # Use request.model if provided, otherwise fall back to self.model
                model_to_use = getattr(request, "model", None) or self.model
                kwargs = {
                    "model": model_to_use,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "messages": messages,
                }

                # Add system prompt if provided
                if request.system_prompt:
                    kwargs["system"] = request.system_prompt

                # Policy: Check egress (sovereignty.egress.default=deny blocks external APIs)
                try:
                    policy.check_egress(
                        "https://api.anthropic.com",
                        run_id=request.metadata.get("interaction_id") if request.metadata else None,
                    )
                except PolicyViolation as e:
                    logger.error(
                        "EGRESS_BLOCKED", provider="claude", url="api.anthropic.com", error=str(e)
                    )
                    raise LLMProviderError(f"External API call blocked by policy: {e}")

                # Call Claude API
                response = self.client.messages.create(**kwargs)

                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)

                # Extract content
                content = response.content[0].text

                # Count tokens (approximation: Claude doesn't return token count in all responses)
                # For now, use input + output from usage
                tokens_used = response.usage.input_tokens + response.usage.output_tokens

                # Track budget
                self.budget.track_request(tokens_used)

                # Build response
                llm_response = LLMResponse(
                    content=content,
                    provider=self.provider_name,
                    model=model_to_use,  # Use actual model from request, not adapter default
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    finish_reason=response.stop_reason or "stop",
                    metadata={
                        "request_id": response.id,
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                )

                # Log success
                logger.info(
                    "LLM_REQUEST_COMPLETED",
                    provider=self.provider_name,
                    model=self.model,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    finish_reason=llm_response.finish_reason,
                )

                return llm_response

            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM_REQUEST_RETRY",
                    provider=self.provider_name,
                    model=self.model,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                )

                # Exponential backoff with configurable limits
                if attempt < self.max_retries - 1:
                    delay_ms = min(self.base_delay_ms * (2**attempt), self.max_delay_ms)
                    time.sleep(delay_ms / 1000.0)  # Convert ms to seconds

        # All retries failed
        logger.error(
            "LLM_REQUEST_FAILED",
            provider=self.provider_name,
            model=self.model,
            error=str(last_error),
        )
        raise LLMProviderError(f"Claude API failed after {self.max_retries} retries: {last_error}")

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """
        Stream response chunks.

        Note: Budget tracking is approximate for streaming.
        """
        # Check budget
        if not self.budget.can_make_request(request.max_tokens):
            raise BudgetExceededError(
                f"Budget exceeded: {self.budget.requests_made}/{self.budget.max_requests_per_hour} requests"
            )

        # Log request
        logger.info(
            "LLM_STREAM_STARTED",
            provider=self.provider_name,
            model=self.model,
            prompt_preview=self.redact_phi(request.prompt[:100]),
        )

        try:
            # Build messages
            messages = [{"role": "user", "content": request.prompt}]

            # Build request kwargs
            kwargs = {
                "model": self.model,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": messages,
            }

            # Add system prompt if provided
            if request.system_prompt:
                kwargs["system"] = request.system_prompt

            # Policy: Check egress for streaming endpoint
            try:
                policy.check_egress(
                    "https://api.anthropic.com",
                    run_id=request.metadata.get("interaction_id") if request.metadata else None,
                )
            except PolicyViolation as e:
                logger.error(
                    "EGRESS_BLOCKED_STREAM",
                    provider="claude",
                    url="api.anthropic.com",
                    error=str(e),
                )
                raise LLMProviderError(f"External streaming API call blocked by policy: {e}")

            # Stream response
            with self.client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text

            # Track budget (approximate)
            self.budget.track_request(request.max_tokens // 2)

            logger.info(
                "LLM_STREAM_COMPLETED",
                provider=self.provider_name,
                model=self.model,
            )

        except Exception as e:
            logger.error(
                "LLM_STREAM_FAILED",
                provider=self.provider_name,
                model=self.model,
                error=str(e),
            )
            raise LLMProviderError(f"Claude streaming failed: {e}")
