"""Durable-marker routing — the persona's in-band side effects, out of the turn.

A persona reply can carry markers that spawn durable work: `[RESEARCH:]` (queue a
deep job), `[AGENDA:]` (persist a standing goal), `[REMIND:]` (schedule a
reminder), `[REMEMBER:]` (write a fact). `MarkerRouter.route` parses each,
persists its side effect, strips the marker from the text, and returns the
cleaned reply — so only the in-character ack reaches Discord.

It does NOT touch Discord: reactions (`[REACT:]`, which need the live message and
the monkeypatch-visible `add_reactions`) and the actual send stay with the caller.
Every persistence is best-effort: a failed queue/save is logged and swallowed so
the ack still sends — better a persona who over-promised once than a silent drop.
"""

from __future__ import annotations

import structlog

from khimeras_shared.agenda_marker import parse_agenda, strip_agenda
from khimeras_shared.memory import MemoryStore
from khimeras_shared.remember_marker import parse_remembers, persist_remembers, strip_remembers
from khimeras_shared.remind_marker import parse_remind, persist_remind, strip_reminds
from khimeras_shared.research_marker import parse_research, strip_research
from shared.personas import Persona

log = structlog.get_logger()


class MarkerRouter:
    """Persist a persona reply's durable markers; return the reply minus markers."""

    def __init__(self, persona: Persona, memory: MemoryStore) -> None:
        self.persona = persona
        self.memory = memory

    async def route(
        self,
        text: str,
        *,
        channel_id: str,
        guild_id: str | None,
        user_id: str,
    ) -> str:
        """Parse → persist → strip every durable marker; return cleaned text."""
        text = await self._route_research(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        text = await self._route_agenda(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        text = await self._route_remind(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        text = await self._route_remember(text, channel_id=channel_id, user_id=user_id)
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

    async def _route_remember(self, text: str, *, channel_id: str, user_id: str) -> str:
        facts = parse_remembers(text)
        if not facts:
            return text
        text = strip_remembers(text)
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
