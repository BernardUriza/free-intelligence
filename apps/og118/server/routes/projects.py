"""Projects: workspaces with a document corpus. Mounted only when OG118_PROYECTOS is on."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from fi_core.rag import NothingToIndex
from fi_runner import MAX_OWNER_INSTRUCTIONS_CHARS
from fi_runner.aire_corpus import AireCorpusError
from fi_runner.auth import Principal
from fi_runner.rag_store import RagStoreClient
from deps import get_principal, get_project_registry, get_rag_store
from projects import ProjectRegistry

router = APIRouter()

# Ceiling on a document upload. Read with a +1 cap so one huge POST cannot OOM the single-replica container.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class ProjectCreateRequest(BaseModel):
    # Only the name is client-supplied. The corpus_id is minted server-side: that is the privacy boundary.
    # pydantic drops any extra field, such as a client-sent project_id.
    name: str | None = None
    description: str | None = None
    instructions: str | None = None


class ProjectUpdateRequest(BaseModel):
    """A partial patch: an OMITTED field is left alone, an empty string CLEARS it.

    That distinction is the whole reason this is a PATCH and the defaults are
    ``None``. A PUT would force the client to resend every field it is not
    editing, and the first client that forgot one would silently wipe it."""

    name: str | None = None
    description: str | None = None
    instructions: str | None = None


@router.post("/projects")
async def create_project(
    req: ProjectCreateRequest,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
) -> dict:
    """Mint a project + its corpus_id SERVER-SIDE, OWNED by the caller's account
    (PROJ-ACCOUNT-1). The client never decides the corpus_id; the owner (account_id
    = principal.sub) is stamped server-side so only the owner can reach it."""
    project = registry.create(
        principal.sub, req.name, description=req.description, instructions=req.instructions
    )
    return {"project_id": project["id"], "name": project["name"], "project": project}


@router.get("/projects")
async def list_projects(
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
) -> dict:
    """The caller's projects (server-authoritative, filtered by owner account)."""
    return {"projects": registry.list_for(principal.sub)}


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
) -> dict:
    """One project the caller owns — what the detail page loads on navigation.
    404 if missing OR not owned (no existence probing)."""
    if not registry.owns(project_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")
    return {"project": registry.get(project_id)}


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
) -> dict:
    """Edit name / description / instructions. Omitted field = untouched."""
    # `instructions` rides in the SYSTEM PROMPT of every turn here, so a pasted document would crowd out the persona and guards.
    # The product refuses and says why; fi-runner's truncation is only the last line of defense.
    if req.instructions is not None and len(req.instructions) > MAX_OWNER_INSTRUCTIONS_CHARS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INSTRUCTIONS_TOO_LONG",
                "message": (
                    f"las instrucciones no pueden pasar de {MAX_OWNER_INSTRUCTIONS_CHARS} "
                    "caracteres; viajan en el prompt de cada turno"
                ),
            },
        )
    project = registry.update(
        project_id,
        principal.sub,
        name=req.name,
        description=req.description,
        instructions=req.instructions,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project": project}


@router.get("/projects/{project_id}/documents")
async def list_project_documents(
    project_id: str,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
    rag: RagStoreClient = Depends(get_rag_store),
) -> dict:
    """The project's corpus: its documents AND how full it is.

    One response for one UI panel. The knowledge rail draws the capacity meter
    directly above the document grid, so splitting this into two routes would buy
    nothing but a second round-trip and a window where the two disagree.

    ``capacity.maxBytes``/``maxDocs`` are ``null`` when no quota is configured
    (``FI_RAG_MAX_BYTES``/``FI_RAG_MAX_DOCS`` unset). Null means UNLIMITED and the
    client must say so — rendering a percentage against an invented ceiling would
    turn an honest "unbounded" into a reassuring number nobody can act on.
    """
    if not principal.is_legacy_bearer and not registry.owns(project_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")
    documents = await rag.list_documents(project_id)
    usage = await rag.stats(project_id)
    quota = rag.quota()
    return {
        "documents": [
            {
                "docId": d["doc_id"],
                "chunks": d["chunk_count"],
                "status": d["status"],
                "attributes": d.get("attributes") or {},
            }
            for d in documents
        ],
        "capacity": {
            "docs": usage["n_docs"],
            "chunks": usage["n_chunks"],
            "bytes": usage["bytes"],
            "maxDocs": quota["max_docs"],
            "maxBytes": quota["max_bytes"],
        },
    }


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
    rag: RagStoreClient = Depends(get_rag_store),
) -> dict:
    """Delete a project the caller owns AND its corpus (no orphaned consultable
    docs). 404 if missing or not owned (no existence probing)."""
    if not registry.owns(project_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")
    # Purge the corpus FIRST, then the registry entry: if the purge fails the project is still there to retry.
    # The reverse order orphaned a corpus nobody could reach to delete.
    await rag.delete_corpus(project_id)
    registry.delete(project_id, principal.sub)
    return {"deleted": project_id}


@router.post("/projects/{project_id}/upload")
async def upload_project_document(
    project_id: str,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
    rag: RagStoreClient = Depends(get_rag_store),
) -> dict:
    """Ingest a text document into the project's corpus (corpus_id=project_id).

    The caller must OWN the project (404 otherwise — no existence probing). Plain
    text in (txt/md): the bytes are decoded as UTF-8, chunked + persisted under the
    file's name. Binary/non-UTF-8 or empty → 400 (PDF/DOCX extraction is the
    caller's job). The agent's rag_store tools then search this corpus when the
    project is the active corpus (see fi_runner.active_corpus_binding)."""
    # Ownership enforced for real accounts; the legacy single shared account
    # (bearer mode) skips it so pre-registry corpora keep working.
    if not principal.is_legacy_bearer and not registry.owns(project_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")
    # Read at most MAX_UPLOAD_BYTES + 1 so a huge upload can't be materialized whole
    # in RAM (OOM the single replica) — if we got more than the cap, reject.
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
            },
        )
    if not raw:
        raise HTTPException(
            status_code=400, detail={"code": "EMPTY_FILE", "message": "uploaded file is empty"}
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"code": "NOT_TEXT", "message": "file is not UTF-8 text; extract text before upload"},
        ) from None
    if not text.strip():
        raise HTTPException(
            status_code=400, detail={"code": "EMPTY_FILE", "message": "uploaded file has no text"}
        )
    doc_id = file.filename or "document.txt"
    # min_chunk_size is below fi-core's default because papelería documents are short. Text under the chunker's floor
    # arrives as `NothingToIndex` (or `AireCorpusError` from AIRE's door), raised BEFORE the previous version is destroyed.
    try:
        chunks = await rag.ingest(project_id, doc_id, text, min_chunk_size=20)
    except (NothingToIndex, AireCorpusError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TOO_SHORT_TO_INDEX",
                "message": "document is too short to index; add more text and re-upload",
                "detail": str(exc),
            },
        ) from exc
    if chunks == 0:  # a store that still reports it this way rather than raising
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TOO_SHORT_TO_INDEX",
                "message": "document is too short to index; add more text and re-upload",
            },
        )
    # Adding knowledge is activity: without this the index sorts a freshly fed project to the bottom.
    registry.touch(project_id, principal.sub)
    return {"corpus_id": project_id, "doc_id": doc_id, "chunks": chunks}
