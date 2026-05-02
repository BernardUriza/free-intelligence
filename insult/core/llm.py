"""Claude API client with character break detection and tool_use support."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import anthropic
import structlog
from anthropic.types import MessageParam

from insult.core.actions import ToolCall
from insult.core.character import (
    CACHE_BOUNDARY,
    CHARACTER_REINFORCEMENT,
    CONTEXT_REINFORCEMENT,
    detect_anti_patterns,
    detect_break,
    detect_clarification_dump,
    normalize_formatting,
    sanitize,
    strip_lists,
    strip_metadata,
)

log = structlog.get_logger()

# --- Token usage tracking (in-memory, resets on redeploy) ---
# Pricing per million tokens, per model family (as of 2026-04).
# Keys are the family tag returned by _resolve_family(); Sonnet is the
# fallback for unknown models (conservative — overestimates Haiku slightly
# but never understates Opus which would mask a blown budget).
_PRICING: dict[str, dict[str, float]] = {
    "haiku": {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_create": 1.25},
    "sonnet": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_create": 3.75},
    "opus": {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_create": 18.75},
}
_DEFAULT_FAMILY = "sonnet"

# Timeouts are capped separately from other retries. Each timeout is ~30s of
# dead air, so five would leave the user staring at nothing for 2+ minutes.
_MAX_TIMEOUT_RETRIES = 2


def _resolve_family(model: str) -> str:
    """Map a full model id to its pricing family.

    claude-haiku-4-5-20251001 → 'haiku', claude-sonnet-4-6 → 'sonnet', etc.
    Unknown models default to Sonnet (conservative — overestimates Haiku
    slightly but never understates Opus, which would hide a blown budget).
    """
    lower = model.lower()
    for family in _PRICING:
        if family in lower:
            return family
    return _DEFAULT_FAMILY


def _zero_bucket() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_create_tokens": 0, "requests": 0}


# Per-family token counters. Keys populated lazily as families are seen.
_usage_by_family: dict[str, dict[str, int]] = {}
_errors_total = 0

# Anti-pattern fallback threshold: number of pattern hits that triggers a
# rerun against the fallback model. Below this the hit is only logged.
_ANTI_PATTERN_FALLBACK_THRESHOLD = 2


def record_usage(
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_create: int = 0,
    model: str = "",
) -> None:
    """Accumulate token usage for cost tracking, keyed by model family."""
    family = _resolve_family(model) if model else _DEFAULT_FAMILY
    bucket = _usage_by_family.setdefault(family, _zero_bucket())
    bucket["input_tokens"] += input_tokens
    bucket["output_tokens"] += output_tokens
    bucket["cache_read_tokens"] += cache_read
    bucket["cache_create_tokens"] += cache_create
    bucket["requests"] += 1


def _record_error() -> None:
    global _errors_total
    _errors_total += 1


def get_usage_report() -> dict:
    """Return accumulated usage with estimated cost in USD, broken out per family."""
    per_family: dict[str, dict] = {}
    total_tokens_in = 0
    total_tokens_out = 0
    total_cache_read = 0
    total_cache_create = 0
    total_requests = 0
    total_cost = 0.0

    for family, bucket in _usage_by_family.items():
        pricing = _PRICING.get(family, _PRICING[_DEFAULT_FAMILY])
        cost_input = (bucket["input_tokens"] / 1_000_000) * pricing["input"]
        cost_output = (bucket["output_tokens"] / 1_000_000) * pricing["output"]
        cost_cache_read = (bucket["cache_read_tokens"] / 1_000_000) * pricing["cache_read"]
        cost_cache_create = (bucket["cache_create_tokens"] / 1_000_000) * pricing["cache_create"]
        family_cost = cost_input + cost_output + cost_cache_read + cost_cache_create

        per_family[family] = {
            "tokens": dict(bucket),
            "cost_usd": round(family_cost, 4),
        }

        total_tokens_in += bucket["input_tokens"]
        total_tokens_out += bucket["output_tokens"]
        total_cache_read += bucket["cache_read_tokens"]
        total_cache_create += bucket["cache_create_tokens"]
        total_requests += bucket["requests"]
        total_cost += family_cost

    return {
        "tokens": {
            "input": total_tokens_in,
            "output": total_tokens_out,
            "cache_read": total_cache_read,
            "cache_create": total_cache_create,
            "total": total_tokens_in + total_tokens_out,
        },
        "requests": total_requests,
        "errors": _errors_total,
        "cost_usd": {"total": round(total_cost, 4)},
        "per_family": per_family,
        "avg_tokens_per_request": round((total_tokens_in + total_tokens_out) / max(total_requests, 1)),
        "note": "Resets on redeploy. Pricing is per-family (haiku/sonnet/opus); unknown models default to sonnet rates.",
    }


@dataclass
class LLMResponse:
    """Structured response from the LLM — text + optional tool calls."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model_used: str = ""  # populated by chat() — reflects the model that actually produced the text


# Web search tool definition — Claude's native server-side search.
#
# Two variants:
#   - WEB_SEARCH_TOOL: general-purpose, any domain. Used outside of
#     clinical/safety contexts.
#   - MEDICAL_WEB_SEARCH_TOOL: constrained to authoritative medical sources
#     and localized to Mexico. Used when the user is flagged as vulnerable
#     or the preset is RESPECTFUL_SERIOUS so that the bot cannot cite a
#     random wellness blog about quetiapine dosing. See APA Health Advisory
#     and MIND-SAFE framework references in vulnerability.py.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
}

MEDICAL_WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
    "allowed_domains": [
        "medlineplus.gov",  # NIH patient-facing drug + condition info (Spanish + English)
        "cima.aemps.es",  # AEMPS CIMA — Spanish regulatory drug leaflets (prospectos + fichas técnicas)
        "nih.gov",  # National Institutes of Health
        "nimh.nih.gov",  # National Institute of Mental Health
        "who.int",  # World Health Organization
        "salud.gob.mx",  # Mexican Secretaría de Salud
    ],
    "user_location": {
        "type": "approximate",
        "country": "MX",
        "timezone": "America/Mexico_City",
    },
}


def _build_system_blocks(system_prompt: str) -> list[dict] | str:
    """Build Anthropic system blocks with prompt caching on the stable prefix.

    If `system_prompt` contains the CACHE_BOUNDARY marker, split it into a
    cacheable stable block (everything before the marker, with
    cache_control=ephemeral) and a dynamic block (everything after, no cache).
    If the marker is absent, return the raw string (backwards compatible with
    callers that don't mark a boundary — e.g., simple utility calls).
    """
    if CACHE_BOUNDARY not in system_prompt:
        return system_prompt

    stable, dynamic = system_prompt.split(CACHE_BOUNDARY, 1)
    stable = stable.rstrip()
    dynamic = dynamic.lstrip()

    if not stable:
        return dynamic or system_prompt

    blocks: list[dict] = [
        {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}},
    ]
    if dynamic:
        blocks.append({"type": "text", "text": dynamic})
    return blocks


def _parse_response_content(content: list) -> LLMResponse:
    """Extract text and tool_use blocks from Claude API response content.

    Handles standard text, tool_use (channel creation), and server-side
    blocks (web_search server_tool_use / web_search_tool_result) which
    are processed transparently by the API — we just skip them.
    """
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []

    for block in content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))
        # server_tool_use and web_search_tool_result are handled server-side
        # by Claude — we just skip them in parsing

    return LLMResponse(text="\n".join(text_parts).strip(), tool_calls=tool_calls)


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        timeout: float = 30.0,
        max_retries: int = 5,
        cure_model: str = "",
    ):
        # max_retries=0 so the SDK does NOT retry internally — our outer loop
        # owns retry policy. Without this, SDK retries ~2x under the hood turn
        # our configured 30s timeout into ~90s per observed attempt.
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=0)
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.cure_model = cure_model  # Haiku model for language cure (step 7c)

    async def _send(
        self,
        system_prompt: str,
        messages: list[MessageParam],
        *,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        model: str | None = None,
        on_timeout: Callable[[], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Raw API call with retry logic for transient errors.

        `model` overrides self.model for this call only (used by the 3-tier
        router to route per-turn). Defaults to self.model when None.

        `on_timeout` is awaited once after the FIRST timeout so callers can
        notify the user that we're retrying (keeps the UX honest instead of
        silent dead air).
        """
        if self.max_retries < 1:
            raise ValueError(f"max_retries must be >= 1, got {self.max_retries}")

        effective_model = model or self.model

        last_error: Exception | None = None
        attempt = 0
        timeout_count = 0
        # kwargs is initialized per-iteration inside the loop, but we bind it
        # here so the BadRequestError fallback (`kwargs.pop("tools")`) can never
        # reference an unbound name even under exotic control flow.
        kwargs: dict = {}

        for attempt in range(1, self.max_retries + 1):
            try:
                log.info("llm_request", model=effective_model, attempt=attempt, messages=len(messages))
                kwargs = {
                    "model": effective_model,
                    "max_tokens": self.max_tokens,
                    "system": _build_system_blocks(system_prompt),
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools
                    if tool_choice:
                        kwargs["tool_choice"] = tool_choice

                # Use streaming transport + .get_final_message() instead of
                # .messages.create(). Anthropic explicitly recommends streaming
                # for long-running requests (see Errors doc § Long requests and
                # the 504 timeout_error guidance). With server-side tools like
                # web_search that can pause the model for 10s+ per use, a
                # non-streaming socket is vulnerable to idle dropouts and to
                # our own 30s httpx read timeout. Streaming keeps SSE events
                # flowing which resets the per-read timeout, letting the full
                # turn run up to the SDK's native 10-minute cap. The post-
                # generation pipeline (character break, language_cure, etc.)
                # is unaffected because .get_final_message() returns the same
                # Message object shape as .create().
                async with self.client.messages.stream(**kwargs) as stream:
                    response = await stream.get_final_message()
                cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
                cache_create = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
                block_types: dict[str, int] = {}
                for block in response.content:
                    bt = getattr(block, "type", "unknown")
                    block_types[bt] = block_types.get(bt, 0) + 1
                record_usage(
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    cache_read,
                    cache_create,
                    model=effective_model,
                )
                parsed = _parse_response_content(response.content)
                parsed.model_used = effective_model
                log.info(
                    "llm_response",
                    model=effective_model,
                    attempt=attempt,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    cache_read=cache_read,
                    cache_create=cache_create,
                    stop_reason=response.stop_reason,
                    block_types=block_types,
                    text_len=len(parsed.text),
                    tool_calls=len(parsed.tool_calls),
                )
                return parsed

            except anthropic.RateLimitError as e:
                last_error = e
                wait = 2**attempt
                log.warning("llm_rate_limited", attempt=attempt, wait_seconds=wait)
                await asyncio.sleep(wait)

            except anthropic.BadRequestError as e:
                # If tools caused the 400, retry WITHOUT tools so the bot doesn't go down
                if tools and "tool" in str(e).lower():
                    log.warning("llm_tools_rejected_fallback", error=str(e))
                    kwargs.pop("tools", None)
                    tools = None  # Don't try tools again on retry
                    continue
                last_error = e
                log.error("llm_bad_request", error=str(e))
                break

            except anthropic.AuthenticationError as e:
                log.error("llm_auth_error", error=str(e))
                raise

            except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
                last_error = e
                timeout_count += 1
                log.warning("llm_timeout", attempt=attempt, timeout_count=timeout_count, error=str(e))
                # Fire callback once, after the first timeout, so the user
                # knows we are retrying rather than dead.
                if timeout_count == 1 and on_timeout is not None:
                    try:
                        await on_timeout()
                    except Exception:
                        log.exception("on_timeout_callback_failed")
                if timeout_count >= _MAX_TIMEOUT_RETRIES or attempt == self.max_retries:
                    log.warning("llm_timeout_giving_up", timeout_count=timeout_count)
                    break
                await asyncio.sleep(1)

            except anthropic.APIStatusError as e:
                last_error = e
                # 529 Overloaded — transient, retry with backoff
                if e.status_code == 529:
                    wait = 2**attempt
                    log.warning("llm_overloaded", attempt=attempt, wait_seconds=wait, status=529)
                    if attempt == self.max_retries:
                        break
                    await asyncio.sleep(wait)
                else:
                    log.error("llm_api_error", status=e.status_code, error=str(e))
                    break

        _record_error()
        log.error(
            "llm_failed",
            attempts=attempt,
            max_retries=self.max_retries,
            last_error_type=type(last_error).__name__ if last_error else None,
            last_error=str(last_error),
        )
        if last_error is None:
            # Unreachable with max_retries >= 1 (loop runs at least once, and
            # every path either returns, raises, or assigns last_error). Keep
            # the explicit RuntimeError instead of `raise None` so if the
            # invariant breaks in the future the failure mode is debuggable.
            raise RuntimeError("llm._send exited loop without last_error set")
        raise last_error

    async def _recover_from_break(
        self,
        original: LLMResponse,
        system_prompt: str,
        messages: list[MessageParam],
        tools: list[dict] | None,
        tool_choice: dict | None,
        primary: str,
        fallback: str,
        has_distinct_fallback: bool,
        on_timeout: Callable[[], Awaitable[None]] | None = None,
    ) -> LLMResponse | None:
        """Handle a character break on the primary response.

        If a distinct fallback tier is available, rerun against it first (no
        reinforced prompt — let the smarter reasoner do the work). If the
        fallback also breaks, or no fallback is available, apply the legacy
        reinforced-retry path. Returns the recovered response, or None if
        every path failed — in which case `original.text` is sanitized in
        place so the caller can still ship something.
        """
        if has_distinct_fallback:
            log.info(
                "model_fallback_triggered",
                reason="character_break",
                from_model=primary,
                to_model=fallback,
            )
            try:
                fb = await self._send(
                    system_prompt,
                    messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    model=fallback,
                    on_timeout=on_timeout,
                )
                fb.text = strip_metadata(fb.text)
                if not detect_break(fb.text):
                    log.info("character_break_fixed_on_fallback", from_model=primary, to_model=fallback)
                    return fb
                log.warning("character_break_persisted_on_fallback", to_model=fallback)
                # Proceed to reinforced-retry against the fallback tier.
                primary_for_reinforcement = fallback
                original_for_sanitize = fb
            except Exception:
                log.exception(
                    "model_fallback_rerun_failed", reason="break_fallback", from_model=primary, to_model=fallback
                )
                primary_for_reinforcement = primary
                original_for_sanitize = original
        else:
            primary_for_reinforcement = primary
            original_for_sanitize = original

        reinforced_prompt = system_prompt + CHARACTER_REINFORCEMENT
        try:
            retry_response = await self._send(
                reinforced_prompt,
                messages,
                tools=tools,
                tool_choice=tool_choice,
                model=primary_for_reinforcement,
                on_timeout=on_timeout,
            )
            retry_response.text = strip_metadata(retry_response.text)
            retry_breaks = detect_break(retry_response.text)

            if not retry_breaks:
                log.info("character_break_fixed_on_retry", model=primary_for_reinforcement)
                return retry_response

            log.warning("character_break_persisted", retry_patterns=retry_breaks)
            retry_response.text = sanitize(retry_response.text)
            return retry_response

        except Exception:
            log.warning("character_break_retry_failed_using_sanitized_original")
            original_for_sanitize.text = sanitize(original_for_sanitize.text)
            # Overwrite the caller's view so it ends up with the sanitized text.
            original.text = original_for_sanitize.text
            original.model_used = original_for_sanitize.model_used
            return None

    async def chat(
        self,
        system_prompt: str,
        messages: list[MessageParam],
        *,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        on_timeout: Callable[[], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Send messages with optional tools, detect character breaks, retry if needed.

        Args:
            model: If provided, overrides self.model for this call (router primary).
            fallback_model: Second-tier model to retry against when the primary
                produces a character break or >=2 anti-pattern hits. When None
                or equal to `model`, falls back to the legacy reinforced-retry
                path against the same model (original behavior).
            on_timeout: Awaited once after the first APITimeoutError so callers
                can post a user-facing retry notice instead of silent dead air.

        Returns LLMResponse with text (for Discord) and tool_calls (for actions).
        """
        primary = model or self.model
        fallback = fallback_model or primary
        has_distinct_fallback = fallback != primary
        chat_start = time.monotonic()

        response = await self._send(
            system_prompt,
            messages,
            tools=tools,
            tool_choice=tool_choice,
            model=primary,
            on_timeout=on_timeout,
        )

        raw_text_len = len(response.text)

        # Strip leaked metadata (timestamps, speaker labels) before any other processing
        before_strip = response.text
        response.text = strip_metadata(response.text)
        if before_strip != response.text:
            log.info(
                "llm_text_mutated",
                stage="strip_metadata",
                before_len=len(before_strip),
                after_len=len(response.text),
            )

        breaks = detect_break(response.text)
        if breaks:
            log.warning(
                "character_break_detected",
                model=primary,
                patterns=breaks,
                text_preview=response.text[:200],
                text_len=len(response.text),
            )
            retry_response = await self._recover_from_break(
                response,
                system_prompt,
                messages,
                tools,
                tool_choice,
                primary,
                fallback,
                has_distinct_fallback,
                on_timeout=on_timeout,
            )
            final = retry_response if retry_response is not None else response
            log.info(
                "llm_chat_complete",
                model=primary,
                fallback=fallback if has_distinct_fallback else None,
                chat_ms=int((time.monotonic() - chat_start) * 1000),
                raw_text_len=raw_text_len,
                final_text_len=len(final.text),
                tool_calls=len(final.tool_calls),
                model_used=final.model_used,
                exit_reason="character_break_recovered" if retry_response is not None else "character_break_sanitized",
            )
            return final

        # Context-first enforcement. When the model produces a clarification
        # dump ("dime qué busco", "a qué te refieres", "repite") even though
        # the conversation has >3 messages of context, that clarification
        # should have been answered from memory. Retry once against the
        # primary with CONTEXT_REINFORCEMENT appended. No fallback model —
        # the issue is prompt obedience, not model capability. If the retry
        # still dumps, ship it anyway (soft enforcement, not a hard block).
        if len(messages) > 3:
            clarification_hits = detect_clarification_dump(response.text)
            if clarification_hits:
                log.warning(
                    "clarification_dump_detected",
                    model=primary,
                    patterns=clarification_hits,
                    text_preview=response.text[:200],
                    text_len=len(response.text),
                    context_messages=len(messages),
                )
                try:
                    retry = await self._send(
                        system_prompt + CONTEXT_REINFORCEMENT,
                        messages,
                        tools=tools,
                        tool_choice=tool_choice,
                        model=primary,
                        on_timeout=on_timeout,
                    )
                    retry.text = strip_metadata(retry.text)
                    retry_hits = detect_clarification_dump(retry.text)
                    if not retry_hits:
                        log.info("clarification_dump_fixed_on_retry", model=primary)
                        response = retry
                    else:
                        log.warning(
                            "clarification_dump_persisted",
                            model=primary,
                            patterns=retry_hits,
                        )
                        # Don't re-retry — the anti-pattern is soft and
                        # shipping the original is better than an infinite loop.
                except Exception:
                    log.exception("clarification_dump_retry_failed", model=primary)

        # Log anti-pattern drift — soft escalate to the fallback tier when distinct.
        anti_patterns = detect_anti_patterns(response.text)
        if anti_patterns:
            log.warning(
                "anti_pattern_detected",
                model=primary,
                patterns=anti_patterns,
                text_preview=response.text[:200],
                text_len=len(response.text),
            )
            if has_distinct_fallback and len(anti_patterns) >= _ANTI_PATTERN_FALLBACK_THRESHOLD:
                log.info(
                    "model_fallback_triggered",
                    reason="anti_pattern",
                    from_model=primary,
                    to_model=fallback,
                    hits=len(anti_patterns),
                )
                try:
                    rerun = await self._send(
                        system_prompt, messages, tools=tools, tool_choice=tool_choice, model=fallback
                    )
                    rerun.text = strip_metadata(rerun.text)
                    # Revalidate: the fallback model can still produce a break.
                    # If it does, route through the same recovery pipeline used
                    # for break-on-primary, but treat the fallback output as
                    # the "original" so we don't double-escalate to itself.
                    rerun_breaks = detect_break(rerun.text)
                    if rerun_breaks:
                        log.warning("character_break_on_antipattern_rerun", model=fallback, patterns=rerun_breaks)
                        recovered = await self._recover_from_break(
                            rerun,
                            system_prompt,
                            messages,
                            tools,
                            tool_choice,
                            fallback,
                            fallback,
                            has_distinct_fallback=False,
                        )
                        response = recovered if recovered is not None else rerun
                    else:
                        response = rerun
                except Exception:
                    log.exception(
                        "model_fallback_rerun_failed",
                        reason="anti_pattern_fallback",
                        from_model=primary,
                        to_model=fallback,
                    )

        # Step 7c: Language Cure — normalize mixed-language output via Haiku
        if self.cure_model and response.text:
            from insult.core.language import language_cure

            before_cure = response.text
            response.text = await language_cure(self.client, self.cure_model, response.text)
            if before_cure != response.text:
                log.info(
                    "llm_text_mutated",
                    stage="language_cure",
                    before_len=len(before_cure),
                    after_len=len(response.text),
                )
            # Defense in depth: the cure model (Haiku) sometimes re-introduces
            # scratchpad XML or stray tags even when the root prompt avoids them.
            # Re-run strip_metadata so nothing reaches the user.
            before_strip2 = response.text
            response.text = strip_metadata(response.text)
            if before_strip2 != response.text:
                log.info(
                    "llm_text_mutated",
                    stage="strip_metadata_post_cure",
                    before_len=len(before_strip2),
                    after_len=len(response.text),
                )

        # Step 7d: Formatting normalization — deterministic enforcement of
        # exclamation limits (max 1) and bold limits (max 2). Runs LAST so
        # neither the LLM nor the language cure can reintroduce violations.
        if response.text:
            before_fmt = response.text
            response.text = normalize_formatting(response.text)
            if before_fmt != response.text:
                log.info(
                    "llm_text_mutated",
                    stage="normalize_formatting",
                    before_len=len(before_fmt),
                    after_len=len(response.text),
                )
            before_lists = response.text
            response.text = strip_lists(response.text)
            if before_lists != response.text:
                log.info(
                    "llm_text_mutated",
                    stage="strip_lists",
                    before_len=len(before_lists),
                    after_len=len(response.text),
                )

        if response.tool_calls:
            log.info("tool_calls_detected", tools=[tc.name for tc in response.tool_calls])

        log.info(
            "llm_chat_complete",
            model=primary,
            fallback=fallback if has_distinct_fallback else None,
            chat_ms=int((time.monotonic() - chat_start) * 1000),
            raw_text_len=raw_text_len,
            final_text_len=len(response.text),
            text_preview=response.text[:160],
            tool_calls=len(response.tool_calls),
            model_used=response.model_used,
            exit_reason="ok",
        )
        return response
