"""Weekly self-reflection — the persona acquires permanent tastes it chose.

Slice 4 of the leveled-DNA work (the "PR-2" the mcp_tools docstring left
unowned): on a slow, durable cadence each persona re-reads its own recent
turns, a judge decides which tastes/opinions earned permanence, and the
survivors land in `agent_facts` with `provenance='self_declared'` — exactly
the semantics the DNA sections "Lo que yo sé sobre mí" promise.

Posts NOTHING to Discord. Reads DB → judge → writes DB. Every fault degrades
to "try again next drain"; a transport failure never advances the gate."""

from __future__ import annotations

import time

import structlog

from khimeras_shared.memory import MemoryStore
from khimeras_shared.self_reflection import reflect_self_facts
from persona_gateway.config import CONFIG
from shared.personas import Persona

log = structlog.get_logger()


class ReflectionWorker:
    """Owns one persona's reflection pass. No-op without a judge client."""

    def __init__(self, persona: Persona, memory: MemoryStore) -> None:
        self.persona = persona
        self.memory = memory

    async def drain(self, judge_client) -> None:
        """One gated pass. `judge_client` is read LIVE off the client each tick
        (same convention as FactExtractor) so toggling it to None disables
        reflection on the next drain."""
        if judge_client is None:
            return
        persona_id = self.persona.persona_id
        now = time.time()
        try:
            last = await self.memory.get_last_reflected_at(persona_id)
        except Exception:
            log.exception("reflection_gate_read_failed", persona_id=persona_id)
            return
        if last is not None and now - last < CONFIG.reflection_min_interval_s:
            return

        try:
            turns = await self.memory.recent_assistant_turns(self.persona.display_name, CONFIG.reflection_window)
        except Exception:
            log.exception("reflection_turns_read_failed", persona_id=persona_id)
            return
        if len(turns) < CONFIG.reflection_min_turns:
            # Too little lived material to judge — do NOT advance the gate;
            # a quiet persona reflects when it has actually spoken.
            log.info("reflection_skipped_thin_material", persona_id=persona_id, turns=len(turns))
            return

        existing = await self.memory.get_agent_self_facts(persona_id)
        try:
            new_facts = await reflect_self_facts(
                judge_client,
                self.persona.display_name,
                existing,
                turns,
                max_facts=CONFIG.reflection_max_facts,
            )
        except Exception:
            # Transport/judge failure: retry on a future drain, gate untouched.
            log.exception("reflection_judge_failed", persona_id=persona_id)
            return

        # Judged (even with zero survivors) = the pass ran; cadence advances.
        await self.memory.mark_reflected(persona_id, now)
        stored = 0
        for fact in new_facts:
            fact_id = await self.memory.add_agent_self_fact(persona_id, fact["fact"], fact["category"], "self_declared")
            if fact_id is not None:
                stored += 1
        log.info(
            "reflection_pass_complete",
            persona_id=persona_id,
            judged_turns=len(turns),
            new_facts=stored,
        )
