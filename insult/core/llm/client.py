"""LLMClient — Anthropic API client with retry policy, character break
detection, and post-generation mutation pipeline.

This is the heart of the request flow. Everything user-facing goes
through `chat()`; internal utility calls (facts extraction, channel
summaries, memory consolidator judges) use `utility_call()` to skip
the user-facing guards. The retry loop in `_send()` owns SDK retry
policy entirely — we configure `max_retries=0` on the SDK so our
outer loop is the single source of truth.

Retry classes (see retry.py for the timing math):
- 429 RateLimitError: honor retry-after-ms / retry-after up to 60s,
  else Full Jitter with cap 60s.
- 5xx APIStatusError (500/502/503/529): retry-after if present,
  else Full Jitter cap 30s. 529 keeps the historical
  `llm_overloaded` event name so alerts still fire.
- 504 + APITimeoutError + APIConnectionError: capped at
  _MAX_TIMEOUT_RETRIES (2) regardless of max_retries, jitter cap
  10s. on_timeout callback fires after the first to keep UX honest.
- 400 BadRequestError with "tool" in message: retry once without
  tools, then break.

Character-break recovery (`_recover_from_break`) escalates to the
fallback tier if distinct, then applies the legacy reinforced-retry
path against whichever tier last spoke. Sanitization is the final
floor; we always ship something.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

import anthropic
import structlog
from anthropic.types import MessageParam

from insult.core.character import (
    CHARACTER_REINFORCEMENT,
    CONTEXT_REINFORCEMENT,
    MutationStage,
    detect_anti_patterns,
    detect_break,
    detect_clarification_dump,
    normalize_formatting,
    run_pipeline,
    sanitize,
    strip_lists,
    strip_metadata,
)
from insult.core.llm.parsing import (
    LLMResponse,
    _build_system_blocks,
    _parse_response_content,
)
from insult.core.llm.pricing import (
    _record_error,
    record_usage,
)
from insult.core.llm.retry import (
    _BACKOFF_CAP_5XX,
    _BACKOFF_CAP_429,
    _BACKOFF_CAP_TIMEOUT,
    _MAX_TIMEOUT_RETRIES,
    _full_jitter_backoff,
    _parse_retry_after,
)

log = structlog.get_logger()

# Anti-pattern fallback threshold: number of pattern hits that triggers a
# rerun against the fallback model. Below this the hit is only logged.
_ANTI_PATTERN_FALLBACK_THRESHOLD = 2


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
        max_tokens: int | None = None,
        on_timeout: Callable[[], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Raw API call with retry logic for transient errors.

        `model` overrides self.model for this call only (used by the 3-tier
        router to route per-turn). Defaults to self.model when None.

        `max_tokens` overrides self.max_tokens for this call only (used by
        utility_call() — facts extraction wants 4096, proactive social
        wants 256, etc.). Defaults to self.max_tokens when None.

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
                    "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
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
                parsed.stop_reason = response.stop_reason or ""
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
                response = getattr(e, "response", None)
                headers = getattr(response, "headers", None) if response is not None else None
                retry_after = _parse_retry_after(headers)
                wait = retry_after if retry_after is not None else _full_jitter_backoff(attempt, _BACKOFF_CAP_429)
                log.warning(
                    "llm_rate_limited",
                    attempt=attempt,
                    wait_seconds=round(wait, 2),
                    retry_after_present=retry_after is not None,
                    status=429,
                )
                log.info(
                    "llm_retry",
                    status=429,
                    attempt=attempt,
                    wait_seconds=round(wait, 2),
                    retry_after_present=retry_after is not None,
                )
                if attempt == self.max_retries:
                    break
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
                wait = _full_jitter_backoff(attempt, _BACKOFF_CAP_TIMEOUT)
                log.warning(
                    "llm_timeout",
                    attempt=attempt,
                    timeout_count=timeout_count,
                    wait_seconds=round(wait, 2),
                    error=str(e),
                )
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
                log.info(
                    "llm_retry",
                    status=None,
                    attempt=attempt,
                    wait_seconds=round(wait, 2),
                    retry_after_present=False,
                )
                await asyncio.sleep(wait)

            except anthropic.APIStatusError as e:
                last_error = e
                response = getattr(e, "response", None)
                headers = getattr(response, "headers", None) if response is not None else None

                # Transient 5xx (500/502/503/529 — overload class). All retried
                # with Full Jitter; 529 keeps the historical event name so
                # alerts that key on it still fire.
                if e.status_code in (500, 502, 503, 529):
                    retry_after = _parse_retry_after(headers)
                    wait = retry_after if retry_after is not None else _full_jitter_backoff(attempt, _BACKOFF_CAP_5XX)
                    event = "llm_overloaded" if e.status_code == 529 else "llm_transient_5xx"
                    log.warning(
                        event,
                        attempt=attempt,
                        wait_seconds=round(wait, 2),
                        status=e.status_code,
                        retry_after_present=retry_after is not None,
                    )
                    log.info(
                        "llm_retry",
                        status=e.status_code,
                        attempt=attempt,
                        wait_seconds=round(wait, 2),
                        retry_after_present=retry_after is not None,
                    )
                    if attempt == self.max_retries:
                        break
                    await asyncio.sleep(wait)
                # 504 Gateway Timeout — same family as APITimeoutError.
                # Capped at _MAX_TIMEOUT_RETRIES regardless of max_retries so
                # the user does not stare at 30s x N of dead air.
                elif e.status_code == 504:
                    timeout_count += 1
                    wait = _full_jitter_backoff(attempt, _BACKOFF_CAP_TIMEOUT)
                    log.warning(
                        "llm_timeout",
                        attempt=attempt,
                        timeout_count=timeout_count,
                        wait_seconds=round(wait, 2),
                        status=504,
                        error=str(e),
                    )
                    if timeout_count == 1 and on_timeout is not None:
                        try:
                            await on_timeout()
                        except Exception:
                            log.exception("on_timeout_callback_failed")
                    if timeout_count >= _MAX_TIMEOUT_RETRIES or attempt == self.max_retries:
                        log.warning("llm_timeout_giving_up", timeout_count=timeout_count)
                        break
                    log.info(
                        "llm_retry",
                        status=504,
                        attempt=attempt,
                        wait_seconds=round(wait, 2),
                        retry_after_present=False,
                    )
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

        # Step 7c-d: Final post-LLM mutation pipeline. See
        # ``insult/core/character/pipeline.py`` for the Intercepting
        # Filter pattern this enforces. Each stage declares its own
        # shrink cap; the runner emits ``mutation_applied`` /
        # ``pipeline_violation`` per stage so a regression like the
        # 2026-05-06 deduplicate_opener bug — where a stage silently
        # deleted 51% of a vulnerable user's reply — cannot recur on
        # any of these stages either.
        #
        # ``language_cure`` is the only async stage; the runner detects
        # awaitables and awaits them so it composes here without
        # special-casing.
        if response.text:
            stages: list[MutationStage] = []
            if self.cure_model:
                from insult.core.language import language_cure

                async def _cure(t: str, _ctx: dict, _self: LLMClient = self) -> str:
                    return await language_cure(_self.client, _self.cure_model, t)

                stages.append(
                    MutationStage(
                        name="language_cure",
                        apply=_cure,
                        max_shrink_pct=0.50,
                        on_violation="skip_stage",
                    )
                )
                # Defense in depth: cure can reintroduce scratchpad XML
                # the root prompt avoided. Re-run strip_metadata after.
                stages.append(
                    MutationStage(
                        name="strip_metadata_post_cure",
                        apply=lambda t, _ctx: strip_metadata(t),
                        max_shrink_pct=0.30,
                        on_violation="skip_stage",
                    )
                )
            stages.append(
                MutationStage(
                    name="normalize_formatting",
                    apply=lambda t, _ctx: normalize_formatting(t),
                    max_shrink_pct=0.20,
                    on_violation="skip_stage",
                )
            )
            stages.append(
                MutationStage(
                    name="strip_lists",
                    apply=lambda t, _ctx: strip_lists(t),
                    max_shrink_pct=0.40,
                    on_violation="skip_stage",
                )
            )
            response.text = await run_pipeline(stages, response.text, ctx={})

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

    async def utility_call(
        self,
        system_prompt: str,
        messages: list[MessageParam],
        *,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Internal-utility variant of chat() — runs through retry policy
        and prompt caching, but skips the user-facing guards
        (character_break detection, anti_pattern check, language_cure,
        formatting normalization, deduplication).

        Use for non-user-facing LLM work: facts extraction, channel
        summaries, memory consolidator judges, image descriptions,
        siesta diary entries. The output of these calls feeds into the
        bot's internal state, not the user — running language_cure on
        them would be wasted Haiku tokens, and a "character break" in a
        fact JSON output is not a leak (it's parser failure, handled
        by the JSON parse).

        Returns the same LLMResponse as `chat()`, including `stop_reason`
        so callers can detect truncation.
        """
        return await self._send(
            system_prompt,
            messages,
            tools=tools,
            tool_choice=tool_choice,
            model=model,
            max_tokens=max_tokens,
        )
