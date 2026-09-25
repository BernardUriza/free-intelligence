"""How many attachment bytes a session may carry (#50) — images and documents.

Every turn resends the session's whole history, attachments included, against a
32 MB request limit — so an image is paid on EVERY later turn, not once. Today
the heaviest session holds 4 images / ~2 MB and nothing has hit the wall, but
only because the consumers rotate sessions often. The cap belongs to the door
that builds the request, so it lives here and not by accident in a consumer.

The read is the agent's own transcript in `claude_session_store`, feeding a
gate that decides whether a turn is spent — the machine-facing read
[[write-only-daemon]] allows, never a view. Native sessions only: an ACP
session's history lives in AIRE's mirror, which this does not count."""

from typing import Any

from .. import db

MAX_SESSION_IMAGES = 100  # the API's per-request image cap
MAX_SESSION_BYTES = 24_000_000  # base64/text of every attachment, of the 32 MB request
_STATEMENT_TIMEOUT_MS = 3_000

_SQL = """
SELECT count(*) FILTER (WHERE block->>'type' = 'image') AS n,
       coalesce(sum(length(block->'source'->>'data')), 0) AS b64
FROM claude_session_store s,
     jsonb_array_elements(CASE WHEN jsonb_typeof(s.entry->'message'->'content') = 'array'
                               THEN s.entry->'message'->'content' ELSE '[]'::jsonb END) block
WHERE s.project_key = $1 AND s.session_id = $2 AND s.subpath = ''
  AND block->>'type' IN ('image', 'document')
"""


class OverBudget(Exception):
    """The session cannot take these images — the caller's 422 detail."""


def check(held: int, held_bytes: int, adding_images: int, adding_bytes: list[int]) -> None:
    """Refuse when the session plus this turn's attachments would pass either cap."""
    count, size = held + adding_images, held_bytes + sum(adding_bytes)
    if count > MAX_SESSION_IMAGES or size > MAX_SESSION_BYTES:
        raise OverBudget(
            f"session attachment budget: it already carries {held} images and "
            f"{held_bytes / 1e6:.1f} MB of attachments, and every turn resends them; "
            f"caps are {MAX_SESSION_IMAGES} images / {MAX_SESSION_BYTES / 1e6:.0f} MB. "
            "Start a new session.")


async def held(project_key: str, session_id: str) -> tuple[int, int]:
    """`(images, attachment chars)` already in the session. File-only mode → (0, 0)."""
    if not db.dsn():
        return 0, 0
    async with db.acquire(statement_timeout_ms=_STATEMENT_TIMEOUT_MS) as conn:
        row: Any = await conn.fetchrow(_SQL, project_key, session_id)
    return int(row["n"]), int(row["b64"])


async def enforce(project_key: str, session_id: str, attachments: tuple[dict[str, Any], ...]) -> None:
    if attachments:
        n, size = await held(project_key, session_id)
        images = sum(1 for block in attachments if block["type"] == "image")
        check(n, size, images, [len(block["source"]["data"]) for block in attachments])
