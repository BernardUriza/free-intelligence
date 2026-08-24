"""The corpus door — where a CONSUMER writes and reads its own documents.

Backlog #47. The tool (`engine/corpus_tool.py`) lets the MODEL search a corpus
from inside a turn. That left the other end of the path with no door at all: a
consumer's upload endpoint is server code, and it had nothing to call — so the
corpus the agent searched was always empty, and og118 told a user their working
upload had failed. Half a data path is worse than none.

**The read half is here by Bernard's decision (2026-08-24)**, and it widens
[[write-only-daemon]] on purpose: `GET .../documents` answers a consumer's own
document list and capacity meter, which a human then looks at. The criterion the
rule states — machine's decision versus human's eyes — would have excluded it. His
reasoning, and the rule now records it: the daemon is forbidden from RENDERING a
view, and a consumer reading back its own rows as JSON is not that. The alternative
was og118 keeping a second local store alive purely to draw a panel, which is the
duplicated surface Art. 6 calls the smell.

The `owner` is derived exactly as the tool derives it — from the casita's `@base`,
read off disk — so a document uploaded through this door and a search run inside a
turn land on the same shelf by construction rather than by two matching conventions.
Everything rides the Bearer, like every route but `/health`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import corpus
from .engine.core import WORKSPACES
from .engine.corpus_tool import owner_of
from .intake import safe_names

router = APIRouter()
MAX_DOC_BYTES = int(1e6)


def _scope(project: str, corpus_id: str) -> tuple[str, str]:
    """The shelf and the corpus this request addresses. `corpus_id` goes through
    the same allowlist a project name does: it reaches a SQL parameter, never an
    identifier, but a name nobody validated is one nobody can log either."""
    project, corpus_id = safe_names(project, corpus_id)
    return owner_of(str(WORKSPACES / project)), corpus_id


@router.post("/projects/{project}/corpus/{corpus_id}/documents")
async def put_document(project: str, corpus_id: str, request: Request) -> JSONResponse:
    """Store a document, replacing any earlier version under the same `doc_id`.

    Replace rather than append, for the reason the tool gives: a corrected file
    must not leave the old sentences searchable beside the new ones."""
    owner, corpus_id = _scope(project, corpus_id)
    body: dict[str, Any] = await request.json()
    doc_id = str(body.get("doc_id") or "").strip()
    text = str(body.get("text") or "")
    if not doc_id:
        raise HTTPException(status_code=422, detail="doc_id is required")
    if not text.strip():
        raise HTTPException(status_code=422, detail="an empty document indexes nothing")
    if len(text.encode("utf-8")) > MAX_DOC_BYTES:
        raise HTTPException(status_code=413, detail=f"document over {MAX_DOC_BYTES} bytes")
    chunks = await corpus.ingest(owner, corpus_id, doc_id, text)
    return JSONResponse({"doc_id": doc_id, "chunks": chunks, "replaced": True})


@router.get("/projects/{project}/corpus/{corpus_id}/documents")
async def list_documents(project: str, corpus_id: str) -> JSONResponse:
    """What the corpus holds and how full it is, in one response — see the module
    docstring for why this read lives in the daemon at all."""
    owner, corpus_id = _scope(project, corpus_id)
    return JSONResponse({"documents": await corpus.documents(owner, corpus_id),
                         "capacity": await corpus.stats(owner, corpus_id)})


@router.delete("/projects/{project}/corpus/{corpus_id}/documents/{doc_id}")
async def delete_document(project: str, corpus_id: str, doc_id: str) -> JSONResponse:
    """Remove one document. Reports the rows removed, so a delete that matched
    nothing is distinguishable from one that worked."""
    owner, corpus_id = _scope(project, corpus_id)
    removed = await corpus.drop(owner, corpus_id, doc_id.strip())
    return JSONResponse({"doc_id": doc_id, "chunks_removed": removed})


@router.delete("/projects/{project}/corpus/{corpus_id}")
async def delete_corpus(project: str, corpus_id: str) -> JSONResponse:
    """Remove every document in a corpus."""
    owner, corpus_id = _scope(project, corpus_id)
    return JSONResponse({"corpus_id": corpus_id,
                         "chunks_removed": await corpus.drop(owner, corpus_id)})
