"""`[INVITE:]` marker — parse, strip, fire, and truncation rescue.

The runner path cannot emit structured tool calls (`AgentRunnerClient` returns
`tool_calls=[]` and the Claude Code runner has its own tool universe), so the
persona summons ALICE via an in-band marker, mirroring `[REACT:]`/`[REMEMBER:]`.
Mutator rule (robustness.md): positive cases + resistance cases for every parser.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from personas.insult.cogs.chat import invites
from personas.insult.cogs.chat.invites import fire_invite, parse_invite, strip_invites
from personas.insult.core.character.formatting import enforce_length_variation


class TestParseInvite:
    def test_extracts_reason(self):
        text = "Ali. Te llaman. [INVITE: Bern quiere tu lectura corta de la mañana] Faltas tú."
        assert parse_invite(text) == "Bern quiere tu lectura corta de la mañana"

    def test_case_insensitive(self):
        assert parse_invite("[invite: dale calor a este hilo]") == "dale calor a este hilo"

    def test_no_marker_returns_none(self):
        assert parse_invite("Ali. Te llaman. Faltas tú.") is None

    def test_empty_reason_is_none(self):
        """RESISTANCE: a stuttered empty marker must not fire an invite."""
        assert parse_invite("bueno [INVITE:] ya") is None

    def test_multiple_markers_only_first_fires(self):
        """RESISTANCE: two markers are a model stutter, not two summons."""
        text = "[INVITE: primera razón] y también [INVITE: segunda razón]"
        assert parse_invite(text) == "primera razón"

    def test_long_reason_truncated(self):
        reason = "x" * 600
        parsed = parse_invite(f"[INVITE: {reason}]")
        assert parsed is not None and len(parsed) <= invites.MAX_REASON_LEN + 1


class TestStripInvites:
    def test_removes_marker_preserves_text(self):
        text = "Ali. Te llaman. [INVITE: lectura corta] Faltas tú."
        assert strip_invites(text) == "Ali. Te llaman. Faltas tú."

    def test_marker_only_response_becomes_empty(self):
        assert strip_invites("[INVITE: ven]") == ""

    def test_no_marker_untouched(self):
        assert strip_invites("sin marcador aquí") == "sin marcador aquí"


class TestFireInvite:
    @pytest.mark.asyncio
    async def test_calls_summon_persona_with_reason(self, monkeypatch):
        mock = AsyncMock(return_value=True)
        monkeypatch.setattr("demux_ai.summon.summon_persona", mock)
        ok = await fire_invite(
            "lectura corta del sábado",
            channel_id="1489180895264116736",
            guild_id="1488419218302042223",
            channel_name="general",
        )
        assert ok is True
        mock.assert_awaited_once()
        args, kwargs = mock.call_args
        assert args[0] == {"reason": "lectura corta del sábado"}
        assert kwargs["channel_id"] == "1489180895264116736"

    @pytest.mark.asyncio
    async def test_forwards_trigger_message_id(self, monkeypatch):
        """The summoned persona reacts to the message that triggered the turn —
        the id must survive the fire_invite hop onto the wire."""
        mock = AsyncMock(return_value=True)
        monkeypatch.setattr("demux_ai.summon.summon_persona", mock)
        await fire_invite(
            "ven",
            channel_id="1",
            guild_id=None,
            channel_name=None,
            trigger_message_id="1526655478313127987",
        )
        assert mock.call_args.kwargs["trigger_message_id"] == "1526655478313127987"

    @pytest.mark.asyncio
    async def test_failure_is_swallowed_not_raised(self, monkeypatch):
        """RESISTANCE: a dead gateway must never blow up the delivered turn."""
        mock = AsyncMock(side_effect=RuntimeError("gateway down"))
        monkeypatch.setattr("demux_ai.summon.summon_persona", mock)
        ok = await fire_invite("ven", channel_id="1", guild_id=None, channel_name=None)
        assert ok is False


def test_truncation_rescues_invite_marker_in_tail():
    """The length enforcer must rescue [INVITE:] like REMEMBER/REACT — a summon
    the model decided on must not vanish because of a formatting heuristic."""
    text = (
        "First sentence. Second sentence. Third sentence. Fourth sentence. "
        "Fifth sentence with [INVITE: Bern necesita tu calor] inside. Sixth sentence."
    )
    result = enforce_length_variation(text, [120, 140, 130])
    assert "[INVITE: Bern necesita tu calor]" in result
