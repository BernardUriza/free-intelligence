"""Azure OpenAI client for ALICE.

GPT-4.1 only, served from the shared `insult-openai` cognitive account.
No router, no provider switching — that's the deliberate choice (see
project_alice_v0_1_0.md). Insult is Anthropic-only, AURITY is Qwen-only,
ALICE is GPT-4.1-only. Composability of three specialists, not one
Frankenbot. Reusing Insult's Azure cognitive resource means one Azure
factura instead of a second OpenAI Inc. account.

Retry policy mirrors Insult's `llm/retry.py` because the lessons learned
there (Full Jitter, honor retry-after, cap timeout retries at 2) are
provider-agnostic and battle-tested in prod.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any

import openai
import structlog
from openai import APIConnectionError, APITimeoutError, AsyncAzureOpenAI, RateLimitError

from alice.config import settings

log = structlog.get_logger()


# Caps borrowed from Insult: more than 2 timeout retries leaves the user
# staring at dead air for a minute; better to fail fast and surface the
# error than make them wait silently. Five would be Discord-message-edit
# territory.
_MAX_TIMEOUT_RETRIES = 2
_MAX_RATE_LIMIT_RETRIES = 5
_MAX_BACKOFF_SECONDS = 30.0


@dataclass(frozen=True)
class LLMResponse:
    """ALICE's response after token accounting + cost calc.

    Same shape as Insult's `LLMResponse` so the audit/observability code
    paths can stay parallel between the two bots if we ever unify them.
    """

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str | None
    latency_ms: int


class AliceLLMClient:
    """Async Azure OpenAI client with retry hygiene.

    Built around `openai.AsyncAzureOpenAI` directly (not LiteLLM, not a
    router) so the request/response path is one hop from ALICE to Azure
    OpenAI. The `/histerical-search` of 2026-05-13 found that LiteLLM had
    800+ open issues and a measurable P95 latency ceiling; we skip the
    gateway tax.

    `model` here is the Azure *deployment* name (not the literal model
    name). For the `insult-openai` account the deployment is `gpt-4.1`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
        max_tokens: int | None = None,
        timeout_s: float | None = None,
    ):
        self.api_key = api_key or settings.azure_openai_key
        self.endpoint = endpoint or settings.azure_openai_endpoint
        self.model = deployment or settings.azure_openai_gpt_deployment
        self.api_version = api_version or settings.azure_openai_api_version
        self.max_tokens = max_tokens or settings.openai_max_tokens
        self.timeout_s = timeout_s or settings.openai_timeout_seconds

        # `max_retries=0` because we own the retry loop below. The SDK's
        # internal retries (default 2) would silently triple our timeout
        # budget — same trap Insult fell into with Anthropic's SDK.
        self._client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            max_retries=0,
        )

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a chat completion request with retry.

        `messages` is OpenAI-shaped: list of `{"role": "...", "content": "..."}`.
        The caller is responsible for assembling history; ALICE doesn't
        try to be clever about token-budgeting because the caller (the
        Discord cog or `/invite` handler) already pulled a bounded window
        from Postgres.
        """
        body_messages = [{"role": "system", "content": system_prompt}, *messages]
        params: dict[str, Any] = {
            "model": model or self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": body_messages,
            "timeout": self.timeout_s,
        }

        rate_limit_attempt = 0
        timeout_attempt = 0
        start = time.monotonic()
        while True:
            try:
                resp = await self._client.chat.completions.create(**params)
                choice = resp.choices[0]
                latency_ms = int((time.monotonic() - start) * 1000)
                log.info(
                    "alice_llm_response",
                    model=resp.model,
                    input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                    output_tokens=resp.usage.completion_tokens if resp.usage else 0,
                    latency_ms=latency_ms,
                    stop_reason=choice.finish_reason,
                )
                return LLMResponse(
                    text=choice.message.content or "",
                    model=resp.model,
                    input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                    output_tokens=resp.usage.completion_tokens if resp.usage else 0,
                    stop_reason=choice.finish_reason,
                    latency_ms=latency_ms,
                )

            except RateLimitError as e:
                rate_limit_attempt += 1
                if rate_limit_attempt > _MAX_RATE_LIMIT_RETRIES:
                    log.error("alice_llm_rate_limit_exhausted", attempt=rate_limit_attempt)
                    raise
                # Honor retry-after header if present (Vercel AI SDK issue
                # #7247 documented as anti-pattern when you ignore it).
                retry_after_s = _parse_retry_after(e)
                wait = retry_after_s if retry_after_s is not None else _full_jitter(rate_limit_attempt)
                log.warning(
                    "alice_llm_rate_limit_retry",
                    attempt=rate_limit_attempt,
                    wait_seconds=round(wait, 2),
                    retry_after_honored=retry_after_s is not None,
                )
                await asyncio.sleep(wait)

            except APITimeoutError:
                timeout_attempt += 1
                if timeout_attempt > _MAX_TIMEOUT_RETRIES:
                    log.error("alice_llm_timeout_exhausted", attempt=timeout_attempt)
                    raise
                log.warning("alice_llm_timeout_retry", attempt=timeout_attempt)
                await asyncio.sleep(1.0)  # short fixed delay; full jitter overkill here

            except APIConnectionError as e:
                # Network blip — single retry with backoff, then bail. We
                # don't want to mask sustained outages from the caller.
                if timeout_attempt > 0:
                    log.error("alice_llm_connection_error_after_retry", error=str(e))
                    raise
                timeout_attempt += 1
                log.warning("alice_llm_connection_error_retry", error=str(e))
                await asyncio.sleep(2.0)

            except openai.AuthenticationError:
                # No point retrying — the key is wrong. Surface immediately
                # so the operator fixes it instead of looping silently.
                log.exception("alice_llm_auth_failed")
                raise


def _full_jitter(attempt: int) -> float:
    """AWS-standard Full Jitter backoff.

    Marc Brooker's 2022 jitter paper (referenced in Insult's robustness
    rules) is the canonical source. Pure exponential without jitter
    produces thundering-herd retry storms.
    """
    cap = min(2**attempt, _MAX_BACKOFF_SECONDS)
    return random.uniform(0, cap)


def _parse_retry_after(err: RateLimitError) -> float | None:
    """Extract the `retry-after` header from a 429 response.

    OpenAI returns it as seconds (integer or float). Returns None if the
    header is missing or unparseable — caller falls back to jittered
    backoff.
    """
    try:
        response = getattr(err, "response", None)
        if response is None:
            return None
        header = response.headers.get("retry-after")
        if header is None:
            return None
        val = float(header)
        # Sanity cap: ignore absurd values that would freeze the bot.
        if val < 0 or val > 60:
            return None
        return val
    except (ValueError, AttributeError, TypeError):
        return None
