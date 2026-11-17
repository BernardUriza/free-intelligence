"""The per-account file door: upload, list, download, delete."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from fi_runner.auth import Principal
from conversations import valid_conversation_id
from deps import get_file_store, get_principal
from files import FileStore, FileTooLarge, QuotaExceeded

router = APIRouter()

MAX_CONTENT_TYPE_CHARS = 120


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


@router.post("/files")
async def upload_file(
    request: Request,
    name: str,
    conversationId: str | None = None,
    principal: Principal = Depends(get_principal),
    store: FileStore = Depends(get_file_store),
) -> dict:
    """Store the raw request body as one file of the caller's account.

    The body IS the file (no multipart), so it streams to disk and a large
    upload is never resident in memory.
    """
    if conversationId is not None and not valid_conversation_id(conversationId):
        raise HTTPException(status_code=422, detail="invalid conversation id")
    content_type = request.headers.get("content-type", "application/octet-stream")
    limits = store.usage(principal.sub)
    try:
        return await store.save(
            principal.sub, name, content_type[:MAX_CONTENT_TYPE_CHARS], request.stream(), conversationId
        )
    except FileTooLarge:
        megabytes = limits["maxFileBytes"] // (1024 * 1024)
        raise _error(413, "FILE_TOO_LARGE", f"file exceeds the {megabytes} MB limit") from None
    except QuotaExceeded:
        raise _error(413, "FILE_QUOTA_EXCEEDED", "the account's file storage is full") from None


@router.get("/files")
async def list_files(
    conversationId: str | None = None,
    principal: Principal = Depends(get_principal),
    store: FileStore = Depends(get_file_store),
) -> dict:
    """The caller's files (metadata only) and how much of the quota they take."""
    found = store.list_for(principal.sub)
    if conversationId is not None:
        found = [f for f in found if f.get("conversationId") == conversationId]
    return {"files": found, **store.usage(principal.sub)}


@router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    principal: Principal = Depends(get_principal),
    store: FileStore = Depends(get_file_store),
) -> FileResponse:
    """The stored bytes, always as a download: an uploaded HTML must never render on this origin."""
    held = store.get(principal.sub, file_id)
    if held is None:
        raise HTTPException(status_code=404, detail="file not found")
    meta, blob = held
    return FileResponse(
        blob,
        media_type=meta["contentType"],
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(meta['name'])}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    principal: Principal = Depends(get_principal),
    store: FileStore = Depends(get_file_store),
) -> dict:
    if not store.delete(principal.sub, file_id):
        raise HTTPException(status_code=404, detail="file not found")
    return {"deleted": file_id}
