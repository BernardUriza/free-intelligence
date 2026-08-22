"""The casita's identity survives the box (#36's soul — casita.py).

Two claims carry this feature and both fail silently if they are wrong: a
persona that changed must reach Postgres, and a persona already on disk must
NEVER be clobbered by an older stored copy. The second is the dangerous one —
getting it backwards would overwrite a living identity with a stale snapshot,
and nothing would report it.
"""

import os

import asyncpg
import pytest

from aire import casita

DSN = os.environ.get("AIRE_DSN", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")
NAME = "persona-test-casita"


async def _conn(tmp_path, monkeypatch):
    monkeypatch.setattr(casita, "WORKSPACES", tmp_path)
    c = await asyncpg.connect(DSN, timeout=10)
    await c.execute(casita.DDL)
    await c.execute("DELETE FROM aire_casita WHERE casita = $1", NAME)
    return c


def _write(tmp_path, text: str):
    d = tmp_path / NAME
    d.mkdir(parents=True, exist_ok=True)
    (d / "CLAUDE.md").write_text(text, encoding="utf-8")
    return d / "CLAUDE.md"


@pytest.mark.asyncio
async def test_a_changed_persona_is_stored_and_an_unchanged_one_is_not(tmp_path, monkeypatch):
    c = await _conn(tmp_path, monkeypatch)
    try:
        _write(tmp_path, "I am the first identity.")
        assert await casita.offer(c) == 1
        assert await casita.offer(c) == 0, "an unchanged file must not append a row every tick"
        path = _write(tmp_path, "I am the SECOND identity.")
        os.utime(path, (0, 12345.0))
        assert await casita.offer(c) == 1
        rows = await c.fetch(
            "SELECT claude_md FROM aire_casita WHERE casita = $1 ORDER BY seq", NAME)
        assert [r[0] for r in rows] == ["I am the first identity.", "I am the SECOND identity."], \
            "append-only: rewriting a persona keeps both versions, it does not mutate one"
    finally:
        await c.execute("DELETE FROM aire_casita WHERE casita = $1", NAME)
        await c.close()


@pytest.mark.asyncio
async def test_an_absent_persona_comes_back_and_a_live_one_is_never_clobbered(tmp_path, monkeypatch):
    c = await _conn(tmp_path, monkeypatch)
    try:
        path = _write(tmp_path, "who I am")
        await casita.offer(c)

        path.unlink()  # the kill test: a fresh box has the code, not the soul
        assert await casita.restore(c) == 1
        assert path.read_text() == "who I am"

        # DISK WINS — a file that exists is left alone even when Postgres holds
        # a different version. Getting this backwards overwrites a living
        # identity with a stale snapshot, silently.
        path.write_text("who I have BECOME since", encoding="utf-8")
        assert await casita.restore(c) == 0
        assert path.read_text() == "who I have BECOME since"
    finally:
        await c.execute("DELETE FROM aire_casita WHERE casita = $1", NAME)
        await c.close()


@pytest.mark.asyncio
async def test_a_workspace_without_a_persona_is_not_invented(tmp_path, monkeypatch):
    c = await _conn(tmp_path, monkeypatch)
    try:
        (tmp_path / "empty-casita").mkdir()
        assert await casita.offer(c) == 0
        assert not (tmp_path / "empty-casita" / "CLAUDE.md").exists()
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_a_missing_workspaces_root_is_LOUD_not_an_empty_result(tmp_path, monkeypatch):
    """This is not hypothetical: it bit within an hour of shipping. The mirror
    unit did not carry AIRE_WORKSPACES, the root resolved to a directory that
    does not exist, and the run reported ZERO as if there were no personas —
    the exact silent degradation #40 exists to kill, reproduced by the commit
    that was fixing it. An absent directory is not an empty one."""
    c = await _conn(tmp_path, monkeypatch)
    monkeypatch.setattr(casita, "WORKSPACES", tmp_path / "nowhere")
    try:
        with pytest.raises(casita.NoWorkspaces):
            casita.on_disk()
        with pytest.raises(casita.NoWorkspaces):
            await casita.restore(c)
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_restore_recovers_the_NEWEST_version(tmp_path, monkeypatch):
    c = await _conn(tmp_path, monkeypatch)
    try:
        path = _write(tmp_path, "v1")
        await casita.offer(c)
        _write(tmp_path, "v2")
        os.utime(path, (0, 999.0))
        await casita.offer(c)
        path.unlink()
        await casita.restore(c)
        assert path.read_text() == "v2", "the log keeps every version; restore takes the last"
    finally:
        await c.execute("DELETE FROM aire_casita WHERE casita = $1", NAME)
        await c.close()
