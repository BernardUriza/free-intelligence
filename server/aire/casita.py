"""The casita's identity, deathless — the half of #36 that died with the box.

The transcript has been immortal since day one: it lives in the owner's Postgres,
and a session revives by name from any device, through a process that never met
it. Verified 2026-08-22 by killing the daemon between two turns and watching the
second one answer from the first one's memory.

The casita's ``CLAUDE.md`` was not. It lives on ``/opt/aire/workspaces/<casita>/``
— the droplet's mortal disk — written by the ``init`` endpoint (the protected
base) and by the persona tool (the living half the agent writes about itself,
#36). ``restore.py`` resurrects the SSH door's JSONL and nothing resurrected
this, so a fresh box would bring every casita back **remembering everything that
was said and having forgotten who it is.** That is exactly the litmus test in
CLAUDE.md — *does this give the agent a body back? then no* — failing on the one
file that holds the soul.

Same two verbs as the door (Art. 6 — the pattern is proven, do not invent a
third): ``offer`` pushes a changed file to Postgres, ``restore`` re-materializes
an absent one. **DISK WINS** on restore, identically: an existing file is never
touched, so a re-run is idempotent and a live persona is never clobbered by an
older copy.

**Append-only, like everything else here.** A persona is REWRITTEN over its life,
and [[log-is-the-truth]] forbids mutating what is stored — so each version is a
new row and "current" is the newest. That is not extra bookkeeping: the history
of how a casita rewrote itself is precisely what #36 is about, and it comes free.

Created as role ``aire``, so the reader's default-privileges grant covers it
([[write-only-daemon]]). Reading it back in ``restore`` is the same sanctioned
exception the door's restore already is: the agent recovering its own memory.
"""

from __future__ import annotations

import os
from pathlib import Path

from .agent_sdk import project_key_for_directory

from .engine.core import WORKSPACES

DDL = """
CREATE TABLE IF NOT EXISTS aire_casita (
  seq         bigserial PRIMARY KEY,
  ts          timestamptz NOT NULL DEFAULT now(),
  project_key text NOT NULL,
  casita      text NOT NULL,
  claude_md   text NOT NULL,
  stamp       double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS aire_casita_key_idx ON aire_casita (project_key, seq DESC);
"""


class NoWorkspaces(Exception):
    """The casitas are not where this process is looking.

    It exists because the silent version of this bit within an hour of shipping:
    `aire-mirror.service` did not carry `AIRE_WORKSPACES`, so `WORKSPACES`
    resolved to a directory that does not exist, `glob` found nothing, and the
    mirror reported ZERO as if there were simply no personas yet. That is the
    disease #40 is about — a guard that degrades politely and says nothing —
    reproduced by the very commit that was fixing it. An absent directory is not
    an empty one, and restore must never write a soul into a path nobody reads.
    """


def on_disk() -> list[tuple[str, str, Path]]:
    """Every casita that HAS a persona: (project_key, name, path). A workspace
    without a CLAUDE.md has no identity to keep — but a missing WORKSPACES root
    is a misconfiguration, and it raises rather than reading as 'none'."""
    if not WORKSPACES.is_dir():
        raise NoWorkspaces(f"{WORKSPACES} does not exist — is AIRE_WORKSPACES set?")
    found = []
    for path in sorted(WORKSPACES.glob("*/CLAUDE.md")):
        directory = path.parent
        found.append((project_key_for_directory(str(directory)), directory.name, path))
    return found


async def offer(conn) -> int:
    """Append every persona whose file changed since its newest stored version.
    The stamp comparison is what keeps an idle minute silent and the table from
    growing a row per tick."""
    await conn.execute(DDL)
    written = 0
    for project_key, name, path in on_disk():
        stamp = path.stat().st_mtime
        newest = await conn.fetchval(
            "SELECT stamp FROM aire_casita WHERE project_key = $1 ORDER BY seq DESC LIMIT 1",
            project_key)
        if newest is not None and abs(newest - stamp) < 1e-6:
            continue
        await conn.execute(
            "INSERT INTO aire_casita (project_key, casita, claude_md, stamp)"
            " VALUES ($1, $2, $3, $4)",
            project_key, name, path.read_text(encoding="utf-8"), stamp)
        written += 1
    return written


async def restore(conn) -> int:
    """Re-materialize the newest version of every persona whose file is absent.
    DISK WINS: a file that exists is left alone, because it may already be newer
    than anything Postgres has seen."""
    if not WORKSPACES.is_dir():
        raise NoWorkspaces(f"{WORKSPACES} does not exist — restoring there would "
                           "write every soul into a path nobody reads")
    await conn.execute(DDL)
    rows = await conn.fetch(
        "SELECT DISTINCT ON (project_key) casita, claude_md FROM aire_casita"
        " ORDER BY project_key, seq DESC")
    written = 0
    for row in rows:
        directory = WORKSPACES / row["casita"]
        path = directory / "CLAUDE.md"
        if path.exists():
            continue
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(row["claude_md"], encoding="utf-8")
        written += 1
    return written


def dsn() -> str:
    return os.environ.get("AIRE_DATABASE_URL", "")
