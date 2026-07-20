"""The door mirror (backlog #17): the interactive CLI's transcripts, deathless.

The SSH door (the tmux'd Claude Code TUI) writes its transcript as JSONL on the
MORTAL disk — exactly what the litmus test forbids. This mirror re-reads those
files and appends every uuid'd entry to the same Postgres store the engine
uses (`claude_session_store`), keyed the same way: project_key derived from
the entry's cwd, session_id = the file's stem. Idempotent by the store's
uuid-dedup, so re-reading whole files is safe and NO local offset state exists
to lose. Entries WITHOUT a uuid (queue-operation, ai-title, last-prompt — CLI
metadata, not transcript) are skipped: no dedup handle, no memory. Runs as a
oneshot under aire-mirror.timer (the sweep pattern); logs to the file only
when it actually offered entries, so an idle minute stays silent.
"""

import asyncio
import json
import os
from pathlib import Path

from claude_agent_sdk import project_key_for_directory

from .listen.applog import _now, append_file
from .store import create_postgres_session_store

DSN = os.environ.get("AIRE_DSN", "")
PROJECTS = Path(os.environ.get("AIRE_CLI_PROJECTS",
                               Path.home() / ".claude" / "projects"))


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


async def mirror() -> int:
    if not DSN:
        print("SESSION-MIRROR skipped (no AIRE_DSN)")
        return 0
    store = await create_postgres_session_store(DSN)
    offered, sessions = 0, 0
    try:
        for path in sorted(PROJECTS.glob("*/*.jsonl")):
            cwd, entries = read_entries(path)
            if not cwd or not entries:
                continue
            key = {"project_key": project_key_for_directory(cwd),
                   "session_id": path.stem}
            await store.append(key, entries)
            offered += len(entries)
            sessions += 1
    finally:
        await store.close()
    if offered:
        append_file(f"{_now()} - SESSION-MIRROR offered {offered} entries "
                    f"from {sessions} door sessions")
    print(f"SESSION-MIRROR offered {offered} entries from {sessions} sessions")
    return offered


if __name__ == "__main__":
    asyncio.run(mirror())
