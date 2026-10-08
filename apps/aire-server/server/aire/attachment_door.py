"""The attachment customs (#50) — what a turn's images and documents must pass
before a single dollar, or a single megabyte of this box's RAM, is spent.

Split from `intake.py` because an attachment is not a field: it is a fetch, a
decode and a weight, and the ORDER of those is the whole point. The adversarial
review of 2026-09-25 found the expensive half running before its gates:

1. **Shape first** — a malformed list costs nothing to refuse.
2. **Session weight BEFORE the fetch** — a session already at its cap is refused
   from the counts alone, so hammering it with turns that can only fail no
   longer buys a download and a decode each time.
3. **One fetch-and-decode at a time, box-wide.** The engine's RAM semaphore
   (`pool.slot()`) only wraps the turn; the attachments were prepared before it,
   so N concurrent requests decoded N images at once on a ~186 MB box. This gate
   is its own, waited on with a timeout, never skipped.
4. **The final weight** once the real sizes are known."""

import asyncio
from typing import Any

from fastapi import HTTPException

from .agent_sdk import DEFAULT_PROVIDER
from .engine import attachment_budget
from .engine.documents import BadDocument, clean_documents, prepare_documents
from .engine.vision import BadImage, clean_images, prepare_images

PREP_WAIT_S = 30.0
_prep_gate: asyncio.Semaphore | None = None


def _gate() -> asyncio.Semaphore:
    global _prep_gate
    if _prep_gate is None:
        _prep_gate = asyncio.Semaphore(1)
    return _prep_gate


def _shapes(images: Any, documents: Any) -> int:
    """How many images the turn declares — raising 422 on a malformed list."""
    try:
        clean_documents(documents)
        return len(clean_images(images))
    except (BadImage, BadDocument) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _weigh(check: Any) -> None:
    try:
        await check
    except attachment_budget.OverBudget as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # the store is unreachable: refuse loud, never guess the weight
        raise HTTPException(status_code=503,
                            detail=f"session attachment budget unreadable: {type(exc).__name__}") from exc


async def _prepare(images: Any, documents: Any, provider: str) -> tuple[dict[str, Any], ...]:
    try:
        async with asyncio.timeout(PREP_WAIT_S):
            await _gate().acquire()
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail="attachment gate busy; retry") from exc
    try:
        blocks = await prepare_images(images) + await prepare_documents(documents)
    except (BadImage, BadDocument) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        _gate().release()
    if provider != DEFAULT_PROVIDER and any(b["type"] == "document" and b["source"]["type"] == "base64"
                                            for b in blocks):
        raise HTTPException(status_code=422, detail=f"PDF documents need the {DEFAULT_PROVIDER} provider")
    return blocks


async def safe_attachments(images: Any, documents: Any, key: dict[str, str],
                           provider: str = DEFAULT_PROVIDER) -> tuple[dict[str, Any], ...]:
    """The turn's attachments as ready content blocks, or the HTTP refusal."""
    if not images and not documents:
        return ()
    declared = _shapes(images, documents)
    pk, sid = key["project_key"], key["session_id"]
    await _weigh(attachment_budget.precheck(pk, sid, declared))
    blocks = await _prepare(images, documents, provider)
    await _weigh(attachment_budget.enforce(pk, sid, blocks))
    return blocks
