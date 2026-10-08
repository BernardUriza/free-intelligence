"""The "alive but mute" signal (#14) — /health can tell answering from silent.

`serving:true` means a persona logged in; it does NOT mean the persona is
answering. The 2026-06-13 boot-zombie reported ready for 14 min while mute. This
signal closes that gap: a persona that SAW an addressed message but delivered no
reply (past the grace window) is flagged `mute_suspected`. Both timestamps old =
just no traffic (normal at low scale), never flagged.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

from persona_gateway import invite_server
from persona_gateway.invite_server import INVITE_PERSONA_ID, build_invite_app

TOKEN = "t"  # noqa: S105


def _client(last_message_seen=None, last_turn_delivered=None) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(id=1),
        respond_to_invite=None,
        last_message_seen=last_message_seen,
        last_turn_delivered=last_turn_delivered,
    )


def _health(persona) -> dict:
    app = build_invite_app({INVITE_PERSONA_ID: persona}, TOKEN)
    with TestClient(app) as http:
        return http.get("/health").json()


def test_message_seen_but_no_reply_past_grace_is_mute():
    """A message came in, no turn went out, and it's older than the grace window."""
    now = time.time()
    persona = _client(last_message_seen=now - (invite_server._MUTE_GRACE_SECONDS + 60), last_turn_delivered=None)
    body = _health(persona)
    assert body["mute_suspected"] == [INVITE_PERSONA_ID]
    assert body["liveness"][INVITE_PERSONA_ID]["mute_suspected"] is True


def test_recent_reply_is_not_mute():
    """POSITIVE: a persona that just answered is healthy."""
    now = time.time()
    persona = _client(last_message_seen=now - 300, last_turn_delivered=now - 5)
    body = _health(persona)
    assert body["mute_suspected"] == []
    assert body["liveness"][INVITE_PERSONA_ID]["last_turn_age_s"] < 30


def test_no_traffic_is_not_mute():
    """RESISTANCE: both timestamps None (nobody messaged it) is NOT mute — the
    #1 false-positive to avoid at 1-user scale."""
    body = _health(_client(last_message_seen=None, last_turn_delivered=None))
    assert body["mute_suspected"] == []
    assert body["liveness"][INVITE_PERSONA_ID]["mute_suspected"] is False


def test_message_seen_within_grace_is_not_yet_mute():
    """RESISTANCE: a turn in flight (message seen 30s ago, runner still working)
    must not be misread as mute before the grace window."""
    now = time.time()
    persona = _client(last_message_seen=now - 30, last_turn_delivered=None)
    body = _health(persona)
    assert body["mute_suspected"] == []
