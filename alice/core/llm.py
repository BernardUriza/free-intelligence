"""ALICE's LLM path — OpenAI Codex over the shared Azure OpenAI deployment.

GPT-4.1, served from the shared `insult-openai` cognitive account, driven through
the OpenAI Codex agent harness via `fi_runner.CodexBackend` instead of a direct
`AsyncAzureOpenAI` call.

This is NOT a Frankenbot — it is the "composability of specialists" philosophy
realized, not violated. ALICE stays THIN: this module only maps the chat contract
onto `fi_runner` and reads back a token-accounted `LLMResponse`. All the harness
mechanics (subprocess, MCP wiring, retry, usage/session parsing) live in the
SHARED core (`fi_runner` + `fi-core`), not inside ALICE. A Frankenbot would be one
fat bot that owns all that logic itself; here three thin specialists (Insult,
ALICE, AURITY) each compose over one shared core. Mounting fi-core's cognitive
server later is the same move — capability borrowed from the core, never bolted
into ALICE.

It deliberately OVERRIDES the original "no router, one hop, GPT-4.1-only" decision
(project_alice_v0_1_0.md): we trade a little latency (codex spawns a subprocess +
runs the agent loop) for the agentic harness — tool use + MCP + built-in
retry/usage/session. Endpoint and deployment are unchanged (same Azure factura,
same GPT-4.1).

Not a regression on the LLMResponse contract: codex reports token usage
(`turn.completed.usage`), retries with exponential backoff internally, and
supports session resume — it adds capability on top of the old direct call.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import structlog
from fi_runner import CodexBackend, PermissionMode, RetryPolicy, Runner, ToolPolicy, antidrift_guard, packs

from alice.config import settings

log = structlog.get_logger()


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
    """ALICE's LLM client — Codex harness over the shared Azure OpenAI deployment.

    Routes through `fi_runner.CodexBackend` pointed at the existing Azure OpenAI
    endpoint (`model_provider=azure`, Responses wire API). `model` here is the
    Azure *deployment* name (GPT-4.1 for the `insult-openai` account). The Azure
    key is bridged into `AZURE_OPENAI_API_KEY` so the `codex` subprocess can read
    it; Codex owns retry (exponential backoff), so we don't wrap our own loop.
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

        # Codex reads the key from an env var (its `env_key`). ALICE holds it as a
        # value (settings.azure_openai_key → AZURE_OPENAI_KEY), so bridge it to the
        # name Codex expects. setdefault: don't clobber an explicitly-set one.
        self._key_env = "AZURE_OPENAI_API_KEY"
        if self.api_key:
            os.environ.setdefault(self._key_env, self.api_key)

        # One stateless backend, reused across turns. Pointed at the SAME Azure
        # endpoint — no ChatGPT subscription, just the deployment + key.
        self._backend = CodexBackend(
            default_model=self.model,
            azure_endpoint=self.endpoint,
            azure_api_key_env=self._key_env,
        )

        # Anti-drift guard (fi_runner, backed by fi-core.persona): the presence
        # layer talks TO the patient, so it must not break the ALICE persona. Uses
        # the universal AI-disclosure packs; tune with ALICE-specific patterns
        # later. Paired with retry below — fi_runner re-runs the turn on a break.
        self._antidrift = antidrift_guard(
            break_patterns=packs.GENERIC_AI_DISCLOSURE_EN + packs.GENERIC_AI_DISCLOSURE_ES,
            reinforcement=(
                "You broke character by disclosing you are an AI/assistant/language "
                "model. Do NOT reveal that. Rewrite your reply staying fully in "
                "character as ALICE."
            ),
        )

    @staticmethod
    def _flatten(messages: list[dict[str, str]]) -> str:
        """Flatten OpenAI-shaped history into the single prompt `codex exec` takes.

        `codex exec` accepts one PROMPT arg, so we render the bounded window the
        caller already pulled from Postgres as a `role: content` transcript. The
        persona (system prompt) is prepended by the backend, not here.
        """
        return "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,  # kept for signature parity; codex caps via model config
    ) -> LLMResponse:
        """Send a chat turn through the Codex harness, return a token-accounted result.

        `messages` is OpenAI-shaped: list of `{"role": "...", "content": "..."}`.
        The caller assembles history (a bounded window from Postgres); we flatten
        it into the codex prompt. Two layers of retry, orthogonal: Codex retries
        API/network errors internally; the runner retries a PERSONA BREAK (the
        anti-drift guard) by re-running the turn with reinforcement, sanitizing on
        the final attempt. A hard API failure still surfaces as RuntimeError.
        """
        chosen_model = model or self.model
        runner = Runner(
            backend=self._backend,
            persona=system_prompt,
            guards=[self._antidrift],
            retry_policy=RetryPolicy(max_attempts=2),
            tool_policy=ToolPolicy(permission_mode=PermissionMode.DEFAULT),
            model=chosen_model,
        )
        start = time.monotonic()
        result = await runner.run(self._flatten(messages))
        latency_ms = int((time.monotonic() - start) * 1000)

        usage = result.usage or {}
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        log.info(
            "alice_llm_response",
            model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            backend="codex",
            session_id=result.session_id,
        )
        return LLMResponse(
            text=result.text,
            model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason="stop",
            latency_ms=latency_ms,
        )
