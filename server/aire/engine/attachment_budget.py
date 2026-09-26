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

import asyncio
import base64
from typing import Any

from .. import db
from .documents import MAX_PDF_PAGES, BadDocument, pdf_pages

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


_PDF_SQL = """
SELECT block->'source'->>'data' AS data
FROM claude_session_store s,
     jsonb_array_elements(CASE WHEN jsonb_typeof(s.entry->'message'->'content') = 'array'
                               THEN s.entry->'message'->'content' ELSE '[]'::jsonb END) block
WHERE s.project_key = $1 AND s.session_id = $2 AND s.subpath = ''
  AND block->>'type' = 'document' AND block->'source'->>'media_type' = 'application/pdf'
"""


class OverBudget(Exception):
    """The session cannot take these attachments — the caller's 422 detail."""


def check(held: int, held_bytes: int, adding_images: int, adding_bytes: list[int]) -> None:
    """Refuse when the session plus this turn's attachments would pass either cap."""
    count, size = held + adding_images, held_bytes + sum(adding_bytes)
    if count > MAX_SESSION_IMAGES or size > MAX_SESSION_BYTES:
        raise OverBudget(
            f"session attachment budget: it already carries {held} images and "
            f"{held_bytes / 1e6:.1f} MB of attachments, and every turn resends them; "
            f"caps are {MAX_SESSION_IMAGES} images / {MAX_SESSION_BYTES / 1e6:.0f} MB. "
            "Start a new session.")


async def precheck(project_key: str, session_id: str, declared_images: int) -> None:
    """Refuse from the counts alone, before a byte is fetched: a session that is
    already full cannot be made to pay for downloads it will refuse anyway."""
    n, size = await held(project_key, session_id)
    check(n, size, declared_images, [])


async def _rows(sql: str, project_key: str, session_id: str) -> list[Any]:
    """The session's rows for `sql`. File-only mode or no store table → none."""
    if not db.dsn():
        return []
    from asyncpg.exceptions import UndefinedTableError
    try:
        async with db.acquire(statement_timeout_ms=_STATEMENT_TIMEOUT_MS) as conn:
            return list(await conn.fetch(sql, project_key, session_id))
    except UndefinedTableError:
        return []  # no store table yet (fresh box, CI): no session holds anything


async def held(project_key: str, session_id: str) -> tuple[int, int]:
    """`(images, attachment chars)` already in the session."""
    rows = await _rows(_SQL, project_key, session_id)
    return (int(rows[0]["n"]), int(rows[0]["b64"])) if rows else (0, 0)


def _pages(b64_blobs: list[str]) -> int:
    total = 0
    for blob in b64_blobs:
        try:
            total += pdf_pages(base64.b64decode(blob))
        except BadDocument:
            continue  # accepted once, unreadable now: it cannot be counted, only carried
    return total


async def check_pdf_pages(project_key: str, session_id: str, new_pdfs: list[str]) -> None:
    """History is resent, so the API's page cap binds the SESSION: only a turn
    that adds a PDF can grow the sum, and only such a turn pays for this read."""
    if not new_pdfs:
        return
    rows = await _rows(_PDF_SQL, project_key, session_id)
    held_pages, adding = await asyncio.to_thread(
        lambda: (_pages([r["data"] for r in rows]), _pages(new_pdfs)))
    if held_pages + adding > MAX_PDF_PAGES:
        raise OverBudget(
            f"session PDF budget: it already carries {held_pages} PDF pages and this turn adds "
            f"{adding}; every turn resends them and the cap is {MAX_PDF_PAGES}. Start a new session.")


def _is_pdf(block: dict[str, Any]) -> bool:
    return block["type"] == "document" and block["source"].get("media_type") == "application/pdf"


async def enforce(project_key: str, session_id: str, attachments: tuple[dict[str, Any], ...]) -> None:
    if attachments:
        n, size = await held(project_key, session_id)
        images = sum(1 for block in attachments if block["type"] == "image")
        check(n, size, images, [len(block["source"]["data"]) for block in attachments])
        await check_pdf_pages(project_key, session_id,
                              [b["source"]["data"] for b in attachments if _is_pdf(b)])
