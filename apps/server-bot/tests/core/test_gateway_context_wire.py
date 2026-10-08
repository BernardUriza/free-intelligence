"""Rich context ON THE WIRE — retrieval must leave the process.

`AgentRunnerClient.chat` has accepted `other_people` since 2026-06-03 and the
runner reads it. But after the 2f8d9ad purge NOBODY populated it, and nobody
called `memory.search` either: every turn shipped with a 30-message window and
zero facts about the other participants. The capability was alive and unwired —
the exact shape a unit test on the client cannot catch.

This is the seam test for both halves:
  · `relevant`  — keyword-relevant OLDER turns merged into the replayed context
  · `other_people` — facts about the OTHER channel participants, on the kwarg

Resistance cases: a retrieval fault must cost the ENRICHMENT, never the turn.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

RECENT = [{"role": "user", "user_name": "Bernard", "content": "y luego qué pasó", "timestamp": 200.0}]
OLD_RELEVANT = [{"role": "user", "user_name": "Alex", "content": "renté el depa de Barrhen", "timestamp": 100.0}]


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(
    *,
    relevant: list[dict] | None = None,
    participants: list[dict] | None = None,
    participant_facts: dict[str, list[dict]] | None = None,
    search_raises: bool = False,
    participants_raise: bool = False,
) -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="INSULT_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=list(RECENT))
    memory.get_facts = AsyncMock(return_value=[])
    memory.get_auto_facts = AsyncMock(return_value=[])
    memory.save_facts = AsyncMock()
    memory.search = AsyncMock(
        side_effect=RuntimeError("pg down") if search_raises else None,
        return_value=list(relevant or []),
    )
    memory.build_context = MagicMock(side_effect=lambda rec, **kw: list(rec))
    memory.search_facts_semantic = AsyncMock(return_value=[])
    memory.get_channel_participants = AsyncMock(
        side_effect=RuntimeError("pg down") if participants_raise else None,
        return_value=list(participants or []),
    )
    memory.get_facts_for_injection = AsyncMock(
        side_effect=lambda user_id, **_: (participant_facts or {}).get(user_id, [])
    )
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="respuesta", model_used="claude"))
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=SimpleNamespace(text="[]", stop_reason="end_turn"))
    return PersonaClient(
        persona,
        memory,
        agent_client,
        intents=discord.Intents.none(),
        judge_client=judge,
    )


def _message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.id = 1526655478313127987
    msg.content = text
    msg.channel = MagicMock(spec=discord.TextChannel)
    msg.channel.id = 1489180895264116736
    msg.channel.send = AsyncMock()
    msg.channel.typing = MagicMock(return_value=_Typing())
    msg.author = MagicMock()
    msg.author.id = 907264175246569543
    msg.author.display_name = "Bernard"
    msg.author.bot = False
    msg.guild = None
    msg.attachments = []
    msg.flags.voice = False
    return msg


def _other_people_sent(client: PersonaClient) -> str | None:
    return client.agent_client.chat.await_args.kwargs.get("other_people")


def _messages_sent(client: PersonaClient) -> list[dict]:
    return client.agent_client.chat.await_args.args[1]


async def test_relevant_older_turns_ride_the_relevant_memory_seam():
    """The 30-message window is not the whole memory: a keyword hit from last
    week must ride along — on the wire's `relevant_memory` kwarg, labeled as
    OLD excerpts, never folded into the replayed live thread where the runner
    would frame it as 'lo que se acaba de decir'."""
    client = _client(relevant=OLD_RELEVANT)
    await client._handle(_message("qué onda con el depa"))
    client.memory.search.assert_awaited_once()
    relevant_memory = client.agent_client.chat.await_args.kwargs.get("relevant_memory")
    assert relevant_memory and "Barrhen" in relevant_memory, "el turno relevante viejo no llegó al runner"
    replayed = " ".join(str(m.get("content", "")) for m in _messages_sent(client))
    assert "Barrhen" not in replayed, "el excerpt viejo se coló al hilo vivo replay"


async def test_other_participants_facts_reach_the_runner_kwarg():
    """The hole this closes: recalls Alex when Alex writes, denies her when
    Bernard asks ABOUT her (2026-06-03)."""
    client = _client(
        participants=[{"user_id": "1431300030823927999", "user_name": "Alex"}],
        participant_facts={"1431300030823927999": [{"fact": "estudia enfermería"}]},
    )
    await client._handle(_message("qué sabes de Alex"))
    block = _other_people_sent(client)
    assert block, "el gateway no mandó NINGÚN bloque de other_people"
    assert "Alex" in block and "estudia enfermería" in block


async def test_the_author_is_not_duplicated_into_other_people():
    """RESISTANCE: the runner rebuilds the author's own facts from the user_id;
    echoing them here is what invites cross-attribution between participants."""
    client = _client(
        participants=[{"user_id": "907264175246569543", "user_name": "Bernard"}],
        participant_facts={"907264175246569543": [{"fact": "escribe código"}]},
    )
    await client._handle(_message("hola"))
    assert _other_people_sent(client) is None


async def test_a_search_fault_degrades_to_recent_only_never_mute():
    """RESISTANCE: losing the enrichment is bad; losing the turn is worse."""
    client = _client(search_raises=True)
    await client._handle(_message("qué onda"))
    client.agent_client.chat.assert_awaited_once()
    replayed = " ".join(str(m.get("content", "")) for m in _messages_sent(client))
    assert "y luego qué pasó" in replayed


async def test_a_participants_fault_still_delivers_the_turn():
    """RESISTANCE: same fail-safe posture on the other_people half."""
    client = _client(participants_raise=True)
    await client._handle(_message("qué onda"))
    client.agent_client.chat.assert_awaited_once()
    assert _other_people_sent(client) is None
