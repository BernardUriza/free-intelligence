"""The per-account conversation records: list, read, upsert, organize, delete."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from fi_runner.auth import Principal
import deps
from conversations import ConversationStore, valid_conversation_id
from deps import get_conversation_store, get_principal, logger

router = APIRouter()

# Ceiling on one persisted conversation, so a runaway thread is rejected instead of growing an unbounded file.
# 16 MB because attached images persist base64-inline in the record.
MAX_CONVERSATION_BYTES = 16 * 1024 * 1024


class ConversationRecordRequest(BaseModel):
    """The core ConversationRecord shape (fi-glass sanitizes upstream: messages
    carry role/content/timestamp/trace only, never auth metadata). Extra fields
    are dropped by pydantic — the same invariant as ProjectCreateRequest."""

    id: str
    title: str
    titleCustom: bool | None = None
    createdAt: str
    updatedAt: str
    messages: list[dict]
    preview: str
    # Organization flags (ISO timestamps), dumped with exclude_none: omitting one clears it from the stored record.
    pinnedAt: str | None = None
    archivedAt: str | None = None
    # The project this conversation lives in (the corpus_id bound on its turns), stored so a project can list its own chats.
    # Omitted for a conversation outside any project.
    projectId: str | None = None
    schemaVersion: int


@router.get("/conversations")
async def list_conversations(
    projectId: str | None = None,
    principal: Principal = Depends(get_principal),
    store: ConversationStore = Depends(get_conversation_store),
) -> dict:
    """The caller's conversations as light summaries, newest first (sidebar).

    ``?projectId=`` narrows it to one project — the "Recents" list of the project
    detail page. Filtered here rather than in the client because the client would
    otherwise download every conversation in the account to show the handful that
    belong to the project it is looking at.
    """
    conversations = store.list_for(principal.sub)
    if projectId is not None:
        conversations = [c for c in conversations if c.get("projectId") == projectId]
    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    principal: Principal = Depends(get_principal),
    store: ConversationStore = Depends(get_conversation_store),
) -> dict:
    """One full record. Ownership is structural (per-owner directory), so a
    foreign id is indistinguishable from a missing one — 404, never 403."""
    record = store.get(principal.sub, conversation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return record


@router.put("/conversations/{conversation_id}")
async def put_conversation(
    conversation_id: str,
    record: ConversationRecordRequest,
    principal: Principal = Depends(get_principal),
    store: ConversationStore = Depends(get_conversation_store),
) -> dict:
    """Upsert the record under the caller's account. The path id is canonical
    (a body id that disagrees is rejected — no writing conversation A while
    addressing conversation B)."""
    if not valid_conversation_id(conversation_id):
        raise HTTPException(status_code=422, detail="invalid conversation id")
    if record.id != conversation_id:
        raise HTTPException(status_code=422, detail="body id does not match path id")
    payload = record.model_dump(exclude_none=True)
    if len(json.dumps(payload)) > MAX_CONVERSATION_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "CONVERSATION_TOO_LARGE",
                "message": f"conversation exceeds the {MAX_CONVERSATION_BYTES // (1024 * 1024)} MB limit",
            },
        )
    store.put_content(principal.sub, payload)
    return {"id": conversation_id}


class ConversationMetadataPatchRequest(BaseModel):
    """A metadata-only delta: rename / pin / archive.

    Mirrors core's `ConversationMetadataPatch`. The three-way distinction is
    load-bearing and pydantic gives it for free through `exclude_unset`: a key
    that is ABSENT leaves the field alone, a key set to `null` CLEARS it, a value
    sets it. A whole-record PUT cannot express that — an absent field and a
    deliberately-cleared one look identical — which is exactly why pinning could
    be lost by a device that simply did not know about the pin.
    """

    title: str | None = None
    titleCustom: bool | None = None
    pinnedAt: str | None = None
    archivedAt: str | None = None
    updatedAt: str | None = None


@router.patch("/conversations/{conversation_id}")
async def patch_conversation(
    conversation_id: str,
    patch: ConversationMetadataPatchRequest,
    principal: Principal = Depends(get_principal),
    store: ConversationStore = Depends(get_conversation_store),
) -> dict:
    """Move a conversation's organization flags without shipping the record.

    This is the ONLY way pin / archive / rename change now: `PUT` preserves the
    stored flags, so the two-device race that silently dropped a pin has no
    surface left to happen on. The updated record comes back so the caller syncs
    from the server's merge rather than from its own optimistic guess.

    404 for a record the caller does not own — structural, same as `GET`: a
    foreign id is indistinguishable from a missing one, so nothing can be probed.
    """
    if not valid_conversation_id(conversation_id):
        raise HTTPException(status_code=422, detail="invalid conversation id")
    delta = patch.model_dump(exclude_unset=True)
    if not delta:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_PATCH", "message": "no fields to update"},
        )
    # `title` is the one field whose null is meaningless: a conversation always
    # has a title. Reverting a rename sends the DERIVED title, not a clear.
    if "title" in delta and delta["title"] is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "TITLE_REQUIRED", "message": "title cannot be null"},
        )
    record = store.patch_metadata(principal.sub, conversation_id, delta)
    if record is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return record


async def _forget_native_session(conversation_id: str) -> None:
    """Cascade a visible delete into the native transcript underneath it.

    The conversation id IS the session id og118 hands the runner, so the store
    key is derivable — no mapping table (`ClaudeCodeBackend.sdk_session_uuid`).

    BEST EFFORT, and loudly so, mirroring the lifespan's posture: the memory
    layer never blocks a user-visible action. A dead Postgres must not turn
    "delete my chat" into a 500 — the record is already gone and the user is
    owed that answer. What it must never do is fail in silence, because the
    residue is a full transcript nobody can reach any more.
    """
    try:
        await deps.base_runner().forget_session(conversation_id)
    except Exception:
        logger.exception(
            "conversation %s was deleted but its native session survived — "
            "orphan transcript in the session store",
            conversation_id,
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    principal: Principal = Depends(get_principal),
    store: ConversationStore = Depends(get_conversation_store),
) -> dict:
    """Remove one conversation (no-op if absent — mirrors the client library
    contract, and leaks nothing about other accounts' ids), and the native
    session under it."""
    store.delete(principal.sub, conversation_id)
    await _forget_native_session(conversation_id)
    return {"deleted": conversation_id}


@router.delete("/conversations")
async def clear_conversations(
    principal: Principal = Depends(get_principal),
    store: ConversationStore = Depends(get_conversation_store),
) -> dict:
    """Remove every conversation the caller owns (the library `clear()`), and
    every native session under them.

    The ids are read BEFORE the clear — afterwards there is nothing left to
    derive them from, and this is the surface where the leak multiplies by the
    whole account instead of by one chat.
    """
    ids = [c["id"] for c in store.list_for(principal.sub) if c.get("id")]
    cleared = store.clear_for(principal.sub)
    for conversation_id in ids:
        await _forget_native_session(conversation_id)
    return {"cleared": cleared}
