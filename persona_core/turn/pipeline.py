"""`run_turn` — one persona turn, surface-free (F3, 2026-09-28).

Everything a turn does except DELIVER it:

    recent window → store the ask → context + guardian guidance → framing →
    brain → reactions → durable markers → GIFs → store the reply → facts (bg)

The surface adapter owns what only it can do: receive the message, call
`run_turn`, then deliver the `OutboundTurn` its own way. Discord sends chunks,
reacts and speaks; og118 returns JSON. The brain is injected, because it lives
in different places: the gateway reaches the runner over HTTP, and the runner
calls AIRE in-process.

Why it exists: until F3 this pipeline lived only in `persona_gateway/`, so a
turn from any other surface reached the runner "bald". It carried no guardian,
no stored turn and no fact growth. og118 was the first to hit that wall.

Failure posture is the gateway's, unchanged: every stage around the brain is
best-effort and degrades to a poorer turn, never a mute one. Only the brain may
raise, because only the surface knows how to say "I could not answer".
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import structlog

from persona_core.facts import UtilityClient
from persona_core.gifs import resolve_gifs, strip_gif_markers
from persona_core.memory import MemoryStore
from persona_core.reactions import parse_reactions, strip_reactions
from persona_core.turn.context import RELEVANT_MESSAGES_LIMIT, TurnContextBuilder
from persona_core.turn.facts import FactExtractor
from persona_core.turn.framing import compose_user_text
from persona_core.turn.markers import MarkerRouter
from shared.personas import Persona
from shared.text import split_response

log = structlog.get_logger()

# The gateway's defaults (`persona_gateway/config.py`), so a turn is assembled
# the same way whichever surface asks.
RECENT_LIMIT = 30
FACTS_RECENT_WINDOW = 12


@dataclass(frozen=True)
class InboundTurn:
    """A human's message, already received and identified by its surface."""

    persona: Persona
    surface: str
    channel_id: str
    # The CANONICAL principal (F2 resolves surface ids before this point).
    user_id: str
    user_name: str
    ask: str
    # Who the reply is stored as — Discord's bot user id, or the persona id on a
    # surface with no bot account.
    assistant_id: str
    attachments: list[dict] = field(default_factory=list)
    guild_id: str | None = None
    channel_name: str | None = None
    # The surface's own message id when it has one (Discord's makes the row
    # idempotent). None elsewhere.
    external_message_id: str | None = None
    # A job the runner resumes already stored its ask on the first attempt.
    resumed: bool = False


@dataclass(frozen=True)
class BrainTurn:
    """What the brain reads: one framed message plus the turn's guidance."""

    user_text: str
    behavioral_guidance: str | None
    attachments: list[dict]


@dataclass(frozen=True)
class BrainReply:
    text: str
    model: str | None = None


Brain = Callable[[BrainTurn], Awaitable[BrainReply]]


@dataclass(frozen=True)
class OutboundTurn:
    """What the surface delivers. `text` is marker-free and pacing-free."""

    text: str
    reactions: list[str]
    gif_urls: list[str]
    model: str | None
    # Why a turn ended with nothing to send: "" when it has text or GIFs.
    empty_reason: str = ""


async def run_turn(
    turn: InboundTurn,
    *,
    memory: MemoryStore,
    brain: Brain,
    judge: UtilityClient | None,
    bg_tasks: set[asyncio.Task],
    recent_limit: int = RECENT_LIMIT,
    relevant_limit: int = RELEVANT_MESSAGES_LIMIT,
    facts_recent_window: int = FACTS_RECENT_WINDOW,
    facts_model: str | None = None,
) -> OutboundTurn:
    """Run one turn end to end, short of delivery. Only `brain` may raise."""
    persona = turn.persona
    log.info("turn_pipeline_started", persona_id=persona.persona_id, surface=turn.surface, channel_id=turn.channel_id)

    # Recent window BEFORE storing the ask, so the ask is not in it twice.
    try:
        recent = await memory.get_recent(turn.channel_id, recent_limit)
    except Exception:
        log.exception("turn_pipeline_recent_failed", persona_id=persona.persona_id, channel_id=turn.channel_id)
        recent = []

    await _store_ask(turn, memory)

    context = await TurnContextBuilder(persona, memory, relevant_limit=relevant_limit).build(
        channel_id=turn.channel_id,
        recent=recent,
        relevant_query=turn.ask,
        guidance_user_id=turn.user_id,
        guidance_message=turn.ask,
        corpus_query=turn.ask,
        exclude_user_id=turn.user_id,
    )
    messages = [*context.context, {"role": "user", "content": turn.ask}]
    user_text = compose_user_text(
        turn.ask, messages, relevant_memory=context.relevant_memory, other_people=context.other_people
    )

    reply = await brain(BrainTurn(user_text, context.guidance, list(turn.attachments)))

    text = (reply.text or "").strip()
    raw_had_text = bool(text)
    reactions = parse_reactions(text)
    if reactions:
        text = strip_reactions(text)
    text = await MarkerRouter(persona, memory).route(
        text,
        channel_id=turn.channel_id,
        guild_id=turn.guild_id,
        user_id=turn.user_id,
        bot_user_id=turn.assistant_id,
    )
    gif_urls = resolve_gifs(persona.persona_id, text)
    text = strip_gif_markers(text)
    # What is said is the pacing-free text: memory never sees `[SEND]`.
    delivered = "\n".join(split_response(text)) if text else ""

    if delivered:
        await _store_reply(turn, memory, delivered, reply.model)

    # A real human ask is the only turn worth mining; the extraction runs in the
    # background so its LLM round-trip never sits between the user and the reply.
    FactExtractor(persona, memory, bg_tasks, model=facts_model).spawn(
        judge,
        turn.user_id,
        turn.user_name,
        [*recent[-facts_recent_window:], {"user_name": turn.user_name, "content": turn.ask}],
    )

    empty_reason = ""
    if not delivered and not gif_urls:
        empty_reason = "reactions_only" if reactions else ("markers_only" if raw_had_text else "brain_empty")
    log.info(
        "turn_pipeline_completed",
        persona_id=persona.persona_id,
        surface=turn.surface,
        channel_id=turn.channel_id,
        chars=len(delivered),
        reactions=len(reactions),
        gifs=len(gif_urls),
        empty_reason=empty_reason,
    )
    return OutboundTurn(delivered, reactions, gif_urls, reply.model, empty_reason)


async def _store_ask(turn: InboundTurn, memory: MemoryStore) -> None:
    """Persist the human's turn. A DB fault is logged and the turn goes on."""
    if turn.resumed:
        log.info("turn_pipeline_ask_already_stored", persona_id=turn.persona.persona_id, channel_id=turn.channel_id)
        return
    try:
        await memory.store(
            turn.channel_id,
            turn.user_id,
            turn.user_name,
            "user",
            turn.ask,
            guild_id=turn.guild_id,
            channel_name=turn.channel_name,
            discord_message_id=turn.external_message_id,
        )
    except Exception:
        log.exception("turn_pipeline_ask_store_failed", persona_id=turn.persona.persona_id, channel_id=turn.channel_id)


async def _store_reply(turn: InboundTurn, memory: MemoryStore, delivered: str, model: str | None) -> None:
    """Persist the persona's reply. A DB fault is logged and the turn goes on."""
    try:
        await memory.store(
            turn.channel_id,
            turn.assistant_id,
            turn.persona.display_name,
            "assistant",
            delivered,
            for_user_id=turn.user_id,
            guild_id=turn.guild_id,
            channel_name=turn.channel_name,
            model_used=model,
        )
    except Exception:
        log.exception(
            "turn_pipeline_reply_store_failed", persona_id=turn.persona.persona_id, channel_id=turn.channel_id
        )
