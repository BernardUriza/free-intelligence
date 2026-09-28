"""The TOPIC — the third axis of the AIRE mapping (Bernard's call, 2026-08-22):
casitas *"por sesión de discord bot y por channel y por topic temporal"*.

Stage 2 shipped two axes and hardcoded the third to a constant:

    casita  = {persona_id}-{channel_id}      # the channel's SOUL
    session = "live"                          # ...forever

That constant is the defect. A Discord channel lives for YEARS, so one eternal
session means one transcript that never stops growing: every ``resume`` loads
all of it, every turn pays for it, and a conversation from three months ago
rides into today's answer. The fix keeps both existing axes exactly where they
are and gives the SESSION a life:

    casita  = {persona_id}-{channel_id}      # unchanged — the persona's living
                                             # identity (the `@base` stub plus
                                             # whatever the `persona` tool wrote
                                             # into the living half). It PERSISTS
                                             # across topics.
    session = {topic_id}                     # a topic that rolls over after a
                                             # period of channel silence.

**The topic is deliberately NOT in the casita name.** AIRE keys memory by
(project, session), so a new topic id already gets a fresh transcript inside the
SAME casita — the soul survives. Putting the topic in the casita name would fork
the living identity per topic and re-create the "N frozen copies of the persona"
problem thin birth (aire-server ``ef21e68``) exists to kill.

## Why the topic id must be durable, and where it lives

If the id were derived from in-RAM state, a redeploy — this repo deploys several
times a day — would silently fork the topic mid-conversation: same channel, same
casita, brand-new empty transcript, and the caller-replayed history folded in
again. So the anchor is PERSISTED, in one row per casita:

    aire_topics(casita PK, topic_id, last_activity_at, answered_at)

One atomic statement (``_CLAIM_SQL``) reads the row, decides rollover-or-continue
and records the new activity, all under the row's own lock — so the decision is
correct across replicas, not merely across coroutines. The id itself is minted by
the DATABASE clock (``'t' || floor(epoch(now()))``), so two runners cannot mint
two names for one topic out of clock skew.

``answered_at`` is what governs the history fold, and it is durable ON PURPOSE:
after a restart mid-topic the row says "this topic already got an answer", so the
runner does NOT re-fold history AIRE's session already holds. That closes the
bounded duplication the stage-2 backlog filed as AIRE gap #4 (no session-exists
probe) for every case where Postgres is reachable.

## The fallback, and why it degrades in the safe direction

Postgres unreachable → the claim happens in RAM (``TopicMemory``), which is the
same algorithm over this process's own mirror. A DB fault must never kill a turn
(repo law), and a blip mid-conversation continues the SAME topic because the
mirror is written on every turn. What the fallback cannot survive is a restart
while PG is down: that starts a new topic and folds history once. Logged, never
silent.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import structlog

from persona_runner.core import config

log = structlog.get_logger()

# The runner OWNS this table: it is the only reader and the only writer, and it
# is not part of the memory store's schema (`persona_core/memory/postgres_schema.sql`,
# applied by the gateway). So its DDL rides here, applied once per process on
# first use — a runner that boots before anything else still works, and a failure
# to create it degrades to the RAM path instead of killing turns.
_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS aire_topics (
    casita           TEXT PRIMARY KEY,
    topic_id         TEXT NOT NULL,
    last_activity_at DOUBLE PRECISION NOT NULL,
    answered_at      DOUBLE PRECISION
)
"""

# Decide + record in ONE statement. `ON CONFLICT DO UPDATE` takes the row lock,
# so two claims on one casita — two coroutines here, or two replicas — are
# serialized by Postgres and can never mint two topics for one channel.
#
# The clock is the SERVER's on both sides of the comparison (skew between two
# runners cannot roll a topic that is not idle), and the id is minted from that
# same clock so the name and the decision can never disagree.
#
# The `previous` CTE reads the pre-statement snapshot: exact under this repo's
# per-casita lock, and in a cross-replica race the worst case is a rollover
# LOGGED against a stale predecessor — never a wrong topic_id, which comes from
# the locked row.
_CLAIM_SQL = """
WITH previous AS (
    SELECT topic_id, last_activity_at FROM aire_topics WHERE casita = $1
), claimed AS (
    INSERT INTO aire_topics AS t (casita, topic_id, last_activity_at, answered_at)
    VALUES ($1, 't' || floor(extract(epoch from now()))::bigint, extract(epoch from now()), NULL)
    ON CONFLICT (casita) DO UPDATE SET
        topic_id = CASE
            WHEN extract(epoch from now()) - t.last_activity_at > $2 THEN EXCLUDED.topic_id
            ELSE t.topic_id END,
        answered_at = CASE
            WHEN extract(epoch from now()) - t.last_activity_at > $2 THEN NULL
            ELSE t.answered_at END,
        last_activity_at = extract(epoch from now())
    RETURNING topic_id, answered_at
)
SELECT claimed.topic_id AS topic_id,
       (claimed.answered_at IS NULL) AS needs_fold,
       previous.topic_id AS previous_topic_id,
       previous.last_activity_at AS previous_activity_at
FROM claimed LEFT JOIN previous ON TRUE
"""

# Written only after a turn SUCCEEDED. A failed turn never reached AIRE's memory,
# so it must not consume the topic's one history fold.
_MARK_SQL = """
UPDATE aire_topics SET answered_at = extract(epoch from now())
WHERE casita = $1 AND topic_id = $2
"""

_table_ready = False
# Lazily built inside the running loop, exactly like `mcp_tools.shared`'s pool
# gate: a module-level asyncio.Lock can bind to the wrong/closed loop.
_ddl_lock: asyncio.Lock | None = None


@dataclass
class TopicMemory:
    """This process's mirror of one casita's durable topic row.

    Two jobs, and only two: it is the FALLBACK when Postgres is unreachable, and
    it remembers that THIS process already answered inside ``topic_id`` — so a
    lost ``mark_answered`` write cannot make the next turn fold the history a
    second time. It is never the primary source: a mirror that outranked the row
    would put the topic back in RAM and re-open the restart fork this whole
    module exists to close.
    """

    topic_id: str = ""
    last_activity: float = 0.0
    answered: bool = False


@dataclass(frozen=True)
class TopicClaim:
    """The decision for one turn: which topic it lands in and what that means."""

    topic_id: str
    # True ⇔ AIRE's session for this topic holds nothing yet, so the
    # caller-replayed history must be folded into THIS turn's message.
    needs_fold: bool
    # True ⇔ this claim minted the id (a fresh channel, or a rollover).
    opened: bool
    previous_topic_id: str
    idle_s: float
    # False ⇔ the decision was made in RAM because Postgres was unreachable.
    durable: bool

    @property
    def rolled_over(self) -> bool:
        """A ROLLOVER is an opening that replaced a previous topic. The first
        topic a casita ever gets is an opening, not a rollover — reporting it as
        one would put a context-reset event in the log where no context was
        reset."""
        return self.opened and bool(self.previous_topic_id)


def topic_name(anchor_epoch: float) -> str:
    """A topic id: ``t<epoch seconds of the moment the topic opened>``.

    Deterministic, sortable, human-readable in a log line, and inside AIRE's
    session-name allowlist (``[A-Za-z0-9_-]``). Same FORM the SQL mints, so a
    turn decided in the RAM fallback and a turn decided in Postgres are
    indistinguishable downstream.
    """
    return f"t{int(anchor_epoch)}"


def _get_ddl_lock() -> asyncio.Lock:
    global _ddl_lock
    if _ddl_lock is None:
        _ddl_lock = asyncio.Lock()
    return _ddl_lock


async def _ensure_table(conn) -> None:
    """Create the topic table once per process. Left un-flagged on failure, so
    the next turn retries instead of falling back to RAM forever."""
    global _table_ready
    if _table_ready:
        return
    async with _get_ddl_lock():
        if _table_ready:
            return
        await conn.execute(_TABLE_DDL)
        _table_ready = True


async def _claim_durable(casita: str, window_s: float):
    """The atomic claim against Postgres, or ``None`` when it cannot be made.

    ``None`` is never an exception: a DB fault degrades the turn to the RAM
    path, it does not kill it (repo law, same contract as the fact pre-fetch).
    """
    from persona_runner.mcp_tools import shared

    try:
        async with shared.acquire() as conn:
            if conn is None:
                return None
            await _ensure_table(conn)
            return await conn.fetchrow(_CLAIM_SQL, casita, window_s)
    except Exception:
        log.exception("aire_topic_claim_failed", casita=casita)
        return None


def _claim_in_ram(memory: TopicMemory, now: float, window_s: float) -> TopicClaim:
    """The same decision over this process's mirror — the Postgres-is-down path."""
    previous_topic = memory.topic_id
    idle_s = now - memory.last_activity if memory.last_activity else 0.0
    opened = not previous_topic or idle_s > window_s
    return TopicClaim(
        topic_id=topic_name(now) if opened else previous_topic,
        needs_fold=True if opened else not memory.answered,
        opened=opened,
        previous_topic_id=previous_topic,
        idle_s=idle_s,
        durable=False,
    )


async def claim(casita: str, memory: TopicMemory, *, now: float | None = None) -> TopicClaim:
    """Decide which topic this turn lands in, and record the activity.

    MUST be called under the casita's lock (``aire_route.CasitaState.lock``):
    two messages arriving together in one Discord channel have to land in the
    SAME topic, and the fold has to happen exactly once. Postgres serializes the
    row, but the lock is what makes the decide→turn→mark window atomic for the
    turn that follows it.
    """
    window_s = config.AIRE_TOPIC_IDLE_TIMEOUT_S
    now = time.time() if now is None else now
    row = await _claim_durable(casita, window_s)
    decision = _from_row(row, now, window_s) if row is not None else _claim_in_ram(memory, now, window_s)
    return _reconcile(decision, memory, now)


def _from_row(row, now: float, window_s: float) -> TopicClaim:
    """Read the atomic claim's RETURNING row into a decision."""
    previous_topic = row["previous_topic_id"] or ""
    previous_activity = row["previous_activity_at"]
    topic_id = row["topic_id"]
    return TopicClaim(
        topic_id=topic_id,
        needs_fold=bool(row["needs_fold"]),
        opened=topic_id != previous_topic,
        previous_topic_id=previous_topic,
        idle_s=(now - float(previous_activity)) if previous_activity is not None else 0.0,
        durable=True,
    )


def _reconcile(decision: TopicClaim, memory: TopicMemory, now: float) -> TopicClaim:
    """Intersect the decision with this process's mirror, then refresh it.

    The only thing the mirror may VETO is a fold: if this process already
    answered inside the very same topic, a ``mark_answered`` write that never
    landed must not buy a second fold. It can never veto the topic id — that
    would be RAM outranking the durable row again.
    """
    answered_here = bool(memory.topic_id) and memory.topic_id == decision.topic_id and memory.answered
    reconciled = (
        decision
        if not (answered_here and decision.needs_fold)
        else TopicClaim(
            topic_id=decision.topic_id,
            needs_fold=False,
            opened=decision.opened,
            previous_topic_id=decision.previous_topic_id,
            idle_s=decision.idle_s,
            durable=decision.durable,
        )
    )
    memory.topic_id = reconciled.topic_id
    memory.last_activity = now
    memory.answered = not reconciled.needs_fold
    return reconciled


async def mark_answered(casita: str, topic_id: str, memory: TopicMemory) -> None:
    """Record that a turn in this topic was ANSWERED — the durable half of the
    history fold. Called only after the door returned a result, so a failed turn
    leaves the topic unanswered and the retry still carries the thread.

    Best-effort against Postgres, always applied to the mirror: a write that
    fails costs at most one extra fold after a restart, never a dead turn.
    """
    memory.answered = True
    from persona_runner.mcp_tools import shared

    try:
        async with shared.acquire() as conn:
            if conn is None:
                return
            await conn.execute(_MARK_SQL, casita, topic_id)
    except Exception:
        log.exception("aire_topic_mark_failed", casita=casita, topic=topic_id)


_RESET_SQL = """
DELETE FROM aire_topics WHERE casita LIKE '%-' || $1 RETURNING casita
"""


async def reset_channel(cleaned_channel: str) -> list[str] | None:
    """Durable half of a channel reset: drop every persona's topic row for the
    channel, so each casita's NEXT claim mints a fresh topic and folds history
    anew — the AIRE-route equivalent of force-closing the pooled SDK sessions.

    ``cleaned_channel`` must already be filtered to AIRE's name allowlist (the
    caller owns the casita naming). Returns the casitas whose rows were dropped,
    or ``None`` when Postgres is unreachable — a reset that could not be made
    durable must be REPORTED as such, never silently equated with one that was.
    """
    from persona_runner.mcp_tools import shared

    escaped = cleaned_channel.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
    try:
        async with shared.acquire() as conn:
            if conn is None:
                return None
            await _ensure_table(conn)
            rows = await conn.fetch(_RESET_SQL, escaped)
            return [r["casita"] for r in rows]
    except Exception:
        log.exception("aire_topic_reset_failed", channel=cleaned_channel)
        return None
