"""
Free Intelligence - Claude (Anthropic) LLM Provider

Anthropic Claude provider implementation for cloud-based inference.
Primary provider for production use.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, ClassVar

import anthropic
import numpy as np

from backend.providers.base import LLMProvider, LLMResponse
from backend.providers.embeddings import fallback_embed_sentence_transformer
from backend.providers.utils import sanitize_error_message


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation"""

    # Pricing per 1M tokens (as of 2025-10)
    PRICING: ClassVar[dict[str, dict[str, float]]] = {
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,  # $3 per 1M input tokens
            "output": 15.00,  # $15 per 1M output tokens
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,  # $0.80 per 1M input tokens
            "output": 4.00,  # $4 per 1M output tokens
        },
    }

    client: anthropic.Anthropic
    default_model: str
    timeout: int

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise ValueError("CLAUDE_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_model = str(self.config.get("model") or "claude-3-5-sonnet-20241022")
        self.timeout = int(self.config.get("timeout_seconds") or 30)
        self.logger.info("CLAUDE_PROVIDER_INITIALIZED", model=self.default_model)

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Generate completion using Claude API"""
        model: str = str(kwargs.get("model", self.default_model))
        max_tokens: int = int(kwargs.get("max_tokens") or self.config.get("max_tokens") or 4096)
        temperature: float = float(
            kwargs.get("temperature") or self.config.get("temperature") or 0.7
        )

        self.logger.info(
            "CLAUDE_GENERATE_STARTED",
            model=model,
            prompt_length=len(prompt),
            max_tokens=max_tokens,
            temperature=temperature,
        )

        start_time = datetime.now(UTC)

        try:
            self.logger.info("CLAUDE_CALLING_API", timeout=self.timeout)

            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout,
            )

            self.logger.info("CLAUDE_API_RESPONSE_RECEIVED")

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Extract response content
            content = message.content[0].text if message.content else ""  # type: ignore[attr-defined]

            self.logger.info(
                "CLAUDE_RESPONSE_EXTRACTED",
                content_length=len(content),
            )

            # Calculate cost
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            pricing = self.PRICING.get(model, self.PRICING["claude-3-5-sonnet-20241022"])
            cost_usd = (input_tokens / 1_000_000) * pricing["input"] + (
                output_tokens / 1_000_000
            ) * pricing["output"]

            self.logger.info(
                "CLAUDE_GENERATE_COMPLETED",
                model=model,
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost_usd, 6),
                latency_ms=round(latency_ms, 2),
            )

            return LLMResponse(
                content=content,
                model=model,
                provider="claude",
                tokens_used=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "stop_reason": message.stop_reason,
                },
            )

        except anthropic.APITimeoutError as e:
            sanitized_error = sanitize_error_message(str(e))
            self.logger.error(
                "CLAUDE_TIMEOUT_ERROR", error=sanitized_error, timeout=self.timeout
            )
            raise
        except anthropic.APIConnectionError as e:
            sanitized_error = sanitize_error_message(str(e))
            self.logger.error("CLAUDE_CONNECTION_ERROR", error=sanitized_error)
            raise
        except anthropic.RateLimitError as e:
            sanitized_error = sanitize_error_message(str(e))
            self.logger.error("CLAUDE_RATE_LIMIT_ERROR", error=sanitized_error)
            raise
        except anthropic.APIError as e:
            sanitized_error = sanitize_error_message(str(e))
            self.logger.error(
                "CLAUDE_API_ERROR",
                error=sanitized_error,
                status_code=getattr(e, "status_code", None),
            )
            raise

    def embed(self, text: str) -> np.ndarray:
        """
        Claude doesn't provide embeddings API.
        Fall back to sentence-transformers.
        """
        return fallback_embed_sentence_transformer(
            text=text,
            provider_name="claude",
        )

    def get_provider_name(self) -> str:
        return "claude"
