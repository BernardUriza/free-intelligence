"""`GET /projects/{p}/sessions/{s}` — the answer a caller needs BEFORE a turn.

A consumer that keeps its own conversation history (og118 is local-first: the
browser owns the transcript) has to choose between replaying that history into
the turn and letting AIRE resume the session it already holds. Without this
endpoint the choice is unmakeable, so fi-runner defaulted to replaying — which
re-sent the whole conversation every turn AND minted a fresh session for it,
leaving the casita full of transcripts nobody ever resumed.

The read is `Engine.has_session`, which already existed for the pool's own
resume decision: this route only exposes it. It feeds a machine's decision about
how to send a turn, never a human's eyes ([[write-only-daemon]] exception 1).
"""

import pytest
from fastapi.testclient import TestClient

TOKEN = "the-owners-own-door-token"


class FakeEngine:
    """Answers `has_session` from a set of (project, session) pairs, and reports
    nothing running — enough to pin both routes without a database."""

    def __init__(self, known=()):
        self.known = set(known)
        self.detached = self

    async def has_session(self, project, session):
        return (project, session) in self.known

    def running(self, _key):
        return False


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("AIRE_AUTH_TOKEN", TOKEN)
    import aire.bearer
    import aire.door

    # BOTH bindings: `door.py` does `from .bearer import ACCEPTED_TOKENS`, so it
    # holds its own module-level copy read at import time. Patching only the
    # source passes alone and fails once another test has already imported door.
    monkeypatch.setattr(aire.bearer, "ACCEPTED_TOKENS", (TOKEN,))
    monkeypatch.setattr(aire.door, "ACCEPTED_TOKENS", (TOKEN,))
    from aire.server import app

    return TestClient(app, raise_server_exceptions=False)


def _with_engine(monkeypatch, engine):
    async def get_engine():
        return engine

    import aire.messages

    monkeypatch.setattr(aire.messages, "get_engine", get_engine)


AUTH = {"authorization": f"Bearer {TOKEN}"}


def test_an_unknown_session_is_reported_absent(client, monkeypatch):
    _with_engine(monkeypatch, FakeEngine())
    body = client.get("/projects/og118-abc/sessions/abc", headers=AUTH).json()
    assert body == {"session": "abc", "exists": False}


def test_a_session_the_store_holds_is_reported_present(client, monkeypatch):
    _with_engine(monkeypatch, FakeEngine({("og118-abc", "abc")}))
    body = client.get("/projects/og118-abc/sessions/abc", headers=AUTH).json()
    assert body["exists"] is True


def test_the_internet_cannot_enumerate_sessions(client, monkeypatch):
    """Everything but /health rides the Bearer. An open existence check would let
    anyone probe which casitas and sessions this box holds."""
    _with_engine(monkeypatch, FakeEngine({("og118-abc", "abc")}))
    assert client.get("/projects/og118-abc/sessions/abc").status_code == 401


def test_the_status_route_is_not_shadowed(client, monkeypatch):
    """`/sessions/{s}` and `/sessions/{s}/status` differ by a segment, so the
    router must keep telling them apart — a shadow here would silently turn every
    background-status poll into an existence check."""
    _with_engine(monkeypatch, FakeEngine())
    body = client.get("/projects/og118-abc/sessions/abc/status", headers=AUTH).json()
    assert body == {"session": "abc", "running": False}


def test_a_hostile_name_never_reaches_the_store(client, monkeypatch):
    """`safe_names` is the same allowlist the message endpoint rides; a traversal
    attempt is a 404, not a lookup."""
    _with_engine(monkeypatch, FakeEngine())
    assert client.get("/projects/..%2F..%2Fetc/sessions/abc", headers=AUTH).status_code == 404
