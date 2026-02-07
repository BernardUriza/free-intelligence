"""
Free Intelligence - Ollama LLM Provider

Ollama local inference provider for offline-first operation.

Features (FI-BACKEND-REF-005, FI-BACKEND-FALLBACK-001):
- Exponential backoff retry for transient failures
- Circuit breaker to prevent cascade failures
- Multi-host fallback (Windows tunnel -> Mac localhost)
- Qwen3 thinking mode support
"""

from __future__ import annotations

import os
import threading
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import numpy as np
import ollama

from backend.providers.base import LLMProvider, LLMResponse
from backend.providers.resilience import ResilienceExecutor
from backend.providers.response_parsers import GenericParser, QwenThinkingParser
from backend.providers.retry import CircuitBreakerConfig, RetryConfig, get_circuit_breaker
from backend.utils.common.config.deployment import get_ollama_hosts


class OllamaProvider(LLMProvider):
    """
    Ollama local inference provider for offline-first operation.

    Features (FI-BACKEND-REF-005):
    - Exponential backoff retry for transient failures
    - Circuit breaker to prevent cascade failures
    - Configurable thresholds: failure_threshold=5, window=60s
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)

        # Thread safety lock for host state mutations (FI-BACKEND-FALLBACK-001)
        self._host_lock = threading.Lock()

        # Multi-host fallback support (FI-BACKEND-FALLBACK-001)
        self.hosts = get_ollama_hosts()
        self.base_url: str = self.hosts[0]["url"]

        self.default_model: str = str(self.config.get("model") or "qwen3:1.7b")
        self.embed_model: str = str(self.config.get("embed_model") or "nomic-embed-text")
        self.timeout: int = int(self.config.get("timeout_seconds") or 120)

        # Retry configuration (FI-BACKEND-REF-005)
        self.retry_config = RetryConfig(
            max_retries=int(self.config.get("max_retries") or 3),
            base_delay=float(self.config.get("retry_base_delay") or 1.0),
            max_delay=float(self.config.get("retry_max_delay") or 30.0),
            exponential_base=2.0,
            jitter=True,
        )

        # Circuit breaker PER HOST (FI-BACKEND-FALLBACK-001)
        cb_config = CircuitBreakerConfig(
            failure_threshold=int(self.config.get("circuit_failure_threshold") or 5),
            recovery_timeout=float(self.config.get("circuit_recovery_timeout") or 60.0),
            success_threshold=2,
        )

        self.circuit_breakers: dict[str, Any] = {}
        self.clients: dict[str, Any] = {}

        for host in self.hosts:
            host_url = str(host["url"])
            host_name = str(host["name"])
            self.circuit_breakers[host_url] = get_circuit_breaker(
                name=f"ollama_{host_name}",
                config=cb_config,
            )
            self.clients[host_url] = ollama.Client(host=host_url)

        # Backward compatibility: single client/circuit_breaker for current host
        self.client = self.clients[self.base_url]
        self.circuit_breaker = self.circuit_breakers[self.base_url]

        # Initialize resilience executor
        self._executor = ResilienceExecutor(
            hosts=self.hosts,
            retry_config=self.retry_config,
            circuit_breakers=self.circuit_breakers,
            host_lock=self._host_lock,
        )

        # Initialize response parsers
        self.qwen_parser = QwenThinkingParser()
        self.generic_parser = GenericParser()

        self.logger.info(
            "OLLAMA_PROVIDER_INITIALIZED",
            base_url=self.base_url,
            model=self.default_model,
            embed_model=self.embed_model,
            hosts=[{"name": h["name"], "url": h["url"]} for h in self.hosts],
            fallback_enabled=len(self.hosts) > 1,
            retry_config=self.retry_config.to_dict(),
            circuit_breaker_config=cb_config.to_dict(),
        )

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """
        Generate completion using Ollama API with multi-host fallback.

        Args:
            prompt: Input text prompt
            **kwargs: Ollama-specific parameters (model, temperature, max_tokens, format, etc.)
                - format: Optional JSON schema dict to constrain output to valid JSON

        Returns:
            LLMResponse with content and metadata
        """
        model_arg = kwargs.get("model")
        model: str = model_arg if model_arg else self.default_model
        max_tokens: int = int(kwargs.get("max_tokens") or self.config.get("max_tokens") or 2048)
        temperature: float = float(
            kwargs.get("temperature") or self.config.get("temperature") or 0.7
        )
        # JSON format constraint for structured output (Ollama native feature)
        json_format: dict | None = kwargs.get("format")

        self.logger.info(
            "OLLAMA_GENERATE_STARTED",
            model=model,
            prompt_length=len(prompt),
            hosts_available=len(self.hosts),
            json_format_enabled=json_format is not None,
        )

        start_time = datetime.now(UTC)

        # Thinking mode control
        force_thinking = os.getenv("LLM_FORCE_THINKING", "false").lower() in {"1", "true", "yes"}
        enable_thinking = kwargs.get("enable_thinking", True)
        is_qwen3 = str(model).lower().startswith("qwen3")
        use_generate_with_think = enable_thinking and (is_qwen3 or force_thinking)

        def _make_request(client: Any, host_url: str) -> dict[str, Any]:
            """Execute Ollama request and parse response."""
            # Build common kwargs - format constrains output to JSON schema
            format_kwargs = {"format": json_format} if json_format else {}

            if use_generate_with_think:
                response = client.generate(
                    model=model,
                    prompt=prompt,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "think": True,
                    },
                    **format_kwargs,
                )
            else:
                response = client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    think=enable_thinking,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    **format_kwargs,
                )
            return {"response": response, "host_url": host_url}

        # Execute with resilience patterns
        result, host_url, hosts_tried = self._executor.execute(
            operation=_make_request,
            clients=self.clients,
            operation_name="generate",
        )

        response = result["response"]
        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        # Parse response
        thinking_text, content = self._parse_response(response, use_generate_with_think)

        # Token estimation
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(content) // 4
        total_tokens = prompt_tokens + completion_tokens
        if isinstance(response, dict) and "eval_count" in response:
            completion_tokens = response["eval_count"]
            total_tokens = response.get("prompt_eval_count", prompt_tokens) + completion_tokens

        # Update backward compatibility references
        with self._host_lock:
            self.base_url = host_url
            self.client = self.clients[host_url]
            self.circuit_breaker = self.circuit_breakers[host_url]

        # Find host name for logging
        host_name = next((h["name"] for h in self.hosts if h["url"] == host_url), "unknown")

        self.logger.info(
            "OLLAMA_GENERATE_COMPLETED",
            model=model,
            host=host_name,
            tokens_used=total_tokens,
            latency_ms=round(latency_ms, 2),
            hosts_tried=hosts_tried,
        )

        return LLMResponse(
            content=content,
            model=model,
            provider="ollama",
            tokens_used=total_tokens,
            cost_usd=0.0,
            latency_ms=latency_ms,
            metadata={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "base_url": host_url,
                "host_name": host_name,
                "eval_count": response.get("eval_count") if isinstance(response, dict) else None,
                "eval_duration": response.get("eval_duration") if isinstance(response, dict) else None,
                "hosts_tried": hosts_tried,
                **({"thinking": thinking_text} if thinking_text else {}),
            },
        )

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding using Ollama with multi-host fallback.

        Args:
            text: Input text to embed

        Returns:
            numpy array with embedding vector
        """
        self.logger.info("OLLAMA_EMBED_STARTED", text_length=len(text))

        def _make_request(client: Any, host_url: str) -> dict[str, Any]:
            """Execute Ollama embeddings request."""
            response = client.embeddings(model=self.embed_model, prompt=text)
            return {"response": response, "host_url": host_url}

        result, host_url, hosts_tried = self._executor.execute(
            operation=_make_request,
            clients=self.clients,
            operation_name="embed",
        )

        response = result["response"]
        embedding = np.array(response["embedding"], dtype=np.float32)

        # Update backward compatibility references
        with self._host_lock:
            self.base_url = host_url
            self.client = self.clients[host_url]
            self.circuit_breaker = self.circuit_breakers[host_url]

        host_name = next((h["name"] for h in self.hosts if h["url"] == host_url), "unknown")

        self.logger.info(
            "OLLAMA_EMBED_COMPLETED",
            embedding_dim=len(embedding),
            model=self.embed_model,
            host=host_name,
            hosts_tried=hosts_tried,
        )
        return embedding

    def generate_stream(self, prompt: str, **kwargs: Any) -> Generator[tuple[str, str], None, None]:
        """
        Generate completion using Ollama API with real-time streaming and multi-host fallback.

        Yields chunks as they arrive from Ollama without waiting for complete response.

        Args:
            prompt: Input text prompt
            **kwargs: Ollama-specific parameters (model, temperature, max_tokens, format, etc.)
                - format: Optional JSON schema dict to constrain output to valid JSON

        Yields:
            tuple[str, str]: (chunk_type, chunk_text) where chunk_type is "thinking" or "content"
        """
        model_arg = kwargs.get("model")
        model: str = model_arg if model_arg else self.default_model
        max_tokens: int = int(kwargs.get("max_tokens") or self.config.get("max_tokens") or 2048)
        temperature: float = float(
            kwargs.get("temperature") or self.config.get("temperature") or 0.7
        )
        # JSON format constraint for structured output (Ollama native feature)
        json_format: dict | None = kwargs.get("format")

        self.logger.info(
            "OLLAMA_GENERATE_STREAM_STARTED",
            model=model,
            prompt_length=len(prompt),
            hosts_available=len(self.hosts),
            json_format_enabled=json_format is not None,
        )

        force_thinking = os.getenv("LLM_FORCE_THINKING", "false").lower() in {"1", "true", "yes"}
        enable_thinking = kwargs.get("enable_thinking", True)
        is_qwen3 = str(model).lower().startswith("qwen3")
        use_generate_with_think = enable_thinking and (is_qwen3 or force_thinking)

        # Build format kwargs - format constrains output to JSON schema
        format_kwargs = {"format": json_format} if json_format else {}

        def _make_stream_request(client: Any, _host_url: str) -> Generator[tuple[str, str], None, None]:
            """Execute streaming Ollama request."""
            if use_generate_with_think:
                response = client.generate(
                    model=model,
                    prompt=prompt,
                    stream=True,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "think": True,
                    },
                    **format_kwargs,
                )
            else:
                response = client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "think": False,
                    },
                    **format_kwargs,
                )

            for chunk in response:
                try:
                    if use_generate_with_think:
                        thinking_text = chunk.get("thinking", "")
                        response_text = chunk.get("response", "")
                        if thinking_text:
                            yield ("thinking", thinking_text)
                        if response_text:
                            yield ("content", response_text)
                    else:
                        chunk_text = chunk.get("message", {}).get("content", "")
                        if chunk_text:
                            yield ("content", chunk_text)
                except Exception:
                    continue

        # Use resilience executor for streaming
        yield from self._executor.execute_generator(
            operation=_make_stream_request,
            clients=self.clients,
            operation_name="generate_stream",
        )

    def _parse_response(
        self, response: Any, use_generate_with_think: bool
    ) -> tuple[str | None, str]:
        """
        Parse Ollama response to extract thinking and content.

        Args:
            response: Raw Ollama response
            use_generate_with_think: Whether generate endpoint with think=True was used

        Returns:
            Tuple of (thinking_text, content)
        """
        thinking_text: str | None = None
        content: str = ""

        if use_generate_with_think:
            try:
                thinking_text, content = self.qwen_parser.parse(response)
            except ValueError:
                content = str(response.get("response", "")).strip() if isinstance(response, dict) else ""
            if not thinking_text:
                t = response.get("thinking") if isinstance(response, dict) else None
                if isinstance(t, str) and t.strip():
                    thinking_text = t.strip()
        else:
            try:
                # Convert ChatResponse object to dict if needed
                if hasattr(response, "model_dump"):
                    response_dict = response.model_dump()
                elif hasattr(response, "__dict__"):
                    response_dict = dict(response)
                else:
                    response_dict = response
                thinking_text, content = self.generic_parser.parse(response_dict)
            except Exception:
                # Fallback: try object attribute access for ollama ChatResponse
                if hasattr(response, "message") and hasattr(response.message, "content"):
                    content = str(response.message.content).strip()
                elif isinstance(response, dict):
                    content = response.get("message", {}).get("content", "").strip()
                thinking_text = None

        return thinking_text, content

    def get_provider_name(self) -> str:
        return "ollama"
