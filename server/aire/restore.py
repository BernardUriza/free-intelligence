"""The door's resurrection (backlog #17, the restore half).

Inverse of `mirror.py`: re-materializes the CLI's JSONL transcripts from
`claude_session_store` so a FRESH box (the kill test) gets its conversations
back, not just its code. The project_key IS the CLI's dash-encoded project
dirname (verified: `project_key_for_directory` returns it), so the file lands
exactly where `claude --resume` looks: `<projects>/<project_key>/<session>.jsonl`.

Reading the table here is sanctioned exception #1 of [[write-only-daemon]] —
the agent reading its own memory to resume; restore IS resume for the door.

DISK WINS: an existing file is never touched (it may hold uuid-less metadata
and entries the mirror has not offered yet — the file is the primary, Postgres
the mirror). Only absent files are written, which makes a re-run idempotent.
jsonb normalizes key order, so restored bytes differ while entries stay
semantically identical.
"""

import asyncio
import json
import os
from pathlib import Path

from .listen.applog import _now, append_file
from .store import create_postgres_session_store

DSN = os.environ.get("AIRE_DSN", "")
PROJECTS = Path(os.environ.get("AIRE_CLI_PROJECTS",
                               Path.home() / ".claude" / "projects"))


async def session_keys(store) -> list[tuple[str, str]]:
    rows = await store._pool.fetch(
        "SELECT DISTINCT project_key, session_id "
        f"FROM {store._table} WHERE subpath = ''")
    return [(r["project_key"], r["session_id"]) for r in rows]


async def restore_one(store, project_key: str, session_id: str) -> bool:
    path = PROJECTS / project_key / f"{session_id}.jsonl"
    if path.exists():
        return False
    entries = await store.load({"project_key": project_key,
                                "session_id": session_id})
    if not entries:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return True


async def restore() -> int:
    if not DSN:
        print("SESSION-RESTORE skipped (no AIRE_DSN)")
        return 0
    store = await create_postgres_session_store(DSN)
    written = 0
    try:
        for project_key, session_id in await session_keys(store):
            if await restore_one(store, project_key, session_id):
                written += 1
    finally:
        await store.close()
    if written:
        append_file(f"{_now()} - SESSION-RESTORE rematerialized {written} "
                    "door sessions from the deathless memory")
    print(f"SESSION-RESTORE rematerialized {written} sessions")
    return written


if __name__ == "__main__":
    asyncio.run(restore())
