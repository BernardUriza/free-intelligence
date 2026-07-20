"""HTTP client to the Container-Apps-resident Claude Agent SDK runner.

The legacy direct-Anthropic client talked to the Messages API directly: it
inlined the full conversation context + facts + disclosures as `messages[]`
blocks, then received a single-shot response. Validated 2026-05-13
(histerical-search): 1M-context recall degrades 20-40% on multi-hop
reasoning at scale.

`AgentRunnerClient` replaces that single-shot pattern with a remote call to
the FastAPI runner in the `persona-runner` Container App. The runner hosts
the Claude Agent SDK (Python) and reads selectively from
`/data/insult-workspace/*.md` (mirrored from Postgres by a background
renderer) via Read/Grep/Glob.

## Drop-in contract

Exposes the same `chat()` signature the turn pipeline expects, so
`stages.py` calls it as the single turn backend without any branch.
Returns the same `LLMResponse` dataclass.

## Auth

OAuth Max only. The runner has the credentials in
`~/.claude/.credentials.json`. The runner is reached via
`PERSONA_RUNNER_URL` with a shared bearer in
`PERSONA_RUNNER_TOKEN`. On 429 quota exhaustion the runner returns
in-character error text; the caller surfaces it normally.

## What the runner IGNORES (intentionally)

- `system_prompt`: runner reads persona.md from its own filesystem.
- `tools`: runner uses Read/Grep/Glob exclusively in Fase 2.
- `cache_breakpoints`: SDK manages its own caching.
- `tool_choice`: agent decides per turn.

## What IS preserved

- `messages[-1]['content']` becomes the agent prompt (last user text).
- `max_tokens` is forwarded only in metrics — runner uses its own cap.
- `on_timeout`: fires once after the HTTP read timeout fires the first
  time — same UX as the legacy retry_notice.
- `behavioral_guidance` (v3.9.94): the per-turn preset + vulnerability
  overlay the caller computed. Forwarded to the runner, which injects it
  into the user message (NOT the cached system prompt). This is the
  one piece of `system_prompt`'s former payload that DOES survive — it
  carries the classifier's tone decision the runner would otherwise be
  blind to. The rest of `system_prompt` (persona.md, facts) is still
  ignored because the runner reconstructs those from its own filesystem
  + Postgres.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

import httpx
import structlog

from khimeras_shared.llm.types import LLMResponse
from shared.time_context import _get_current_time_context

log = structlog.get_logger()


class AgentRunnerError(Exception):
    """Base — a turn call to the runner failed. Kept as the common base so
    existing ``except AgentRunnerError`` / ``except Exception`` catch sites
    keep working; callers that need the runner-down vs persona-turn split
    branch on the two subclasses below."""


class RunnerDownError(AgentRunnerError):
    """The runner PROCESS is unreachable: connection refused, read timeout,
    or a 5xx from the container. Insult's brain is genuinely down, so a
    sibling persona on a DIFFERENT provider/container (ALICE on Azure
    OpenAI) can legitimately take this turn — the failover is real, not an
    impersonation."""


class PersonaTurnError(AgentRunnerError):
    """The runner is UP and answered, but THIS turn was rejected: a 4xx (the
    request reached the runner and was refused) or invalid JSON. ALICE
    cannot fix a malformed / over-quota / misbehaving turn, so failing over
    to her would fabricate a 'fake ALICE'. The caller must degrade honestly
    instead of failing over (closes the 2026-06 'ALICE falsa' class)."""


def _last_user_text(messages: list[dict]) -> str:
    """Pluck the text payload of the last user message in the API-shaped list.

    Caller (stages.py) builds Anthropic-shape messages where the final entry is
    role='user'. Its content is either a plain string OR a list of blocks (text
    + image). We only return text here; images are extracted separately by
    `_last_user_attachments`.
    """
    if not messages:
        return ""
    last = messages[-1]
    content = last.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in parts if p)
    return ""


def _last_user_attachments(messages: list[dict]) -> list[dict]:
    """Extract non-text content blocks (image, document) from the final user msg.

    Returns the raw Anthropic-shaped blocks so the runner can forward them
    directly into the SDK's streaming message format. Empty list if the
    final message has no attachments or is text-only.

    Fix v3.9.43 (REWRITE-B1): previous `_last_user_text` discarded image
    blocks silently. Symptom: Alex sent text+2 images, Insult ignored
    the images entirely. The runner now receives them as a separate
    `attachments` field and inlines them into the SDK query.
    """
    if not messages:
        return []
    last = messages[-1]
    content = last.get("content", "")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get("type") in {"image", "document"}]


# How much of the prior channel conversation to replay to the runner. The
# runner DISCARDS the plumbing-built `messages[]` and keeps only PER-USER
# session state (see chat() below), so it is blind to what OTHER participants
# just said. Concrete failure (2026-06-05, #general): Bernard names the film
# "Creep" in his own message; seconds later Alex says "me dio ptsd la peli"
# WITHOUT naming it; her turn's session never saw Bernard's line, so the bot
# answers "¿cuál peli?". Replaying the tail of the SHARED channel lets
# cross-user references ("la peli", "eso", "el de antes") resolve.
_RECENT_CONTEXT_MAX_MESSAGES = 25
_RECENT_CONTEXT_MAX_CHARS = 3500


def _format_recent_context(messages: list[dict]) -> str:
    """Render the channel messages BEFORE the current one as a transcript.

    The plumbing builds `messages[]` (recent 50 + keyword-relevant) where each
    prior entry's `content` is already a speaker-prefixed string like
    "Bernard: ya terminamos". The runner ignores that list entirely, so the
    shared group conversation never reaches it. We replay the tail here so the
    runner can resolve references to what other people just said.

    Returns "" when there is nothing prior to replay.
    """
    if not messages or len(messages) <= 1:
        return ""
    tail = messages[:-1][-_RECENT_CONTEXT_MAX_MESSAGES:]
    lines: list[str] = []
    for m in tail:
        content = m.get("content", "")
        if isinstance(content, list):
            content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if isinstance(content, str) and content.strip():
            lines.append(content.strip())
    if not lines:
        return ""
    transcript = "\n".join(lines)
    if len(transcript) > _RECENT_CONTEXT_MAX_CHARS:
        # Keep the freshest tail — truncate from the front.
        transcript = "…\n" + transcript[-_RECENT_CONTEXT_MAX_CHARS:]
    return transcript


class AgentRunnerClient:
    """The turn backend — delegates each chat turn to the runner.

    Constructor takes the runner URL and bearer auth. Both come from env
    (`PERSONA_RUNNER_URL` + `PERSONA_RUNNER_TOKEN`).
    """

    def __init__(
        self,
        runner_url: str,
        runner_token: str,
        *,
        timeout_s: float = 120.0,
        connect_timeout_s: float = 10.0,
        connect_max_retries: int = 2,
        connect_retry_base_s: float = 0.25,
    ):
        if not runner_url:
            raise ValueError("AgentRunnerClient requires runner_url")
        if not runner_token:
            raise ValueError("AgentRunnerClient requires runner_token")
        self._runner_url = runner_url.rstrip("/")
        self._runner_token = runner_token
        self._timeout_s = timeout_s
        self._connect_timeout_s = connect_timeout_s
        self._connect_max_retries = connect_max_retries
        self._connect_retry_base_s = connect_retry_base_s

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        *,
        model: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
        cache_breakpoints: int = 0,
        tool_choice: str | None = None,
        on_timeout: Callable[[], Any] | None = None,
        timeout_s: float | None = None,
        channel_id: str | None = None,
        user_id: str | None = None,
        session_uuid: str | None = None,
        fallback_model: str | None = None,
        behavioral_guidance: str | None = None,
        relevant_memory: str | None = None,
        other_people: str | None = None,
        persona_id: str | None = None,
    ) -> LLMResponse:
        _ = (system_prompt, tools, max_tokens, cache_breakpoints, tool_choice, model, fallback_model)

        user_text = _last_user_text(messages)
        attachments = _last_user_attachments(messages)
        if not user_text and not attachments:
            log.warning("agent_runner_client_empty_user_text", message_count=len(messages))
            return LLMResponse(text="", model_used="agent-runner", stop_reason="empty_input")

        # v4.3.0: prepend deterministically pre-fetched history (deep_memory
        # auto-retrieval) so the agent ALWAYS sees relevant past context
        # instead of relying on the opt-in `deep_memory` tool (which fired on
        # ~1% of turns). Framed as a labeled block so the agent reads it as
        # retrieved context, not as the user's own words. The STORED message is
        # unaffected — storage runs upstream, before this call.
        effective_user_text = user_text or "[adjuntó solo imagen]"
        # The runner DISCARDS `system_prompt` and rebuilds persona + the AUTHOR's
        # facts from its own filesystem (via the user_id it gets). But facts about
        # OTHER channel participants only live in the plumbing-built system_prompt,
        # so without this the runner is blind to them: it could recall Alex when
        # Alex spoke (her user_id) yet answer "no me lo has contado" when Bernard
        # asked ABOUT Alex. Inject the pre-built "Other People" block into the
        # user_text the runner DOES read — same mechanism as relevant_memory, no
        # runner change needed. (2026-06-03 second-layer fix.)
        prefix_blocks: list[str] = []
        # Wall-clock time is SSOT'd in shared.time_context but only ever reached
        # the plumbing-built system_prompt — which the runner DISCARDS under
        # LEGACY=false. So NEITHER Insult NOR the siblings knew the date/time
        # (Frugívoro built a weekly menu saying "domingo prep" on a Wednesday).
        # Same class of loss as `other_people`; same fix: forward it as a
        # dynamic prefix_block on the user_text every persona's runner DOES read.
        # Goes FIRST + never cached (changes every minute — must not sit in a
        # cacheable region). One seam, all personas inherit it. (2026-07-08.)
        prefix_blocks.append(f"<current_time>\n{_get_current_time_context()} — America/Mexico_City\n</current_time>")
        if relevant_memory:
            prefix_blocks.append(f"<relevant_memory>\n{relevant_memory}\n</relevant_memory>")
        if other_people:
            prefix_blocks.append(f"<other_people_in_channel>\n{other_people}\n</other_people_in_channel>")
        # The shared channel conversation the runner would otherwise never see
        # (it only reads the last user message + its own per-user session).
        # Goes LAST among the prefix blocks — closest to the current message —
        # so it reads as the live thread, not as background memory.
        recent_context = _format_recent_context(messages)
        if recent_context:
            prefix_blocks.append(
                "<recent_conversation>\n"
                "Lo que se acaba de decir en este canal (incluye a otras personas). "
                'Úsalo para resolver referencias como "la peli", "eso", "el de antes" — '
                "NO vuelvas a preguntar qué es algo que ya se nombró aquí.\n"
                f"{recent_context}\n</recent_conversation>"
            )
            log.info("agent_runner_client_recent_context_forwarded", context_chars=len(recent_context))
        if prefix_blocks:
            effective_user_text = "\n\n".join([*prefix_blocks, effective_user_text])

        payload: dict[str, Any] = {
            "channel_id": channel_id or "0",
            "user_id": user_id or "0",
            "user_text": effective_user_text,
        }
        # Khimeras multi-persona: tell the runner which sibling persona answers.
        # Omitted for Insult (None) so the payload + runner behavior are unchanged.
        if persona_id:
            payload["persona_id"] = persona_id
        if attachments:
            payload["attachments"] = attachments
            log.info(
                "agent_runner_client_attachments_forwarded",
                count=len(attachments),
                types=[a.get("type") for a in attachments],
            )
        # v3.9.94: forward the per-turn behavioral guidance (preset +
        # vulnerability overlay) the caller computed. The runner injects it
        # into the user message so persona.md's tone is modulated per turn
        # again — closing the gap where the classifier's decision (e.g.
        # RESPECTFUL_SERIOUS / vulnerability overlay) was computed and then
        # discarded with `system_prompt`.
        if behavioral_guidance:
            payload["behavioral_guidance"] = behavioral_guidance
            log.info(
                "agent_runner_client_guidance_forwarded",
                guidance_chars=len(behavioral_guidance),
            )
        if relevant_memory:
            log.info(
                "agent_runner_client_memory_forwarded",
                memory_chars=len(relevant_memory),
            )
        if session_uuid:
            payload["session_uuid"] = session_uuid

        # A per-turn read-timeout override (the arbiter's time budget for THIS
        # task) supersedes the fixed default. The connect timeout stays constant
        # — connecting has nothing to do with how long the task itself may run.
        effective_timeout_s = timeout_s if timeout_s is not None else self._timeout_s
        timeout = httpx.Timeout(effective_timeout_s, connect=self._connect_timeout_s)
        headers = {
            "Authorization": f"Bearer {self._runner_token}",
            "Content-Type": "application/json",
        }
        url = f"{self._runner_url}/v1/turn"
        start = time.monotonic()
        timed_out_once = False

        # ConnectTimeout / ConnectError happen BEFORE the request body is sent,
        # so the turn provably never reached the runner — re-POSTing is safe (no
        # duplicate turn). A single transient ConnectTimeout to an alive-but-idle
        # runner used to be turned straight into RunnerDownError, summoning ALICE
        # (who never receives the image and answers blind). Retry the connect a
        # few times before declaring the brain down. ReadTimeout is NOT retried:
        # the request may have landed and be processing, so a re-POST would
        # double-spend the turn.
        attempts = self._connect_max_retries + 1
        resp = None
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                break
            except (httpx.ConnectTimeout, httpx.ConnectError) as e:
                if attempt + 1 < attempts:
                    log.warning(
                        "agent_runner_client_connect_retry",
                        attempt=attempt + 1,
                        of=attempts,
                        error_type=type(e).__name__,
                        elapsed_ms=int((time.monotonic() - start) * 1000),
                    )
                    await asyncio.sleep(self._connect_retry_base_s * (2**attempt))
                    continue
                log.error(
                    "agent_runner_client_connect_exhausted",
                    attempts=attempts,
                    error_type=type(e).__name__,
                    elapsed_ms=int((time.monotonic() - start) * 1000),
                )
                # Unreachable across every connect attempt → the runner process
                # is genuinely down. RunnerDownError so failover is allowed.
                raise RunnerDownError(
                    f"runner unreachable after {attempts} connect attempts: {type(e).__name__}"
                ) from e
            except httpx.ReadTimeout as e:
                if on_timeout and not timed_out_once:
                    timed_out_once = True
                    try:
                        maybe = on_timeout()
                        if hasattr(maybe, "__await__"):
                            await maybe
                    except Exception:
                        log.exception("agent_runner_on_timeout_callback_failed")
                log.warning(
                    "agent_runner_client_timeout",
                    elapsed_ms=int((time.monotonic() - start) * 1000),
                    user_id=user_id,
                    channel_id=channel_id,
                )
                # A read timeout means the runner never answered — treat the brain
                # as down so a real sibling persona can take the turn.
                raise RunnerDownError(f"runner read timeout after {effective_timeout_s}s") from e
            except httpx.HTTPError as e:
                log.exception(
                    "agent_runner_client_http_error",
                    error_type=type(e).__name__,
                    elapsed_ms=int((time.monotonic() - start) * 1000),
                )
                # Other transport error (DNS, protocol) → the runner is
                # unreachable. RunnerDownError so failover is allowed.
                raise RunnerDownError(f"runner http error: {type(e).__name__}: {e}") from e

        # The loop either breaks with resp assigned or raises; reaching here
        # without a response is impossible (attempts >= 1).
        assert resp is not None

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code >= 500:
            log.error(
                "agent_runner_client_5xx",
                status=resp.status_code,
                body_preview=resp.text[:200],
                elapsed_ms=elapsed_ms,
            )
            # 5xx = the container is failing to serve. Brain down → failover OK.
            raise RunnerDownError(f"runner {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            log.error(
                "agent_runner_client_4xx",
                status=resp.status_code,
                body_preview=resp.text[:200],
                elapsed_ms=elapsed_ms,
            )
            # 4xx = the runner received and REJECTED this turn (the brain is
            # alive). A sibling persona can't fix a bad request → degrade
            # honestly, never a fake-ALICE failover.
            raise PersonaTurnError(f"runner {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
        except ValueError as e:
            log.exception("agent_runner_client_invalid_json", body_preview=resp.text[:200])
            # The runner answered but emitted garbage — it's reachable but
            # broken. Surface it as a persona-turn error so it's NOT masked by
            # a sibling failover; this is a bug to SEE, not to paper over.
            raise PersonaTurnError("runner returned invalid JSON") from e

        text = data.get("text", "") or ""
        log.info(
            "agent_runner_client_turn_complete",
            text_len=len(text),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            model=data.get("model", ""),
            stop_reason=data.get("stop_reason", ""),
            tool_calls=len(data.get("tool_calls", []) or []),
            session_uuid=data.get("session_uuid"),
            elapsed_ms=elapsed_ms,
        )

        # TEXT NO MODEL EVER GENERATED. A real generation always spends output
        # tokens; text with zero of them came from the SDK itself — an auth
        # failure, a quota wall, a transport error rendered as prose. Returning
        # it delivers a raw vendor string to Discord: on 2026-07-19 a revoked
        # OAuth token made every persona answer
        # "Failed to authenticate. API Error: 401 ..." — in English, with the
        # version tag appended — for 4.5 hours, into a conversation between two
        # real people, while /health, the 200s and `turn_complete` all stayed
        # green. `input_tokens` is NOT the signal (cache reads legitimately
        # report 0); output_tokens is, because generated text cannot be free.
        #
        # Raise instead of return, exactly like the invalid-JSON case above: the
        # gateway's turn guard already degrades to an in-character "…" and logs
        # it. Same class — reachable but broken — so it must be SEEN, not spoken.
        # Only an EXPLICIT zero accuses. A missing field means the runner never
        # reported usage (an older build, a different shape) — unknown, and
        # unknown must not silence a real answer.
        output_tokens = data.get("output_tokens")
        returned_tool_calls = data.get("tool_calls") or []
        if text.strip() and output_tokens == 0 and not returned_tool_calls:
            log.error(
                "agent_runner_client_zero_generation",
                text_preview=text[:120],
                model=data.get("model", ""),
                stop_reason=data.get("stop_reason", ""),
                session_uuid=data.get("session_uuid"),
            )
            raise PersonaTurnError(f"runner returned text with no generation: {text[:120]}")

        return LLMResponse(
            text=text,
            tool_calls=[],
            model_used=data.get("model", "agent-runner"),
            stop_reason=data.get("stop_reason", ""),
        )

    async def health(self) -> dict[str, Any]:
        """Probe the runner's /health endpoint."""
        timeout = httpx.Timeout(10.0, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self._runner_url}/health")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            return {"status": "unreachable", "error": f"{type(e).__name__}: {e}"}
