"""The document door — a project's corpus read back WHOLE, and its history (#55).

The corpus door (#47) writes documents and answers passages; it never gave a
document back as the text that was stored, because the chunk table cannot: it is
an index, and chunking drops the blank lines it splits on. A consumer that keeps
its research here — videopipe's expedientes, which a PreToolUse hook and a
script-writing persona both read as files — needs the exact bytes and the
versions before them. Those live in `corpus_versions`, and this door reads them.

These reads pass [[write-only-daemon]]'s widened test the same way the corpus
list does: the caller owns the rows and gets them back as JSON, nothing rendered.
They are for constant tokens only (`intake.owners_only`), never an invited key.

Doc ids may carry slashes (`casos/niebla/sources-niebla.md`), so the id is the
path's tail; `text/` and `history/` sit before it so neither can be mistaken
for a document name.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import corpus, corpus_versions
from .corpus_door import _scope
from .engine.core import WORKSPACES
from .engine.corpus_tool import owner_of
from .intake import owners_only, safe_names

router = APIRouter()
MAX_DOC_ID = 512


def _doc(doc_id: str) -> str:
    doc_id = doc_id.strip()
    if not doc_id or len(doc_id) > MAX_DOC_ID:
        raise HTTPException(status_code=422, detail=f"doc_id must be 1–{MAX_DOC_ID} characters")
    return doc_id


@router.get("/projects/{project}/corpus")
async def list_corpora(project: str, request: Request) -> JSONResponse:
    """Every corpus on the project's shelf, with its size."""
    owners_only(request)
    project, _ = safe_names(project, "corpora")
    return JSONResponse({"project": project,
                         "corpora": await corpus.corpora(owner_of(str(WORKSPACES / project)))})


@router.get("/projects/{project}/corpus/{corpus_id}/text/{doc_id:path}")
async def read_document(project: str, corpus_id: str, doc_id: str, request: Request,
                        version: int | None = None) -> JSONResponse:
    """The exact text of the newest version, or of `version` when it is named."""
    owners_only(request)
    owner, corpus_id = _scope(project, corpus_id)
    found = await corpus_versions.read(owner, corpus_id, _doc(doc_id), version)
    if found is None:
        raise HTTPException(status_code=404, detail=f"no live document {doc_id!r} in {corpus_id}")
    return JSONResponse(found)


@router.get("/projects/{project}/corpus/{corpus_id}/history/{doc_id:path}")
async def document_history(project: str, corpus_id: str, doc_id: str,
                           request: Request) -> JSONResponse:
    """Every version of one document, newest first — tombstones included."""
    owners_only(request)
    owner, corpus_id = _scope(project, corpus_id)
    versions = await corpus_versions.history(owner, corpus_id, _doc(doc_id))
    return JSONResponse({"doc_id": doc_id, "versions": versions})
