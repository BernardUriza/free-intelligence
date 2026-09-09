"""Durable-marker routing — the persona's in-band side effects, out of the turn.

A persona reply can carry markers that spawn durable work: `[RESEARCH:]` (queue a
deep job), `[AGENDA:]` (persist a standing goal), `[REMIND:]` (schedule a
reminder), `[REMIND_CANCEL:]` (retire pending reminders matching a criterion),
`[REMEMBER:]` (write a fact). `MarkerRouter.route` parses each,
persists its side effect, strips the marker from the text, and returns the
cleaned reply — so only the in-character ack reaches Discord.

It does NOT touch Discord: reactions (`[REACT:]`, which need the live message and
the monkeypatch-visible `add_reactions`) and the actual send stay with the caller.
Every persistence is best-effort: a failed queue/save is logged and swallowed so
the ack still sends — better a persona who over-promised once than a silent drop.
"""

from __future__ import annotations

import asyncio

import structlog

from khimeras_shared.agenda_marker import parse_agenda, strip_agenda
from khimeras_shared.invite_marker import parse_invite, strip_invites
from khimeras_shared.markers import parse_remind_cancels, strip_remind_cancels
from khimeras_shared.memory import MemoryStore
from khimeras_shared.remember_marker import parse_remembers, persist_remembers, strip_remembers
from khimeras_shared.remind_marker import parse_remind, persist_remind, strip_reminds
from khimeras_shared.research_marker import parse_research, strip_research
from shared.personas import Persona
from shared.personas.registry import DEFAULT_INVITE_PERSONA_ID as INVITE_PERSONA_ID

log = structlog.get_logger()


class MarkerRouter:
    """Persist a persona reply's durable markers; return the reply minus markers."""

    def __init__(self, persona: Persona, memory: MemoryStore) -> None:
        self.persona = persona
        self.memory = memory
        # Late-bound in `app._main` once every PersonaClient exists: the gateway
        # runs all personas in ONE process, so a summon is a direct call to the
        # sibling's guarded `dispatch_invite` — no HTTP hop, no second token.
        self._siblings: dict[str, object] = {}
        self._bg_tasks: set[asyncio.Task[None]] = set()

    def bind_siblings(self, personas: dict[str, object]) -> None:
        """Give this router the live persona registry so `[INVITE:]` can summon."""
        self._siblings = personas

    async def route(
        self,
        text: str,
        *,
        channel_id: str,
        guild_id: str | None,
        user_id: str,
        bot_user_id: str = "",
    ) -> str:
        """Parse → persist → strip every durable marker; return cleaned text."""
        text = await self._route_research(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        text = await self._route_agenda(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        # Cancel BEFORE create: "cancela el de la ropa y recuérdame X" must never
        # let the cancel criterion eat the reminder being scheduled in this same
        # turn — the cancel only sees rows that existed before the turn.
        text = await self._route_remind_cancel(text, channel_id=channel_id, user_id=user_id)
        text = await self._route_remind(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        text = await self._route_remember(text, channel_id=channel_id, user_id=user_id, bot_user_id=bot_user_id)
        # LAST and unconditional: whatever happens above, `[INVITE:]` must not
        # survive into Discord. See `_route_invite`.
        text = await self._route_invite(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        return text

    async def _route_invite(self, text: str, *, channel_id: str, guild_id: str | None, user_id: str) -> str:
        """Strip `[INVITE:]` — always — and record that a summon was wanted.

        The summon pipeline died with `personas/` on 2026-07-14 and nothing
        replaced it, so this marker had no parser AND no stripper. On 2026-07-31
        that shipped an internal note about Bernard's own suicidal ideation
        straight into the channel, addressed to a sibling who never came.

        Stripping is therefore unconditional and lives at the END of the chain:
        no branch above can skip it. The log line is the honest half — it says
        out loud that a persona wanted a sibling and could not get one, instead
        of the silence that hid this for a month. Wiring the actual summon
        (late-bound sibling lookup -> `PersonaClient.dispatch_invite`) is the
        next change; it touches gateway boot order, so it does not ride here.
        """
        reason = parse_invite(text)
        if reason is None:
            return text
        # STRIP FIRST, unconditionally: every path below may fail, and none of
        # them is allowed to let the marker reach a human.
        text = strip_invites(text)

        if self.persona.persona_id == INVITE_PERSONA_ID:
            return text
        target = self._siblings.get(INVITE_PERSONA_ID)
        if target is None or getattr(target, "user", None) is None:
            log.warning(
                "persona_gateway_invite_target_unavailable",
                persona_id=self.persona.persona_id,
                target=INVITE_PERSONA_ID,
                channel_id=channel_id,
                known=sorted(self._siblings),
            )
            return text

        task = asyncio.create_task(
            target.dispatch_invite(  # type: ignore[attr-defined]
                channel_id=channel_id,
                guild_id=guild_id,
                channel_name=None,
                reason=reason,
                invited_by=self.persona.persona_id,
            )
        )
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        log.info(
            "persona_gateway_invite_summoned",
            persona_id=self.persona.persona_id,
            target=INVITE_PERSONA_ID,
            channel_id=channel_id,
            user_id=user_id,
            reason_preview=reason[:80],
        )
        return text

    async def _route_research(self, text: str, *, channel_id: str, guild_id: str | None, user_id: str) -> str:
        prompt = parse_research(text)
        if not prompt:
            return text
        text = strip_research(text)
        try:
            job_id = await self.memory.save_research_job(
                channel_id=channel_id,
                guild_id=guild_id,
                created_by=user_id,
                prompt=prompt,
                persona_id=self.persona.persona_id,
            )
            log.info(
                "research_job_queued",
                persona_id=self.persona.persona_id,
                job_id=job_id,
                channel_id=channel_id,
                prompt_chars=len(prompt),
            )
        except Exception:
            log.exception("research_job_queue_failed", persona_id=self.persona.persona_id, channel_id=channel_id)
        return text

    async def _route_agenda(self, text: str, *, channel_id: str, guild_id: str | None, user_id: str) -> str:
        goal = parse_agenda(text)
        if not goal:
            return text
        text = strip_agenda(text)
        try:
            agenda_id = await self.memory.save_agenda(
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
                guild_id=guild_id,
                created_by=user_id,
                goal=goal,
            )
            log.info(
                "agenda_saved",
                persona_id=self.persona.persona_id,
                agenda_id=agenda_id,
                channel_id=channel_id,
                goal_chars=len(goal),
            )
        except Exception:
            log.exception("agenda_save_failed", persona_id=self.persona.persona_id, channel_id=channel_id)
        return text

    async def _route_remind(self, text: str, *, channel_id: str, guild_id: str | None, user_id: str) -> str:
        request = parse_remind(text)
        if not request:
            return text
        text = strip_reminds(text)
        try:
            reminder_id = await persist_remind(
                request,
                memory=self.memory,
                channel_id=channel_id,
                guild_id=guild_id,
                created_by=user_id,
                # Ownership stamp: only THIS persona's drain loop fires it.
                persona_id=self.persona.persona_id,
            )
            log.info(
                "remind_saved",
                persona_id=self.persona.persona_id,
                reminder_id=reminder_id,
                channel_id=channel_id,
                when_raw=request.when_raw[:40],
            )
        except Exception:
            log.exception("remind_save_failed", persona_id=self.persona.persona_id, channel_id=channel_id)
        return text

    async def _route_remind_cancel(self, text: str, *, channel_id: str, user_id: str) -> str:
        criteria = parse_remind_cancels(text)
        if not criteria:
            return text
        text = strip_remind_cancels(text)
        for criterion in criteria:
            try:
                # Isolation mirrors the drain loop: only rows created by THIS user
                # and owned by THIS persona are eligible — a cancel can never reach
                # another user's reminders nor a sibling persona's queue.
                cancelled = await self.memory.cancel_pending_reminders(
                    created_by=user_id,
                    persona_id=self.persona.persona_id,
                    criterion=criterion,
                )
                log.info(
                    "remind_cancel_routed",
                    persona_id=self.persona.persona_id,
                    channel_id=channel_id,
                    criterion=criterion[:80],
                    cancelled=len(cancelled),
                    reminder_ids=[r.get("id") for r in cancelled],
                )
            except Exception:
                log.exception(
                    "remind_cancel_failed",
                    persona_id=self.persona.persona_id,
                    channel_id=channel_id,
                    criterion=criterion[:80],
                )
        return text

    async def _route_remember(self, text: str, *, channel_id: str, user_id: str, bot_user_id: str = "") -> str:
        facts = parse_remembers(text)
        if not facts:
            return text
        text = strip_remembers(text)
        # Un turno SIN sujeto humano —trigger de bot, trigger no fetchable, o el
        # `[INVITE:]` de una hermana— llega con el id del propio bot como
        # `user_id`. Escribir ahí no guarda el fact "en otro lado": lo guarda en
        # una cuenta que no es de nadie, y la persona lo relee mañana como si
        # fuera de un usuario. Se tira, y se dice en el log — un fact sin dueño
        # no tiene a quién pertenecer.
        if bot_user_id and user_id == bot_user_id:
            log.warning(
                "remember_discarded_no_human_subject",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
                count=len(facts),
            )
            return text
        try:
            saved = await persist_remembers(self.memory, user_id, facts)
            log.info(
                "remember_saved",
                persona_id=self.persona.persona_id,
                user_id=user_id,
                count=saved,
                channel_id=channel_id,
            )
        except Exception:
            log.exception("remember_save_failed", persona_id=self.persona.persona_id, channel_id=channel_id)
        return text
