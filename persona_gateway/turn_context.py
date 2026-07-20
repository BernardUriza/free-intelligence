"""Turn context assembly — everything a persona turn carries besides the ask.

One builder, two callers: the @mention path (`PersonaClient._handle`) and the
host-routed invite path (`PersonaClient.respond_to_invite`) used to assemble
this pipeline each on their own — relevant retrieval → context framing →
guardian guidance → pending reminders → corpus RAG → other-people facts. The
2026-07-19 invite gap (guardian/reminders/relevant wired only into the
near-zero-traffic mention path) is exactly the drift that duplicated assembly
invites; this module is the single source of that pipeline.

Every stage is best-effort by construction: a fault in retrieval, guidance,
reminders or corpus degrades that block to None/[] — never to a mute turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

from khimeras_shared.guidance import MAX_GUIDANCE_CHARS, guidance_for_turn
from khimeras_shared.memory import MemoryStore
from khimeras_shared.other_people import other_people_block_for_turn
from persona_gateway.config import CONFIG
from persona_gateway.routing import format_context
from shared.corpus.persona_corpus import build_persona_corpus_block
from shared.personas import Persona

log = structlog.get_logger()

# The pending-reminders context block stays small on purpose: enough for the
# persona to list/cancel by text, never a wall that crowds out the guidance.
PENDING_REMINDERS_MAX = 10
_REMINDER_BLOCK_TZ = "America/Mexico_City"


def _pending_reminders_block(pending: list[dict]) -> str:
    """Render this user's pending reminders as turn context (data rows + a
    2-line structural frame — the ≤5-line inline exception; the rows are data)."""
    tz = ZoneInfo(_REMINDER_BLOCK_TZ)
    lines = ["RECORDATORIOS PENDIENTES de este usuario (agendados por ti):"]
    for row in pending[:PENDING_REMINDERS_MAX]:
        when = datetime.fromtimestamp(float(row["remind_at"]), tz=tz).strftime("%Y-%m-%d %H:%M")
        recurring = row.get("recurring") or "none"
        suffix = f" ({recurring})" if recurring != "none" else ""
        lines.append(f"- «{row['description']}» — {when}{suffix}")
    lines.append("Para cancelar uno emite [REMIND_CANCEL: <fragmento del texto del recordatorio>].")
    return "\n".join(lines)


@dataclass(frozen=True)
class TurnContext:
    """The assembled non-ask half of a turn, ready for `TurnRunner`."""

    context: list[dict]
    guidance: str | None
    other_people: str | None


class TurnContextBuilder:
    """Owns the shared context pipeline for both turn entry points."""

    def __init__(self, persona: Persona, memory: MemoryStore) -> None:
        self.persona = persona
        self.memory = memory

    async def build(
        self,
        *,
        channel_id: str,
        recent: list[dict],
        relevant_query: str,
        guidance_user_id: str | None,
        guidance_message: str,
        corpus_query: str,
        exclude_user_id: str,
    ) -> TurnContext:
        """Assemble context + guidance + other-people for one turn.

        `guidance_user_id=None` (an invite with no human subject) skips the
        guardian and reminders — there is no user to classify — but the corpus
        and other-people blocks still ride.
        """
        relevant = await self.load_relevant(channel_id, relevant_query)
        context = format_context(self.memory.build_context(recent, relevant))

        # The guardian: classify THIS turn against the user's accumulated facts
        # and send the persona's guidance on the wire. Without it the
        # vulnerable-user overlay never reaches the model — a user with a
        # clinical cluster gets the raw abrasive register. Every fault inside
        # returns None: a turn without guidance is a normal turn.
        guidance = None
        if guidance_user_id:
            guidance = await guidance_for_turn(
                memory=self.memory,
                user_id=guidance_user_id,
                current_message=guidance_message,
                recent_messages=context,
                persona_id=self.persona.persona_id,
            )
            # Pending reminders BEFORE the corpus merge, so the final order is
            # corpus → reminders → guardian guidance (safety stays freshest/last).
            guidance = await self.append_pending_reminders(guidance, guidance_user_id)
        guidance = await self.append_corpus_block(guidance, corpus_query)

        # Facts about the OTHER participants. The runner rebuilds the AUTHOR's
        # facts from the user_id, but is blind to the people being talked ABOUT
        # unless we forward them — the "recuerda a Alex cuando Alex escribe, la
        # niega cuando preguntan por ella" hole (2026-06-03).
        other_people = await other_people_block_for_turn(self.memory, channel_id, exclude_user_id=exclude_user_id)
        return TurnContext(context=context, guidance=guidance, other_people=other_people)

    async def load_relevant(self, channel_id: str, ask: str) -> list[dict]:
        """Keyword-relevant OLDER turns for this ask, or [] on any fault.

        Degrading to recent-only is a poorer answer; raising here would be a
        mute turn. Always the former.
        """
        if not ask:
            return []
        try:
            hits = await self.memory.search(channel_id, ask, CONFIG.relevant_limit)
        except Exception:
            log.exception("relevant_search_failed", channel_id=channel_id)
            return []
        # Positive telemetry, not just failure telemetry: without a success
        # event this retrieval is unauditable in prod — "it didn't error" is not
        # "it fired", and inferring from the answer's richness is exactly the
        # attribution guess this event exists to replace.
        log.info(
            "relevant_context_loaded",
            channel_id=channel_id,
            hits=len(hits),
            persona_id=self.persona.persona_id,
        )
        return hits

    async def append_pending_reminders(self, guidance: str | None, user_id: str) -> str | None:
        """Merge this user's pending reminders (owned by THIS persona) into the
        turn guidance so the persona can list them and cancel by text.

        Same contract as `append_corpus_block`: the block goes BEFORE the
        guidance (the safety overlay stays last), the merge never grows past
        MAX_GUIDANCE_CHARS (the block is dropped whole rather than trimmed —
        a half reminder row is worse than none), and any fault returns the
        guidance untouched. A user with no pending rows gets no block.
        """
        try:
            pending = await self.memory.list_pending_reminders(user_id, self.persona.persona_id)
            if not pending:
                return guidance
            block = _pending_reminders_block(pending)
        except Exception:
            log.exception("gateway_pending_reminders_failed", persona_id=self.persona.persona_id)
            return guidance
        if not guidance:
            return block[:MAX_GUIDANCE_CHARS]
        sep = "\n\n"
        if len(block) + len(sep) + len(guidance) > MAX_GUIDANCE_CHARS:
            log.warning(
                "gateway_reminders_dropped_guidance_full",
                persona_id=self.persona.persona_id,
                guidance_chars=len(guidance),
                block_chars=len(block),
            )
            return guidance
        return f"{block}{sep}{guidance}"

    async def append_corpus_block(self, guidance: str | None, ask: str) -> str | None:
        """Merge this persona's corpus references into the turn guidance.

        ORDER IS SAFETY: corpus FIRST, guardian guidance LAST — the vulnerable-user
        overlay must be the freshest thing in the block, never buried under 2,200
        chars of erudition (cruel-critic 2026-07-16, finding #2).

        CAP IS SAFETY TOO: the runner rejects `behavioral_guidance` > 16000 with a
        422 (a mute bot). `guidance_for_turn` already truncates to that cap; this
        merge would re-inflate it past the cap by prepending the corpus, so we
        RE-CAP here — trimming the CORPUS end, never the guidance. The safety
        overlay always survives intact; erudition yields. If guidance alone
        already fills the cap, the corpus is dropped entirely (cruel-critic
        2026-07-16, finding #1: a near-cap vulnerable-user overlay + a corpus hit
        used to 422 and mute the bot for the most fragile person).

        Fail-safe: any fault returns the guidance untouched. A persona with no
        `corpus_namespace` (or no relevant hit) simply gets its guidance back.
        """
        try:
            block = await build_persona_corpus_block(persona_id=self.persona.persona_id, query=ask)
        except Exception:
            log.exception("gateway_corpus_block_failed", persona_id=self.persona.persona_id)
            return guidance
        if not block:
            return guidance
        if not guidance:
            return block[:MAX_GUIDANCE_CHARS]
        # Reserve the full guidance (safety-critical); the corpus gets whatever
        # budget is left. sep is "\n\n". A non-positive budget → drop the corpus.
        sep = "\n\n"
        corpus_budget = MAX_GUIDANCE_CHARS - len(guidance) - len(sep)
        if corpus_budget <= 0:
            log.warning(
                "gateway_corpus_dropped_guidance_full",
                persona_id=self.persona.persona_id,
                guidance_chars=len(guidance),
            )
            return guidance
        if len(block) > corpus_budget:
            log.info(
                "gateway_corpus_trimmed_to_cap",
                persona_id=self.persona.persona_id,
                block_chars=len(block),
                corpus_budget=corpus_budget,
            )
            block = block[:corpus_budget]
        return f"{block}{sep}{guidance}"
