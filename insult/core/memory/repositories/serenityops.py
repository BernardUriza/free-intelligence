"""SerenityOps sync — snapshots + per-user bearer tokens.

Companion repository to the `/sync/serenityops` endpoint and the
`!sync-token` Discord command. Two tables, both owned here:

- `serenityops_snapshots`: append-only feed of `curriculum.yaml` +
  `opportunities/structure.yaml` payloads pushed from each user's local
  SerenityOps install. The bot reads only the latest snapshot per user
  at prompt-build time — older ones are kept for audit/recovery but
  never enter the prompt.

- `user_sync_tokens`: hashed bearer tokens. Plaintext shown to the user
  exactly once via DM; what we store is `sha256(token).hexdigest()`. A
  DB leak yields no usable credentials, and rotation is a soft-delete
  (revoked_at) + new row, so audit trails survive.
"""

from __future__ import annotations

import hashlib
import json
import time

import asyncpg
import structlog

from insult.core.memory.base import BaseRepository

log = structlog.get_logger()


def _hash_token(plain: str) -> str:
    """One-way hash for storage. SHA-256 is fine here — these are
    high-entropy random tokens (32 bytes from secrets.token_urlsafe), not
    user-chosen passwords, so a slow KDF would add latency without any
    security benefit against the threat model (DB read leak)."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


class SerenityOpsRepository(BaseRepository):
    """Owns `serenityops_snapshots` and `user_sync_tokens`."""

    # -- Snapshots --

    async def insert_snapshot(
        self,
        user_id: str,
        curriculum: dict | None,
        opportunities: dict | None,
        client_version: str | None = None,
    ) -> int:
        """Append a sync payload. Returns the new snapshot id."""
        snapshot_at = time.time()
        try:
            new_id = await self._fetchval(
                "INSERT INTO serenityops_snapshots "
                "(user_id, snapshot_at, curriculum_json, opportunities_json, client_version) "
                "VALUES ($1, $2, $3::jsonb, $4::jsonb, $5) RETURNING id",
                user_id,
                snapshot_at,
                json.dumps(curriculum) if curriculum is not None else None,
                json.dumps(opportunities) if opportunities is not None else None,
                client_version,
            )
            log.info(
                "serenityops_snapshot_inserted",
                user_id=user_id,
                snapshot_id=int(new_id or 0),
                has_cv=curriculum is not None,
                has_pipeline=opportunities is not None,
            )
            return int(new_id or 0)
        except asyncpg.PostgresError as e:
            log.error("serenityops_snapshot_insert_failed", user_id=user_id, error=str(e))
            raise

    async def get_latest_snapshot(self, user_id: str) -> dict | None:
        """Latest snapshot for a user, or None if they've never synced.

        Returns the parsed JSONB columns as Python dicts (asyncpg's
        default JSONB codec decodes for us). Callers should treat the
        payload as untrusted user input even though it traversed bearer
        auth — the user controls everything in curriculum.yaml."""
        row = await self._fetchrow(
            "SELECT id, snapshot_at, curriculum_json, opportunities_json, "
            "client_version, source "
            "FROM serenityops_snapshots "
            "WHERE user_id = $1 "
            "ORDER BY snapshot_at DESC LIMIT 1",
            user_id,
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "snapshot_at": row["snapshot_at"],
            "curriculum": _decode_jsonb(row["curriculum_json"]),
            "opportunities": _decode_jsonb(row["opportunities_json"]),
            "client_version": row["client_version"],
            "source": row["source"],
        }

    # -- Sync tokens --

    async def create_token(self, user_id: str, plaintext_token: str) -> int:
        """Store a new bearer token (hashed) for `user_id`.

        Does NOT revoke prior tokens — that's a separate decision the
        caller makes via `revoke_all_for_user`. Allowing multiple live
        tokens supports operator-led rotation where you generate the new
        one, paste it into SerenityOps, and only then revoke the old.

        Returns the inserted row id.
        """
        try:
            new_id = await self._fetchval(
                "INSERT INTO user_sync_tokens (user_id, token_hash, created_at) VALUES ($1, $2, $3) RETURNING id",
                user_id,
                _hash_token(plaintext_token),
                time.time(),
            )
            log.info("sync_token_created", user_id=user_id, token_id=int(new_id or 0))
            return int(new_id or 0)
        except asyncpg.PostgresError as e:
            log.error("sync_token_create_failed", user_id=user_id, error=str(e))
            raise

    async def revoke_all_for_user(self, user_id: str) -> int:
        """Soft-delete every live token for a user. Returns the count.

        Called by `!sync-token rotate` after the new token is in place,
        and by `!sync-token revoke` to nuke access entirely."""
        now = time.time()
        tag = await self._execute(
            "UPDATE user_sync_tokens SET revoked_at = $1 WHERE user_id = $2 AND revoked_at IS NULL",
            now,
            user_id,
        )
        try:
            return int(tag.rsplit(" ", 1)[-1])
        except (ValueError, AttributeError):
            return 0

    async def resolve_token(self, plaintext_token: str) -> str | None:
        """Map a presented bearer token to its owner's user_id (or None).

        Also bumps `last_used_at` on the matching row so we can spot
        dormant tokens and rotate them. The bump is atomic with the read
        — same UPDATE ... RETURNING does both."""
        token_hash = _hash_token(plaintext_token)
        row = await self._fetchrow(
            "UPDATE user_sync_tokens SET last_used_at = $2 "
            "WHERE token_hash = $1 AND revoked_at IS NULL "
            "RETURNING user_id",
            token_hash,
            time.time(),
        )
        return row["user_id"] if row else None


def _decode_jsonb(value):
    """JSONB → Python object.

    asyncpg's default codec decodes JSONB to a Python dict/list for us,
    but the column is also nullable and we sometimes round-trip raw text
    when migrating; tolerate both shapes."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None
