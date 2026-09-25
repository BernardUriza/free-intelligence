import re
from pathlib import Path

import pytest

from demux_ai.fallback import RETRY_INVITED_BY
from persona_gateway.invites import HOST_ROUTED_INVITERS, invite_instruction

DEMUX = Path(__file__).resolve().parents[2] / "demux_ai"


@pytest.mark.parametrize("invited_by", ["host", RETRY_INVITED_BY])
def test_host_routed_turn_is_told_the_turn_is_its_own(invited_by):
    text = invite_instruction(invited_by, "hilo de cine")
    assert text.startswith("[El turno es tuyo")
    assert "Insult te invitó" not in text


def test_sibling_invite_keeps_the_invitation_prose():
    text = invite_instruction("insult", "pídele una peli")
    assert text.startswith("[Insult te invitó")


def test_every_literal_the_host_emits_is_recognized():
    emitted = {
        value
        for path in DEMUX.rglob("*.py")
        for value in re.findall(r'invited_by="([a-z_]+)"', path.read_text(encoding="utf-8"))
    }
    assert emitted, "the scan found no invited_by literal — the regex no longer matches demux_ai"
    assert emitted <= HOST_ROUTED_INVITERS
