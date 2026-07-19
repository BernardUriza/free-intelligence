"""The "Other People in This Channel" block — producer side.

Restored after 2f8d9ad deleted it with `personas/insult`. The consumer side
(`AgentRunnerClient.chat(other_people=...)` prefixing it onto user_text) never
died and is covered by the agent-client integration tests.
"""

import pytest

from khimeras_shared.other_people import (
    format_other_people_block,
    load_other_participants_facts,
    other_people_block_for_turn,
)


class FakeMemory:
    def __init__(self, participants: list[dict], facts: dict[str, list[dict]]):
        self._participants = participants
        self._facts = facts
        self.injection_calls: list[str] = []

    async def get_channel_participants(self, channel_id: str, limit: int = 10) -> list[dict]:
        return self._participants[:limit]

    async def get_facts_for_injection(self, user_id: str, auto_limit: int = 10) -> list[dict]:
        self.injection_calls.append(user_id)
        return self._facts.get(user_id, [])


def test_block_renders_header_and_one_bullet_per_person() -> None:
    block = format_other_people_block(
        {
            "Alex": [{"fact": "estudia enfermería"}, {"fact": "vive en Guadalajara"}],
            "Bernard": [{"fact": "escribe código"}],
        }
    )
    assert "Other People in This Channel" in block
    assert "- Alex: estudia enfermería; vive en Guadalajara" in block
    assert "- Bernard: escribe código" in block


def test_block_carries_the_strict_attribution_warning() -> None:
    """The header is what stops the model carrying the asker's traits over."""
    block = format_other_people_block({"Alex": [{"fact": "estudia enfermería"}]})
    assert "STRICT ATTRIBUTION" in block


def test_empty_facts_render_to_empty_string() -> None:
    assert format_other_people_block({}) == ""
    assert format_other_people_block({"Alex": []}) == ""


@pytest.mark.asyncio
async def test_author_is_excluded_from_the_block() -> None:
    """The runner already rebuilds the author's own facts from the user_id;
    duplicating them here invites the cross-attribution the header warns about."""
    memory = FakeMemory(
        participants=[{"user_id": "1", "user_name": "Bernard"}, {"user_id": "2", "user_name": "Alex"}],
        facts={"1": [{"fact": "escribe código"}], "2": [{"fact": "estudia enfermería"}]},
    )
    facts = await load_other_participants_facts(memory, "chan", exclude_user_id="1")
    assert list(facts) == ["Alex"]
    assert "1" not in memory.injection_calls


@pytest.mark.asyncio
async def test_participants_without_facts_are_omitted() -> None:
    memory = FakeMemory(
        participants=[{"user_id": "2", "user_name": "Alex"}, {"user_id": "3", "user_name": "Nadie"}],
        facts={"2": [{"fact": "estudia enfermería"}]},
    )
    facts = await load_other_participants_facts(memory, "chan", exclude_user_id="1")
    assert list(facts) == ["Alex"]


@pytest.mark.asyncio
async def test_caps_at_the_participant_limit() -> None:
    people = [{"user_id": str(i), "user_name": f"P{i}"} for i in range(2, 30)]
    memory = FakeMemory(
        participants=people,
        facts={p["user_id"]: [{"fact": "existe"}] for p in people},
    )
    facts = await load_other_participants_facts(memory, "chan", exclude_user_id="1", limit=3)
    assert len(facts) == 3


@pytest.mark.asyncio
async def test_a_memory_fault_degrades_to_no_block_never_raises() -> None:
    """Fail-safe: a turn without the block is a normal turn; a raise is a mute bot."""

    class Broken:
        async def get_channel_participants(self, channel_id: str, limit: int = 10) -> list[dict]:
            raise RuntimeError("pg down")

        async def get_facts_for_injection(self, user_id: str, auto_limit: int = 10) -> list[dict]:
            return []

    assert await load_other_participants_facts(Broken(), "chan", exclude_user_id="1") == {}
    assert await other_people_block_for_turn(Broken(), "chan", exclude_user_id="1") is None


@pytest.mark.asyncio
async def test_turn_helper_returns_none_when_nobody_else_has_facts() -> None:
    memory = FakeMemory(participants=[{"user_id": "1", "user_name": "Bernard"}], facts={"1": [{"fact": "x"}]})
    assert await other_people_block_for_turn(memory, "chan", exclude_user_id="1") is None


@pytest.mark.asyncio
async def test_turn_helper_renders_when_someone_else_has_facts() -> None:
    memory = FakeMemory(
        participants=[{"user_id": "2", "user_name": "Alex"}],
        facts={"2": [{"fact": "estudia enfermería"}]},
    )
    block = await other_people_block_for_turn(memory, "chan", exclude_user_id="1")
    assert block is not None
    assert "- Alex: estudia enfermería" in block
