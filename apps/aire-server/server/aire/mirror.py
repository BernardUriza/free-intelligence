"""The door mirror (backlog #17): the interactive CLI's transcripts, deathless.

The SSH door (the tmux'd Claude Code TUI) writes its transcript as JSONL on the
MORTAL disk — exactly what the litmus test forbids. This mirror re-reads those
files and appends every uuid'd entry to the same Postgres store the engine
uses (`claude_session_store`), keyed the same way: project_key derived from
the entry's cwd, session_id = the file's stem. Idempotent by the store's
uuid-dedup. An mtime+size cache (#26) skips files that have not changed since
their last successful offer — a RECONSTRUCTIBLE cache, not truth: deleting it
just re-reads everything once and the dedup absorbs it, so there is still no
local state whose loss loses anything. Entries WITHOUT a uuid (queue-operation,
ai-title, last-prompt — CLI metadata, not transcript) are skipped: no dedup
handle, no memory. Runs as a oneshot under aire-mirror.timer (the sweep
pattern); logs to the file only when it actually offered entries, so an idle
minute stays silent.
"""

import asyncio
import json
import os
from pathlib import Path

from .agent_sdk import project_key_for_directory

from .listen.applog import _now, append_file
from .store import create_postgres_session_store

DSN = os.environ.get("AIRE_DATABASE_URL", "")
PROJECTS = Path(os.environ.get("AIRE_CLI_PROJECTS",
                               Path.home() / ".claude" / "projects"))
CACHE = Path(os.environ.get("AIRE_MIRROR_CACHE", "/var/lib/aire/mirror-cache.json"))


def read_entries(path: Path) -> tuple[str | None, list[dict]]:
    """Parse one JSONL transcript: (cwd, uuid'd entries in file order)."""
    cwd, entries = None, []
    for line in path.read_text().splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if cwd is None and d.get("cwd"):
            cwd = d["cwd"]
        if d.get("uuid"):
            entries.append(d)
    return cwd, entries


def load_cache() -> dict[str, list]:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict[str, list]) -> None:
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:  # a cache that cannot save only costs a re-read
        print(f"SESSION-MIRROR cache not saved: {exc}")


def stamp(path: Path) -> list:
    st = path.stat()
    return [st.st_mtime, st.st_size]


async def _offer_changed(store, cache: dict[str, list]) -> tuple[int, int]:
    """Offer every transcript whose stamp moved; stamp it only once its entries
    are safely in Postgres, so a failed run retries the same file next minute."""
    offered = sessions = 0
    alive: set[str] = set()
    for path in sorted(PROJECTS.glob("*/*.jsonl")):
        alive.add(str(path))
        seen = stamp(path)
        if cache.get(str(path)) == seen:
            continue
        cwd, entries = read_entries(path)
        if cwd and entries:
            key = {"project_key": project_key_for_directory(cwd),
                   "session_id": path.stem}
            await store.append(key, entries)
            offered += len(entries)
            sessions += 1
        cache[str(path)] = seen
    for gone in set(cache) - alive:  # a deleted transcript's stamp has no future
        del cache[gone]
    return offered, sessions


async def _offer_personas() -> int:
    """The casitas' CLAUDE.md, on the same tick (#36's soul, which nothing kept
    — see casita.py). Its own try: a persona that fails to store must not stop
    the door's transcripts from being mirrored, and vice versa."""
    import asyncpg

    from . import casita

    try:
        conn = await asyncpg.connect(DSN, timeout=10)
        try:
            return await casita.offer(conn)
        finally:
            await conn.close()
    except Exception as exc:  # noqa: BLE001 — loud, and the door's mirror carries on
        print(f"CASITA-MIRROR failed: {type(exc).__name__}: {exc}")
        return 0


async def mirror() -> int:
    if not DSN:
        print("SESSION-MIRROR skipped (no AIRE_DATABASE_URL)")
        return 0
    store = await create_postgres_session_store(DSN)
    cache = load_cache()
    offered = sessions = 0
    try:
        offered, sessions = await _offer_changed(store, cache)
    finally:
        await store.close()
        save_cache(cache)
    if personas := await _offer_personas():
        append_file(f"{_now()} - CASITA-MIRROR stored {personas} persona version(s)")
        print(f"CASITA-MIRROR stored {personas} persona version(s)")
    if offered:
        append_file(f"{_now()} - SESSION-MIRROR offered {offered} entries "
                    f"from {sessions} door sessions")
    print(f"SESSION-MIRROR offered {offered} entries from {sessions} sessions")
    return offered


if __name__ == "__main__":
    asyncio.run(mirror())
