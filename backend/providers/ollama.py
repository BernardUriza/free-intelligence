"""
Free Intelligence - Ollama Provider

Local Ollama adapter (local-only, timeout controls, hash tracking).

File: backend/providers/ollama.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001

Features:
- Local-only execution (rejects external hosts)
- Timeout: 8s max per request
- Retry: 1 attempt
- Hash tracking: SHA-256 of prompt
- Redacts long prompts in logs (>800 chars → 120 chars preview)
"""

import hashlib
import time
from collections.abc import Iterator
from typing import Optional
from urllib.parse import urlparse

import requests

from backend.llm_adapter import (LLMAdapter, LLMBudget, LLMProviderError,
                                 LLMRequest, LLMResponse)
from backend.logger import get_logger
from backend.policy_enforcer import PolicyViolation, get_policy_enforcer
from backend.utils.token_counter import TokenCounter

logger = get_logger(__name__)
policy = get_policy_enforcer()


class OllamaAdapter(LLMAdapter):
    """
    Ollama local LLM adapter.

    Features:
    - Local-only (http://127.0.0.1:11434)
    - Timeout: 8s max
    - Retry: 1 attempt
    - No streaming in v1
    - Hash tracking for prompts
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct-q4_0",
        budget: Optional[LLMBudget] = None,
        max_retries: int = 3,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 8,
        token_counter: Optional[TokenCounter] = None,
        base_delay_ms: int = 100,
        max_delay_ms: int = 1000,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_window: int = 60,
    ):
        super().__init__(
            provider_name="ollama",
            model=model,
            budget=budget,
            max_retries=max_retries,
        )
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        # Inject token counter (create default if not provided)
        self.token_counter = token_counter or TokenCounter()
        # Retry backoff configuration
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        # Circuit breaker: track failures in time window
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_window = circuit_breaker_window
        self.failure_timestamps: list[float] = []

        # Validate local-only host
        parsed = urlparse(base_url)
        if parsed.hostname not in ["127.0.0.1", "localhost"]:
            raise ValueError(
                f"OllamaAdapter only accepts local hosts (127.0.0.1 or localhost). Got: {parsed.hostname}"
            )

        logger.info(
            "OLLAMA_ADAPTER_INIT",
            model=self.model,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
        )

    def _record_failure(self):
        """Record a failure timestamp for circuit breaker."""
        self.failure_timestamps.append(time.time())

    def _is_circuit_open(self) -> bool:
        """
        Check if circuit breaker is open (too many failures).

        Returns:
            True if circuit is open (should reject requests)
        """
        now = time.time()
        # Remove old failures outside the window
        self.failure_timestamps = [
            ts for ts in self.failure_timestamps if now - ts < self.circuit_breaker_window
        ]
        # Check if we've exceeded threshold
        return len(self.failure_timestamps) >= self.circuit_breaker_threshold

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from local Ollama.

        Args:
            request: LLM request with prompt and parameters

        Returns:
            LLM response with text, usage, latency, hash

        Raises:
            LLMProviderError: If Ollama fails or times out or circuit is open
        """
        # Check circuit breaker first
        if self._is_circuit_open():
            logger.error(
                "OLLAMA_CIRCUIT_OPEN",
                provider=self.provider_name,
                failures_in_window=len(self.failure_timestamps),
                threshold=self.circuit_breaker_threshold,
            )
            raise LLMProviderError(
                f"Circuit breaker open: {len(self.failure_timestamps)} failures in last {self.circuit_breaker_window}s"
            )

        start_time = time.time()

        # Calculate prompt hash
        prompt_content = f"{request.prompt}|{request.system_prompt or ''}"
        prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()

        # Redact long prompts in logs
        prompt_preview = request.prompt
        if len(request.prompt) > 800:
            prompt_preview = request.prompt[:120] + "... [REDACTED]"

        logger.info(
            "OLLAMA_REQUEST_STARTED",
            provider=self.provider_name,
            model=self.model,
            prompt_preview=self.redact_phi(prompt_preview),
            prompt_hash=prompt_hash[:16],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        # Build Ollama request payload (API v0.12+ uses /api/chat with messages format)
        messages = [{"role": "user", "content": request.prompt}]

        # Add system prompt if provided
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        # Retry logic
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Policy: Check egress (Ollama is local so should pass, but checked for consistency)
                try:
                    policy.check_egress(
                        f"{self.base_url}/api/chat",
                        run_id=request.metadata.get("interaction_id") if request.metadata else None,
                    )
                except PolicyViolation as e:
                    logger.error(
                        "EGRESS_BLOCKED", provider="ollama", url=self.base_url, error=str(e)
                    )
                    raise LLMProviderError(f"API call blocked by policy: {e}")

                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()

                # Parse response (API v0.12+ format)
                data = response.json()
                text = data.get("message", {}).get("content", "")

                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)

                # Estimate tokens using injected counter
                input_tokens = self.token_counter.estimate_tokens(request.prompt)
                output_tokens = self.token_counter.estimate_tokens(text)
                tokens_used = input_tokens + output_tokens

                # Build response
                llm_response = LLMResponse(
                    content=text,
                    provider=self.provider_name,
                    model=self.model,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    finish_reason="stop",
                    metadata={
                        "prompt_hash": prompt_hash,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "done": data.get("done", True),
                    },
                )

                logger.info(
                    "OLLAMA_REQUEST_COMPLETED",
                    provider=self.provider_name,
                    model=self.model,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    prompt_hash=prompt_hash[:16],
                )

                return llm_response

            except requests.exceptions.Timeout as e:
                last_error = e
                self._record_failure()
                logger.warning(
                    "OLLAMA_REQUEST_TIMEOUT",
                    provider=self.provider_name,
                    model=self.model,
                    attempt=attempt + 1,
                    timeout_seconds=self.timeout_seconds,
                )

            except requests.exceptions.RequestException as e:
                last_error = e
                self._record_failure()
                logger.warning(
                    "OLLAMA_REQUEST_RETRY",
                    provider=self.provider_name,
                    model=self.model,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                )

            except Exception as e:
                last_error = e
                self._record_failure()
                logger.warning(
                    "OLLAMA_REQUEST_ERROR",
                    provider=self.provider_name,
                    model=self.model,
                    attempt=attempt + 1,
                    error=str(e),
                )

            # Exponential backoff with configurable limits
            if attempt < self.max_retries:
                delay_ms = min(self.base_delay_ms * (2**attempt), self.max_delay_ms)
                time.sleep(delay_ms / 1000.0)  # Convert ms to seconds

        # All retries failed
        logger.error(
            "OLLAMA_REQUEST_FAILED",
            provider=self.provider_name,
            model=self.model,
            error=str(last_error),
        )
        raise LLMProviderError(
            f"Ollama API failed after {self.max_retries + 1} attempts: {last_error}"
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """
        Stream response (NOT IMPLEMENTED in v1).

        Raises:
            NotImplementedError: Streaming not supported in v1
        """
        raise NotImplementedError("Ollama streaming not supported in v1. Use generate() instead.")
