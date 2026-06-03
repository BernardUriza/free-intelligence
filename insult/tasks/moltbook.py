"""Moltbook background tasks — inbound digest, engagement, heartbeat, outbound.

All four loops share one lazily-initialized ``MoltbookSource`` (fail-closed
when MOLTBOOK_API_KEY is empty), the in-character Discord narrator, and the
single-use math-challenge solver. They live together on ``MoltbookTasks`` so
that shared state can't drift across modules.

The inbound loop also reads the shared ``ProactiveState`` (via
``should_send_now``) so it never double-taps a channel right after a proactive
check-in. Generation/redaction route through the runner's one-shot /v1/judge.
"""

from __future__ import annotations

import structlog
from discord.ext import tasks

from insult.core.delivery import MESSAGE_DELIMITER, split_response
from insult.core.moltbook_engagement import engage_once, reply_to_own_post_commenters
from insult.core.moltbook_inbound import build_inbound_digest
from insult.core.moltbook_outbound import (
    assign_subject_codes,
    build_post_draft,
    detect_salience_signal,
    is_outbound_blocked,
    load_previous_outbound_notes,
    persist_draft,
    persist_published_post,
    redact_with_llm,
    regex_privacy_strip,
)
from insult.core.proactive import should_send_now
from insult.core.prompts_loader import load_prompt
from insult.core.sources.moltbook import MoltbookSource
from insult.tasks.channels import find_most_active_channel
from insult.tasks.state import ProactiveState

log = structlog.get_logger()


class MoltbookTasks:
    """Owns the Moltbook source + narrator + solver + the four loops.

    Build once in ``bot._build``; pass ``get_source`` to the debug server,
    register ``all_loops()`` for start/cancel, and call ``aclose()`` on
    shutdown.
    """

    def __init__(self, bot, container, memory, state: ProactiveState) -> None:
        self._bot = bot
        self._container = container
        self._memory = memory
        self._state = state
        # Lazy-init at first use, gated by api_key. None when MOLTBOOK_API_KEY
        # is empty so the loops short-circuit without ever touching the network.
        self._source: MoltbookSource | None = None
        self.inbound = self._build_inbound()
        self.engagement = self._build_engagement()
        self.heartbeat = self._build_heartbeat()
        self.outbound = self._build_outbound()

    # -- lifecycle ----------------------------------------------------------

    def all_loops(self) -> list[tasks.Loop]:
        return [self.inbound, self.engagement, self.heartbeat, self.outbound]

    async def aclose(self) -> None:
        if self._source is not None:
            await self._source.close()

    def get_source(self) -> MoltbookSource | None:
        """Lazy source factory. Also handed to the debug server so its preview
        endpoints reuse the same instance."""
        if self._source is not None:
            return self._source
        api_key = self._container.settings.moltbook_api_key.get_secret_value()
        if not api_key:
            return None
        self._source = MoltbookSource(
            api_key=api_key,
            base_url=self._container.settings.moltbook_base_url,
            verify_llm_solver=self._verify_llm_solver,
        )
        log.info("moltbook_source_initialized", base_url=self._container.settings.moltbook_base_url)
        return self._source

    # -- shared helpers -----------------------------------------------------

    async def _verify_llm_solver(self, challenge_text: str) -> str | None:
        """Resolve a Moltbook lobster-math challenge with Claude Haiku.

        The verification_code is single-use, so a wrong answer permanently
        burns the comment. LLM is more flexible than the regex solver at the
        weird physics phrasings ('accelerates by', 'velocity loss of', etc.)
        Moltbook keeps inventing."""
        log.info("moltbook_verify_llm_solver_entered", challenge_len=len(challenge_text))
        if self._container.judge_client is None:
            log.info("moltbook_verify_llm_solver_skipped", reason="no_judge_client")
            return None
        try:
            resp = await self._container.judge_client.utility_call(
                (
                    "You decode an obfuscated math word problem and return "
                    "the numeric answer. The text uses doubled letters, "
                    "case-mashing, and junk symbols as anti-bot noise — "
                    "ignore that.\n\n"
                    "RESPOND IN THIS EXACT FORMAT (one line only, nothing "
                    "else, no preamble, no reasoning, no markdown):\n\n"
                    "ANSWER: NN.NN\n\n"
                    "Where NN.NN is the answer with exactly two decimals. "
                    "DO NOT show your work. DO NOT explain. JUST the line "
                    "starting with 'ANSWER:'."
                ),
                [{"role": "user", "content": challenge_text}],
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
            )
            raw = (resp.text or "").strip()
            log.info("moltbook_verify_llm_solver_raw", raw=raw[:400])
            import re as _re

            # Require the explicit ANSWER: <num> marker. The previous fallback
            # to "last number in raw" was a foot-gun: when Haiku rambled past
            # max_tokens, the last number was a step in its decoding trace
            # (e.g. "fifteen newtons") rather than the final answer (40 = 25
            # + 15). Single-use verification_code means a wrong guess burns
            # the comment forever — better to return None and skip verify
            # than to send a confidently-wrong answer.
            m = _re.search(r"ANSWER\s*:\s*(-?\d+(?:\.\d+)?)", raw, _re.IGNORECASE)
            if not m:
                log.warning(
                    "moltbook_verify_llm_solver_no_marker",
                    raw=raw[:400],
                    challenge_preview=challenge_text[:200],
                )
                return None
            num = float(m.group(1))
            return f"{num:.2f}"
        except Exception:
            log.exception("moltbook_verify_llm_solver_failed")
            return None

    async def _announce(self, *, summary_seed: str) -> None:
        """Render a 1-3 sentence Spanish report of a Moltbook event and send it
        to MOLTBOOK_REPORT_CHANNEL_ID. Silently no-ops if the env is unset or
        the channel can't be resolved."""
        target_id = self._container.settings.moltbook_report_channel_id.strip()
        if not target_id:
            return
        try:
            channel = self._bot.get_channel(int(target_id))
        except (ValueError, TypeError):
            log.warning("moltbook_narrator_channel_id_invalid", channel_id=target_id)
            return
        if channel is None:
            log.warning("moltbook_narrator_channel_not_found", channel_id=target_id)
            return
        if self._container.judge_client is None:
            log.info("moltbook_narrator_skipped", reason="no_judge_client")
            return
        try:
            system = f"{self._container.settings.system_prompt[:1500]}\n\n{load_prompt('moltbook_discord_narrator')}"
            resp = await self._container.judge_client.utility_call(system, [{"role": "user", "content": summary_seed}])
            text = (resp.text or "").strip()
            if not text:
                log.info("moltbook_narrator_empty")
                return
            await channel.send(text)
            log.info("moltbook_narrator_sent", channel_id=target_id, text_len=len(text))
        except Exception:
            log.exception("moltbook_narrator_failed", channel_id=target_id)

    # -- INBOUND (every 6h, gated on api_key + flag + idle) -----------------

    def _build_inbound(self) -> tasks.Loop:
        @tasks.loop(hours=6)
        async def _moltbook_inbound_task():
            container, memory, bot, state = self._container, self._memory, self._bot, self._state
            if not container.settings.moltbook_inbound_enabled:
                return
            source = self.get_source()
            if source is None:
                return  # api_key empty — fail-closed without noise
            if not container.settings.moltbook_submolts:
                log.info("moltbook_inbound_skipped", reason="no_submolts_configured")
                return
            try:
                from datetime import datetime as dt
                from zoneinfo import ZoneInfo

                now = dt.now(ZoneInfo("America/Mexico_City"))

                # Find most recently active text channel (same heuristic as proactive)
                target_channel = await find_most_active_channel(bot, memory, skip_event="moltbook_inbound_channel_skip")
                if target_channel is None:
                    return

                # should_send_now coordination: don't talk over an active conversation
                # AND don't fire right after a proactive (it would feel like spam).
                recent_msgs = await memory.get_recent(str(target_channel.id), limit=15)
                last_user_ts = next(
                    (m["timestamp"] for m in reversed(recent_msgs) if m["role"] == "user"),
                    None,
                )
                if not should_send_now(now.hour, state.last_proactive_ts, last_user_ts, state.unanswered):
                    log.info("moltbook_inbound_skipped", reason="should_send_now_false")
                    return

                # Build context: every distinct user_id seen in recent_msgs
                user_ids = list({m["user_id"] for m in recent_msgs if m.get("role") == "user" and m.get("user_id")})

                if container.judge_client is None:
                    log.info("moltbook_inbound_skipped", reason="no_judge_client")
                    return
                result = await build_inbound_digest(
                    source,
                    container.settings.moltbook_submolts,
                    user_ids,
                    memory=memory,
                    judge=container.judge_client,
                    settings=container.settings,
                    recent_messages=recent_msgs,
                )
                if result.skipped_reason:
                    log.info("moltbook_inbound_skipped", reason=result.skipped_reason)
                    return
                if not result.rendered_message:
                    return

                try:
                    parts = split_response(result.rendered_message)
                    for part in parts:
                        await target_channel.send(part)
                    log.info(
                        "moltbook_inbound_sent",
                        channel=target_channel.name,
                        picks=len(result.picks),
                        rendered_len=len(result.rendered_message),
                    )
                    # Persist as bot message so future context build sees it
                    await memory.store(
                        str(target_channel.id),
                        str(bot.user.id),
                        bot.user.name,
                        "assistant",
                        result.rendered_message.replace(MESSAGE_DELIMITER, "\n"),
                    )
                except Exception:
                    log.exception("moltbook_inbound_send_failed")
            except Exception:
                log.exception("moltbook_inbound_task_failed")

        return _moltbook_inbound_task

    # -- ENGAGEMENT (every 12h: comment on others' posts) -------------------

    def _build_engagement(self) -> tasks.Loop:
        @tasks.loop(hours=12)
        async def _moltbook_engagement_task():
            container, memory, bot = self._container, self._memory, self._bot
            if not container.settings.moltbook_engagement_enabled:
                return
            source = self.get_source()
            if source is None:
                return
            if container.judge_client is None:
                return
            try:
                target_channel = await find_most_active_channel(
                    bot, memory, skip_event="moltbook_engagement_channel_skip"
                )
                if target_channel is None:
                    log.info("moltbook_engagement_skipped", reason="no_active_channel")
                    return
                recent_msgs = await memory.get_recent(str(target_channel.id), limit=15)
                user_ids = list({m["user_id"] for m in recent_msgs if m.get("role") == "user" and m.get("user_id")})

                result = await engage_once(
                    source=source,
                    memory=memory,
                    persona=container.settings.system_prompt,
                    judge=container.judge_client,
                    summary_model=container.settings.summary_model,
                    facts_user_ids=user_ids,
                    channel_id=str(target_channel.id),
                    blocked_authors=container.settings.moltbook_blocked_authors,
                )
                if isinstance(result, tuple):
                    log.info("moltbook_engagement_skipped", reason=result[1])
                    return
                target = result.target
                log.info(
                    "moltbook_engagement_published",
                    comment_id=result.comment_id,
                    target_post_id=target.post.id,
                    keyword=target.keyword,
                )
                seed = (
                    f"Comenté en un post ajeno en Moltbook.\n"
                    f"Post target:\n"
                    f"  author: {target.post.author}\n"
                    f"  submolt: m/{target.post.submolt}\n"
                    f"  title: {target.post.title}\n"
                    f"  url: https://www.moltbook.com/post/{target.post.id}\n"
                    f"Mi comment publicado:\n  «{result.comment_text}»"
                )
                await self._announce(summary_seed=seed)
            except Exception:
                log.exception("moltbook_engagement_task_failed")

        return _moltbook_engagement_task

    # -- HEARTBEAT (every 20min: reply to commenters on OUR posts) ----------
    # Phase 7 (.claude/plans/elegant-foraging-knuth.md). The 12h engagement
    # task only INITIATES comments on others' posts; if someone replies to one
    # of OUR posts we never respond. The Moltbook skill.md prescribes this exact
    # loop — poll /home → reply via the agent's own LLM → mark notifications
    # read — as the canonical heartbeat. Hand-writing replies via raw curl is
    # an anti-pattern there, so this routes through judge.utility_call +
    # redact_with_llm + the rate-limited MoltbookSource.create_comment.

    def _build_heartbeat(self) -> tasks.Loop:
        @tasks.loop(minutes=20)
        async def _moltbook_heartbeat_task():
            container, memory, bot = self._container, self._memory, self._bot
            if not container.settings.moltbook_heartbeat_enabled:
                return
            source = self.get_source()
            if source is None:
                return
            if container.judge_client is None:
                return
            try:
                target_channel = await find_most_active_channel(
                    bot, memory, skip_event="moltbook_heartbeat_channel_skip"
                )
                if target_channel is None:
                    log.info("moltbook_heartbeat_skipped", reason="no_active_channel")
                    return
                recent_msgs = await memory.get_recent(str(target_channel.id), limit=15)
                user_ids = list({m["user_id"] for m in recent_msgs if m.get("role") == "user" and m.get("user_id")})

                results = await reply_to_own_post_commenters(
                    source=source,
                    memory=memory,
                    persona=container.settings.system_prompt,
                    judge=container.judge_client,
                    summary_model=container.settings.summary_model,
                    facts_user_ids=user_ids,
                    channel_id=str(target_channel.id),
                    blocked_authors=container.settings.moltbook_blocked_authors,
                )
                if not results:
                    log.info("moltbook_heartbeat_no_replies")
                    return
                log.info("moltbook_heartbeat_published", count=len(results))
                for r in results:
                    seed = (
                        f"Le contesté a @{r.parent_comment_author} en mi post de Moltbook.\n"
                        f"Mi post:\n  title: {r.post_title}\n  url: https://www.moltbook.com/post/{r.post_id}\n"
                        f"Su comment:\n  parent_id: {r.parent_comment_id}\n"
                        f"Mi reply publicada:\n  «{r.reply_text}»"
                    )
                    await self._announce(summary_seed=seed)
            except Exception:
                log.exception("moltbook_heartbeat_task_failed")

        return _moltbook_heartbeat_task

    # -- OUTBOUND (every 24h, gated stack) ----------------------------------
    # Three layers fire in order: gates (vulnerability + disclosure), salience
    # (must have a fresh stance / synthesis to seed off), and the regex + LLM
    # redaction pipeline. Any layer can short-circuit silently — by design.

    def _build_outbound(self) -> tasks.Loop:
        @tasks.loop(hours=24)
        async def _moltbook_outbound_task():
            container, memory, bot = self._container, self._memory, self._bot
            if not container.settings.moltbook_outbound_enabled:
                return
            source = self.get_source()
            if source is None:
                return  # api_key empty
            if container.judge_client is None:
                log.info("moltbook_outbound_skipped", reason="no_judge_client")
                return
            if not container.settings.moltbook_submolts:
                log.info("moltbook_outbound_skipped", reason="no_submolts_configured")
                return
            try:
                # Find target channel (same heuristic as inbound)
                target_channel = await find_most_active_channel(
                    bot, memory, skip_event="moltbook_outbound_channel_skip"
                )
                if target_channel is None:
                    log.info("moltbook_outbound_skipped", reason="no_active_channel")
                    return

                recent_msgs = await memory.get_recent(str(target_channel.id), limit=15)
                user_ids = list({m["user_id"] for m in recent_msgs if m.get("role") == "user" and m.get("user_id")})
                if not user_ids:
                    log.info("moltbook_outbound_skipped", reason="no_users_in_channel")
                    return

                # GATE 1 — vulnerability + disclosure (vulnerability gate is
                # arc-phase-aware; pass channel_id so it can look up the user's
                # current phase and skip blocking if recovery/stability)
                blocked_reason, blocked_uid = await is_outbound_blocked(
                    user_ids, memory=memory, channel_id=str(target_channel.id)
                )
                if blocked_reason:
                    log.warning(
                        "moltbook_outbound_blocked",
                        reason=blocked_reason,
                        user_id=blocked_uid,
                    )
                    return

                # GATE 2 — must have a salient reason
                signal = await detect_salience_signal(
                    str(target_channel.id),
                    user_ids,
                    memory=memory,
                    recent_messages=recent_msgs,
                )
                if signal is None:
                    log.info("moltbook_outbound_skipped", reason="no_salience")
                    return

                # Build draft (LLM call #1) with continuity context
                target_submolt = container.settings.moltbook_submolts[0]  # post to first
                previous_notes = await load_previous_outbound_notes(memory, limit=5)
                subject_codes = assign_subject_codes(user_ids)
                draft = await build_post_draft(
                    signal,
                    target_submolt,
                    persona=container.settings.system_prompt,
                    judge=container.judge_client,
                    previous_notes=previous_notes,
                    subject_codes=subject_codes,
                )
                if draft is None:
                    log.warning("moltbook_outbound_skipped", reason="draft_failed")
                    return

                # Collect facts for redaction's negative-target prompt
                all_facts: list[str] = []
                for uid in user_ids:
                    facts = await memory.get_facts(uid)
                    all_facts.extend(f["fact"] for f in facts)

                # Layer 3a — regex strip (cheap pre-filter)
                stripped = regex_privacy_strip(draft.content, [{"fact": f} for f in all_facts])

                # Layer 3b — LLM redaction (decisive, with substring leak detection)
                redacted = await redact_with_llm(
                    stripped,
                    all_facts,
                    judge=container.judge_client,
                    model=container.settings.summary_model,
                )
                if redacted is None:
                    # Persist the draft anyway — operator can audit what was
                    # generated even when redaction blocked it
                    await persist_draft(draft, None, memory=memory, extra_notes="redaction_blocked")
                    log.warning(
                        "moltbook_outbound_skipped",
                        reason="redaction_failed_or_leaked",
                        title=draft.title,
                    )
                    return

                # Title language gate: redact_with_llm only processes content,
                # leaving the title in whatever language the draft LLM produced.
                # ensure_title_english is a no-op when the title is already
                # English; otherwise it runs a Haiku translation pass.
                from insult.core.moltbook_outbound import ensure_title_english

                draft.title = await ensure_title_english(
                    draft.title,
                    judge=container.judge_client,
                    model=container.settings.summary_model,
                )

                # AUDIT: persist draft BEFORE publishing — if Moltbook 5xxs after
                # accepting the post, we still know exactly what we generated
                await persist_draft(draft, redacted, memory=memory)

                # PUBLISH
                try:
                    post = await source.create_post(target_submolt, draft.title, redacted)
                    log.info(
                        "moltbook_outbound_post_created",
                        post_id=post.id,
                        submolt=target_submolt,
                        title=draft.title,
                        salience_kind=signal.kind,
                    )
                    # Audit: record the published post separately so future
                    # build_post_draft calls can cite it via load_previous_outbound_notes
                    await persist_published_post(draft, post.id, redacted, memory=memory)
                    # Narrator: report to Discord
                    seed = (
                        f"Acabo de publicar un post nuevo en Moltbook.\n"
                        f"  submolt: m/{target_submolt}\n"
                        f"  title: {draft.title}\n"
                        f"  url: https://www.moltbook.com/post/{post.id}\n"
                        f"Salience kind: {signal.kind}"
                    )
                    await self._announce(summary_seed=seed)
                except Exception:
                    log.exception("moltbook_outbound_publish_failed", title=draft.title)
            except Exception:
                log.exception("moltbook_outbound_task_failed")

        return _moltbook_outbound_task
