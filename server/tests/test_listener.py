"""The socket's real contract, over a real socket (the pen's happy path).

Until now the ONLY thing that ever exercised port 9099 end to end was
`demo_device.py`, a systemd unit that is `disabled` and `inactive` — the whole
coverage of the daemon that holds the pen sat at the top of the pyramid, manual,
and not even running. That shape has a name (the inverted pyramid / ice-cream
cone) and the cure is the one this repo already uses for HTTP in
`test_gateway.py`: bind the REAL handler on an ephemeral port, speak the REAL
protocol from outside, assert on what actually landed.

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
    replies, _ = await _talk(["app-demo-device-01 KEEPALIVE seq=1"])
    text = _log(tmp_path)
    assert replies == [], "a plain report is appended, never ACKed"
    assert "app-demo-device-01 KEEPALIVE seq=1" in text
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
