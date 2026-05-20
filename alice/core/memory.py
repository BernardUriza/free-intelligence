"""ALICE shares Insult's Postgres data plane.

Same DSN (`POSTGRES_URL`), same `messages` table, same `user_facts` and
`serenityops_snapshots`. ALICE READS the conversation Insult is in
(otherwise she'd respond blind when Insult invites her). ALICE WRITES
her own replies as `role='assistant'` with `user_name='ALICE'` so the
audit history distinguishes Insult's voice from hers cleanly.

Why not a separate Postgres or a separate schema:
- The whole point of ALICE is that she sees the same conversation Insult
  saw. A separate DB would require ETL or cross-DB queries to give her
  context — added complexity for zero gain.
- The `messages` table is append-only by design. Two writers (Insult +
  ALICE) is fine. Postgres MVCC handles it natively; no SQLite-style
  single-writer constraint.

What ALICE deliberately does NOT do:
- Doesn't touch `user_facts` (read-only). Fact extraction is Insult's
  responsibility; her decisions about what to extract reflect her
  identity. ALICE adopting Insult's facts is fine; rewriting them isn't.
- Doesn't write to `disclosure_log`, `emotional_arcs`, `stance_log` —
  those are Insult's relational state ledger. Mixing ALICE's reads into
  them would confuse Insult's flow analysis.
"""

from __future__ import annotations

import time

import asyncpg
import structlog

from alice.config import settings

log = structlog.get_logger()


class AliceMemory:
    """Thin asyncpg wrapper for ALICE's reads + write of her own replies."""

    def __init__(self, postgres_url: str | None = None):
        self._postgres_url = postgres_url or settings.postgres_url
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Open the pool. Idempotent — safe to call multiple times."""
        if self._pool is not None:
            return
        self._pool = await asyncpg.create_pool(
            dsn=self._postgres_url,
            min_size=1,
            max_size=4,  # ALICE is much lower volume than Insult; small pool is enough
            command_timeout=30,
        )
        log.info("alice_memory_connected", pool_max=4)

    async def close(self) -> None:
        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None
        log.info("alice_memory_closed")

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("AliceMemory.connect() not called")
        return self._pool

    async def get_recent_messages(self, channel_id: str, limit: int | None = None) -> list[dict]:
        """Pull the last N messages from the channel (chronological order).

        Used at /invite or @mention time to build the conversation
        ALICE is about to enter. Returns OpenAI-ready dicts:

            [{"role": "user"|"assistant", "content": "..."}]

        We collapse the original `user_name` / `for_user_id` / metadata
        because OpenAI's chat API doesn't care — only role + content
        matter. If audit needs richer attribution later, store the raw
        rows separately.
        """
        n = limit if limit is not None else settings.memory_recent_limit
        rows = await self.pool.fetch(
            "SELECT user_name, role, content, timestamp FROM messages "
            "WHERE channel_id = $1 ORDER BY timestamp DESC LIMIT $2",
            channel_id,
            n,
        )
        # Reverse so the LLM sees oldest → newest, the way humans read.
        # Prepend speaker labels to `content` because OpenAI's chat schema
        # doesn't have a place for them — the bot needs them to
        # distinguish Bernard from Alex inside a single `role: user`.
        out: list[dict] = []
        for r in reversed(rows):
            label = r["user_name"] or "?"
            # ALICE's own past replies are the ONLY genuine assistant turns
            # from her point of view. Everyone else — humans AND the sibling
            # bot Insult (which also writes role='assistant' into this shared
            # table, distinguished only by user_name) — must become role='user'
            # with a speaker label. If Insult's row stays role='assistant' and
            # it is the LAST message, gpt-4.1 treats it as an assistant prefill
            # and continues its sentence instead of replying — the mid-word
            # "gar con la película" bug (2026-05-20), which fired because
            # Insult's last chunk had been truncated at "...necesitas lle".
            is_alice_own = r["role"] == "assistant" and label == "ALICE"
            if is_alice_own:
                out.append({"role": "assistant", "content": r["content"]})
            else:
                out.append({"role": "user", "content": f"{label}: {r['content']}"})
        return out

    async def store_user_message(
        self,
        *,
        channel_id: str,
        user_id: str,
        user_name: str,
        content: str,
        guild_id: str | None = None,
        channel_name: str | None = None,
    ) -> None:
        """Persist an inbound message from a Discord user.

        In server channels Insult handles this — it sees every message in
        the shared guild and writes a row before ALICE even runs. In DMs
        Insult is NOT present (DMs are 1:1 with whichever bot the user
        opened a thread with), so if ALICE doesn't persist the user's
        message herself, the next turn's `get_recent_messages` will be
        missing the user's side and the conversation effectively has no
        memory. Idempotency is best-effort: same channel/user/timestamp
        combo from Insult and ALICE both writing would create a duplicate,
        but in practice DMs only flow through ALICE so this doesn't fire
        in server channels.
        """
        try:
            await self.pool.execute(
                "INSERT INTO messages (channel_id, user_id, user_name, role, content, "
                "timestamp, guild_id, channel_name) "
                "VALUES ($1, $2, $3, 'user', $4, $5, $6, $7)",
                channel_id,
                user_id,
                user_name,
                content,
                time.time(),
                guild_id,
                channel_name,
            )
        except asyncpg.PostgresError as e:
            log.error("alice_memory_store_user_failed", channel_id=channel_id, error=str(e))
            raise

    async def store_response(
        self,
        channel_id: str,
        content: str,
        *,
        guild_id: str | None = None,
        channel_name: str | None = None,
        for_user_id: str | None = None,
    ) -> None:
        """Persist ALICE's reply into the shared `messages` table.

        `user_name='ALICE'` distinguishes her turns from Insult's in
        future reads (Insult writes `user_name='Insult'`). `user_id` we
        set to the literal string `'alice'` so foreign-key-less joins
        keep working — Postgres TEXT column, no UUID requirement.
        """
        try:
            await self.pool.execute(
                "INSERT INTO messages (channel_id, user_id, user_name, role, content, "
                "timestamp, for_user_id, guild_id, channel_name, model_used) "
                "VALUES ($1, 'alice', 'ALICE', 'assistant', $2, $3, $4, $5, $6, $7)",
                channel_id,
                content,
                time.time(),
                for_user_id,
                guild_id,
                channel_name,
                settings.azure_openai_gpt_deployment,
            )
        except asyncpg.PostgresError as e:
            # Same posture as Insult's `MessagesRepository.store` —
            # log + raise so the caller can decide whether to surface
            # the failure to the user or proceed without the audit row.
            log.error("alice_memory_store_failed", channel_id=channel_id, error=str(e))
            raise

    async def get_user_facts(self, user_id: str) -> list[dict]:
        """Read-only access to Insult's `user_facts` for the given user.

        Used so ALICE arrives knowing what Insult already learned about
        Bernard / Alex. Soft-deleted rows excluded (same predicate as
        Insult's `FactsRepository.get_facts`).
        """
        rows = await self.pool.fetch(
            "SELECT fact, category FROM principal_facts "
            "WHERE principal_id = $1 AND deleted_at IS NULL ORDER BY updated_at DESC",
            user_id,
        )
        return [{"fact": r["fact"], "category": r["category"]} for r in rows]
