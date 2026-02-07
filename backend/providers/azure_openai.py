"""
Free Intelligence - Azure OpenAI LLM Provider

Azure OpenAI (GPT-4, GPT-4o) provider for cloud-based inference.
"""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, ClassVar

import numpy as np

from backend.providers.base import LLMProvider, LLMResponse
from backend.providers.embeddings import fallback_embed_sentence_transformer
from backend.providers.utils import sanitize_error_message

# Optional: aiohttp for async HTTP
try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI (GPT-4, GPT-4o) provider for cloud-based inference"""

    # Pricing per 1M tokens (as of 2025-11)
    PRICING: ClassVar[dict[str, dict[str, float]]] = {
        "gpt-4o": {
            "input": 2.50,  # $2.50 per 1M input tokens
            "output": 10.00,  # $10 per 1M output tokens
        },
        "gpt-4": {
            "input": 30.00,  # $30 per 1M input tokens
            "output": 60.00,  # $60 per 1M output tokens
        },
    }

    endpoint: str | None
    api_key: str | None
    api_version: str
    default_model: str
    deployment_name: str
    timeout: int
    aiohttp: Any

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.api_version = str(self.config.get("api_version") or "2024-02-15-preview")

        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_KEY environment variable not set")

        self.default_model = str(self.config.get("model") or "gpt-4o")
        self.deployment_name = str(self.config.get("deployment") or self.default_model)
        self.timeout = int(self.config.get("timeout_seconds") or 30)

        # Check if aiohttp is available
        if aiohttp is None:
            raise ImportError("aiohttp library not installed. Install with: pip install aiohttp")

        self.aiohttp = aiohttp

        self.logger.info(
            "AZURE_OPENAI_PROVIDER_INITIALIZED",
            endpoint=self.endpoint,
            model=self.default_model,
            deployment=self.deployment_name,
        )

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """
        Generate completion using Azure OpenAI API.

        Args:
            prompt: Input text prompt
            **kwargs: Azure-specific parameters (model, temperature, max_tokens, etc.)

        Returns:
            LLMResponse with content and metadata

        Notes:
            - Requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables
            - Supports chat/completions endpoint with streaming
            - Pricing: gpt-4o ($2.50/$10 per 1M tokens), gpt-4 ($30/$60)
        """

        model: str = str(kwargs.get("model", self.default_model))
        deployment: str = str(kwargs.get("deployment", self.deployment_name))
        max_tokens: int = int(kwargs.get("max_tokens") or self.config.get("max_tokens") or 1024)
        temperature: float = float(
            kwargs.get("temperature") or self.config.get("temperature") or 0.7
        )

        self.logger.info(
            "AZURE_GENERATE_STARTED",
            model=model,
            deployment=deployment,
            prompt_length=len(prompt),
            max_tokens=max_tokens,
            temperature=temperature,
        )

        start_time = datetime.now(UTC)

        try:
            # Check if we're already in an async context
            try:
                _ = asyncio.get_running_loop()
                # We're already in an event loop, so we need to run in a thread

                with ThreadPoolExecutor() as executor:
                    response = executor.submit(
                        lambda: asyncio.run(
                            self._generate_async(
                                prompt=prompt,
                                model=model,
                                deployment=deployment,
                                max_tokens=max_tokens,
                                temperature=temperature,
                            )
                        )
                    ).result()
            except RuntimeError:
                # No event loop running, safe to use asyncio.run()
                response = asyncio.run(
                    self._generate_async(
                        prompt=prompt,
                        model=model,
                        deployment=deployment,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            self.logger.info(
                "AZURE_GENERATE_COMPLETED",
                model=model,
                deployment=deployment,
                tokens_used=response["total_tokens"],
                cost_usd=round(response["cost_usd"], 6),
                latency_ms=round(latency_ms, 2),
            )

            return LLMResponse(
                content=response["content"],
                model=model,
                provider="azure",
                tokens_used=response["total_tokens"],
                cost_usd=response["cost_usd"],
                latency_ms=latency_ms,
                metadata={
                    "input_tokens": response["input_tokens"],
                    "output_tokens": response["output_tokens"],
                    "deployment": deployment,
                    "finish_reason": response["finish_reason"],
                },
            )

        except Exception as e:
            sanitized_error = sanitize_error_message(str(e))
            self.logger.error(
                "AZURE_GENERATE_FAILED",
                error=sanitized_error,
                model=model,
                deployment=deployment,
            )
            raise

    async def _generate_async(
        self, prompt: str, model: str, deployment: str, max_tokens: int, temperature: float
    ) -> dict[str, Any]:
        """
        Async helper for Azure OpenAI API call.

        Args:
            prompt: Input text prompt
            model: Model name
            deployment: Azure deployment name
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Dictionary with response content and metadata
        """
        url = f"{self.endpoint}openai/deployments/{deployment}/chat/completions?api-version={self.api_version}"

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        self.logger.info("AZURE_CALLING_API")

        async with self.aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"Azure API error {resp.status}: {error_text}")

                    data = await resp.json()

                    # Extract response
                    content = data["choices"][0]["message"]["content"]
                    input_tokens = data["usage"]["prompt_tokens"]
                    output_tokens = data["usage"]["completion_tokens"]
                    total_tokens = input_tokens + output_tokens
                    finish_reason = data["choices"][0].get("finish_reason", "stop")

                    # Calculate cost
                    pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])
                    cost_usd = (input_tokens / 1_000_000) * pricing["input"] + (
                        output_tokens / 1_000_000
                    ) * pricing["output"]

                    self.logger.info("AZURE_API_RESPONSE_RECEIVED")

                    return {
                        "content": content,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "finish_reason": finish_reason,
                        "cost_usd": cost_usd,
                    }

            except self.aiohttp.ClientConnectorError as e:
                sanitized_error = sanitize_error_message(str(e))
                self.logger.error("AZURE_CONNECTION_ERROR", error=sanitized_error)
                raise
            except TimeoutError as e:
                sanitized_error = sanitize_error_message(str(e))
                self.logger.error(
                    "AZURE_TIMEOUT_ERROR", error=sanitized_error, timeout=self.timeout
                )
                raise
            except Exception as e:
                sanitized_error = sanitize_error_message(str(e))
                self.logger.error("AZURE_API_ERROR", error=sanitized_error)
                raise

    def embed(self, text: str) -> np.ndarray:
        """
        Azure OpenAI doesn't provide embeddings API.
        Fall back to sentence-transformers.
        """
        return fallback_embed_sentence_transformer(
            text=text,
            provider_name="azure",
        )

    def get_provider_name(self) -> str:
        return "azure"
