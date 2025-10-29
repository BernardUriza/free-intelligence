"""
Free Intelligence - Claude Provider

Anthropic Claude API adapter.

File: backend/providers/claude.py
Created: 2025-10-28
"""

import json
import os
import time
from typing import Iterator, Optional

from backend.llm_adapter import (
    BudgetExceededError,
    LLMAdapter,
    LLMBudget,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
)
from backend.logger import get_logger

logger = get_logger(__name__)


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
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        budget: Optional[LLMBudget] = None,
        max_retries: int = 3,
    ):
        super().__init__(
            provider_name="claude",
            model=model,
            budget=budget,
            max_retries=max_retries,
        )

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
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

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
                kwargs = {
                    "model": self.model,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "messages": messages,
                }

                # Add system prompt if provided
                if request.system_prompt:
                    kwargs["system"] = request.system_prompt

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
                    model=self.model,
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

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

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
