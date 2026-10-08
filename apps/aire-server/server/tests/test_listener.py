"""The socket's real contract, over a real socket (the pen's happy path).

Until 2026-08-22 the ONLY thing that ever exercised port 9099 end to end was a
simulated device run as a systemd unit — `disabled`, `inactive`, and (since the
monorepo move) pointing at a path that no longer existed, so the demo it
promised could not even start. The whole coverage of the daemon that holds the
pen sat at the top of the pyramid, manual, and unable to run at all.

That shape has a name (the inverted pyramid / ice-cream cone) and the cure is
the one this repo already uses for HTTP in `test_gateway.py`: bind the REAL
handler on an ephemeral port, speak the REAL protocol from outside, assert on
what actually landed. The simulator was deleted once these replaced it.

The load-bearing claim here is not that a line arrives — it is that **the raw
verb token never touches the log**. `verbs.py` promises exactly that, the log is
append-only, and it is mirrored to Postgres and rendered by the front; a token
leaking into it could not be erased, only appended over.
"""

import asyncio

import pytest

from aire.listen import applog, guards, net, verbs

TOKEN = "the-verb-token-that-must-never-be-logged"


def _wire(tmp_path, monkeypatch) -> None:
    """Point the listener's captured module-level config at this test. They are
    read at import (`from .config import ...`), so the modules are patched, not
    the environment."""
    monkeypatch.setattr(applog, "LOG", tmp_path / "aire.log")
    monkeypatch.setattr(verbs, "VERB_TOKEN", TOKEN)
    monkeypatch.setattr(verbs, "WORKSPACES", tmp_path / "workspaces")
    (tmp_path / "aire.log").touch()


async def _talk(lines: list[str]) -> tuple[list[str], int]:
    """Serve the real handler on an ephemeral port, say `lines`, read replies."""
    server = await asyncio.start_server(net.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    replies: list[str] = []
    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        for line in lines:
            writer.write(line.encode() + b"\n")
            await writer.drain()
            try:
                got = await asyncio.wait_for(reader.readline(), timeout=0.4)
            except asyncio.TimeoutError:
                got = b""      # a report gets no ACK, only a log line
            if got:
                replies.append(got.decode().rstrip("\n"))
        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.05)   # let the handler append DISCONNECT
    return replies, port


def _log(tmp_path) -> str:
    return (tmp_path / "aire.log").read_text()


@pytest.mark.asyncio
async def test_a_report_lands_in_the_log_bracketed_by_the_connection(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch)
    replies, _ = await _talk(["patrol-07 KEEPALIVE seq=1"])
    text = _log(tmp_path)
    assert replies == [], "a plain report is appended, never ACKed"
    assert "patrol-07 KEEPALIVE seq=1" in text
    assert "CONNECT" in text and "DISCONNECT" in text


@pytest.mark.asyncio
async def test_the_raw_verb_token_NEVER_reaches_the_log(tmp_path, monkeypatch):
    """The one that would be catastrophic and silent. The log is append-only and
    mirrored to Postgres, so a leaked token could not be erased — only appended
    over. Both the accepted and the denied path are checked."""
    _wire(tmp_path, monkeypatch)
    await _talk([f"MKDIR {TOKEN} casita-uno", "MKDIR wrong-token casita-dos"])
    text = _log(tmp_path)
    assert TOKEN not in text, "the raw token reached the append-only log"
    assert "MKDIR casita-uno" in text, "the command is still an event, redacted"
    assert "MKDIR-DENIED" in text


@pytest.mark.asyncio
async def test_a_good_token_creates_the_casita_and_a_bad_one_is_refused(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch)
    replies, _ = await _talk([f"MKDIR {TOKEN} casita-uno", "MKDIR nope casita-dos"])
    assert replies[0].startswith("CREATED "), replies
    assert replies[1] == "DENIED"
    made = list((tmp_path / "workspaces").glob("*_casita-uno"))
    assert len(made) == 1 and made[0].is_dir()
    assert not list((tmp_path / "workspaces").glob("*_casita-dos"))


@pytest.mark.asyncio
async def test_a_NUL_byte_is_neutralised_at_the_mouth(tmp_path, monkeypatch):
    """NUL is valid UTF-8 and Postgres text cannot hold it — the poison pill that
    cost six days (docs/listener-doctrine.md). It must die before the log."""
    _wire(tmp_path, monkeypatch)
    await _talk(["device-x MESSAGE po\x00ison"])
    text = _log(tmp_path)
    assert "\x00" not in text
    assert "po�ison" in text


@pytest.mark.asyncio
async def test_an_empty_line_is_skipped_not_appended(tmp_path, monkeypatch):
    _wire(tmp_path, monkeypatch)
    await _talk(["", "device-x MESSAGE real"])
    lines = [line for line in _log(tmp_path).splitlines() if line.strip()]
    assert sum("MESSAGE" in line for line in lines) == 1


@pytest.mark.asyncio
async def test_a_socket_that_never_finishes_a_line_is_dropped(tmp_path, monkeypatch):
    """The slow-loris, demonstrated before it was fixed: four sockets that send
    bytes with no newline held every connection slot FOREVER and a real device
    was refused, on a port deliberately open to the whole internet. The caps
    bound how MANY sockets may be open; nothing bounded how LONG one may sit."""
    _wire(tmp_path, monkeypatch)
    monkeypatch.setattr(net, "HANDSHAKE_TIMEOUT_S", 0.3)
    server = await asyncio.start_server(net.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"bytes but never a newline")
        await writer.drain()
        # Bounded, and NOT with `async with server`: without the timeout in
        # net.py this read never returns, and a test that HANGS cannot go red —
        # it just burns the CI job. It must fail, and fail fast.
        try:
            eof = await asyncio.wait_for(reader.read(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("the socket was never hung up — the slow-loris still holds its slot")
        assert eof == b""
        writer.close()
    finally:
        # NOT `await server.wait_closed()`: it waits for the handler task, and a
        # handler stuck in a timeout-less readline never returns — the mutation
        # that proves this test would hang the suite instead of failing it.
        server.close()
    assert "IDLE-TIMEOUT dropped (handshake)" in _log(tmp_path), \
        "a jammed door that says nothing is the failure this repo keeps finding"


@pytest.mark.asyncio
async def test_a_device_that_HAS_spoken_keeps_the_generous_window(tmp_path, monkeypatch):
    """The half that would be worse to get wrong. One window for both cases
    either kills real devices between reports or leaves the loris a door — so a
    connection that has already delivered a line idles on IDLE_TIMEOUT_S, not on
    the handshake's."""
    _wire(tmp_path, monkeypatch)
    monkeypatch.setattr(net, "HANDSHAKE_TIMEOUT_S", 0.3)
    monkeypatch.setattr(net, "IDLE_TIMEOUT_S", 5.0)
    server = await asyncio.start_server(net.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"patrol-07 KEEPALIVE seq=1\n")
        await writer.drain()
        await asyncio.sleep(0.9)          # three handshake windows of silence
        writer.write(b"patrol-07 KEEPALIVE seq=2\n")
        await writer.drain()
        await asyncio.sleep(0.2)
        writer.close()
        await writer.wait_closed()
    text = _log(tmp_path)
    assert "seq=1" in text and "seq=2" in text, "a real device was killed mid-conversation"
    assert "IDLE-TIMEOUT" not in text


def test_the_whitelist_gate_fails_CLOSED_on_an_unloaded_roster(tmp_path, monkeypatch):
    """Not driven through the socket on purpose: loopback is exempt by design, so
    a localhost client can never exercise this. A security control that
    self-disables when the roster is unloaded is worse than none, so the gate is
    asserted where it lives."""
    _wire(tmp_path, monkeypatch)
    monkeypatch.setattr(guards, "WHITELIST_ENFORCE", True)
    monkeypatch.setattr(guards.roster, "ready", lambda: False)
    assert guards.admit("203.0.113.7", "203.0.113.7:5555", exempt=False) is False
    assert "DENIED-DEVICE" in _log(tmp_path), "a refused device must be SEEN, not silent"


@pytest.mark.asyncio
async def test_a_roster_write_that_FAILS_leaves_the_attempt_in_the_log(tmp_path, monkeypatch):
    """The failure #40 named: ALLOW logged only its success, so a Postgres blip
    took the whole command out of the append-only log AND out of the client's
    hands — the exception walked up through the connection handler, which
    appended DISCONNECT and hung up. Two devices, one roster, no record of who
    asked for what."""
    _wire(tmp_path, monkeypatch)
    monkeypatch.setattr(verbs.roster, "enabled", lambda: True)

    async def _explode(*_a, **_k):
        raise OSError("postgres went away mid-ALLOW")

    monkeypatch.setattr(verbs.roster, "add", _explode)
    replies, _ = await _talk([f"ALLOW {TOKEN} 203.0.113.9 the-camera"])
    text = _log(tmp_path)
    assert replies == ["ERROR roster write failed"], "the client must be TOLD"
    assert "ALLOW 203.0.113.9" in text, "the command itself was never recorded"
    assert "ALLOW-ERROR 203.0.113.9" in text, "the failure was never recorded"
    assert "ALLOWED-DEVICE" not in text, "a failed write must not read as a grant"
    assert TOKEN not in text


def test_an_overflowing_pen_marks_the_gap_in_BOTH_memories(tmp_path, monkeypatch):
    """A dropped line is correct — the file holds it and the mirror is the copy.
    A dropped line nobody counts is not: the front reads Postgres, where a hole
    with no marker reads as a quiet stretch. So the gap is bracketed, and the
    closing marker is the one that has to reach the MIRROR."""
    from aire.listen import pen as pen_mod

    _wire(tmp_path, monkeypatch)
    pen = pen_mod.Pen("postgresql://unused", maxsize=2)
    for i in range(5):
        pen.write(f"line-{i}")

    assert pen.dropped == 3
    assert "PEN-OVERFLOW mirror queue full" in _log(tmp_path)

    marker = pen._overflow_marker()
    assert len(marker) == 1 and "3 lines never reached postgres" in marker[0], \
        "the count must travel INTO the mirror, not only into the file"
    assert pen.dropped == 0
    assert marker[0] in _log(tmp_path)
