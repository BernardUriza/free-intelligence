"""The "elementos": the catalog the selector offers and the UI-created ones an author edits."""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from fi_runner.auth import Principal
from deps import get_principal, logger
from elements_registry import (
    Element,
    ElementsRegistryError,
    claim_for,
    claim_slot,
    get_registry,
    release_slot,
    replace_claim,
)
from external_engine import (
    PersonaWriteError,
    delete_persona,
    get_persona,
    put_persona,
    stream_external_turn,
)

router = APIRouter()


@router.get("/elements")
async def list_elements() -> dict:
    """The active "elementos" the UI selector offers (OG118-ELEMENTS-ADR-1).

    Active-only by design: the 117 empty/reserved slots are catalog, not product —
    surfacing them would read as an unfinished roster. Public on purpose: this is
    names/symbols, never the persona prompts, so it carries nothing the bearer gate
    protects and it must render before the user pastes a token."""
    reg = get_registry()
    return {
        "elements": [
            {
                "id": e.id,
                "atomicNumber": e.atomic_number,
                "symbol": e.symbol,
                "slug": e.slug,
                "displayName": e.display_name,
                "displayLabel": e.display_label,
                "status": e.status,
                "aliases": list(e.aliases),
                "description": e.description,
                "engine": e.engine_label,
            }
            for e in reg.elements
            if e.is_active
        ]
    }


_PERSONA_ID_RE = r"^[a-z0-9_]{1,32}$"


def _element_author(principal: Principal) -> bool:
    """Who may claim a slot: accounts named in OG118_ELEMENT_AUTHORS by the same
    hash the conversation store files them under. Unset = nobody (fail closed)."""
    allowed = {a.strip() for a in os.getenv("OG118_ELEMENT_AUTHORS", "").split(",") if a.strip()}
    if principal.is_legacy_bearer or not allowed:
        return False
    return hashlib.sha256(principal.sub.encode("utf-8")).hexdigest()[:32] in allowed


class ElementCreateRequest(BaseModel):
    atomicNumber: int = Field(ge=1, le=118)
    displayName: str = Field(min_length=1, max_length=80)
    personaId: str = Field(pattern=_PERSONA_ID_RE)
    description: str | None = Field(default=None, max_length=500)
    aliases: list[str] = Field(default_factory=list, max_length=8)
    provider: str = "claude"
    model: str | None = Field(default=None, max_length=80)
    dna: str = Field(min_length=1, max_length=200_000)


@router.get("/elements/slots")
async def list_empty_slots(principal: Principal = Depends(get_principal)) -> dict:
    """The empty slots a new element can take, whether this caller may take one, and
    the slugs it may edit (the ones born from the UI)."""
    author = _element_author(principal)
    elements = get_registry().elements
    return {
        "canCreate": author,
        "slots": [
            {"atomicNumber": e.atomic_number, "symbol": e.symbol, "slug": e.slug, "displayName": e.display_name}
            for e in elements
            if e.status == "empty"
        ],
        "editable": [e.slug for e in elements if author and e.is_active and claim_for(e.atomic_number)],
    }


@router.post("/elements", status_code=201)
async def create_element(req: ElementCreateRequest, principal: Principal = Depends(get_principal)) -> dict:
    """Claim an empty slot and give it a persona, with no deploy (OG118-ELEMENTOS-ALTA).

    Both ends in one call: the persona goes to the engine that answers the turns
    (server-bot's runner, durable in its Postgres) and the slot goes to og118's
    catalog overlay. The engine is written first: a slot that points at a persona
    the engine does not hold would answer as the default persona."""
    if not _element_author(principal):
        raise HTTPException(status_code=403, detail="no puedes crear elementos")
    claim = {
        "atomicNumber": req.atomicNumber,
        "displayName": req.displayName.strip(),
        "personaId": req.personaId,
        "description": (req.description or "").strip() or None,
        "aliases": [a.strip().lower() for a in req.aliases if a.strip()],
    }
    try:
        get_registry().with_claim(claim)
    except ElementsRegistryError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    try:
        written = await put_persona(
            req.personaId,
            {
                "display_name": claim["displayName"],
                "provider": req.provider,
                "model": req.model,
                "dna": req.dna,
                "created_by": hashlib.sha256(principal.sub.encode("utf-8")).hexdigest()[:32],
            },
        )
    except PersonaWriteError as e:
        status = 422 if e.status == 422 else 502
        raise HTTPException(status_code=status, detail=f"el motor no guardó la persona: {e}") from e
    try:
        element = claim_slot(claim)
    except ElementsRegistryError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    logger.info("element_created z=%s persona=%s version=%s", element.atomic_number, req.personaId, written.get("version"))
    return {
        "id": element.id,
        "atomicNumber": element.atomic_number,
        "symbol": element.symbol,
        "displayLabel": element.display_label,
        "personaId": req.personaId,
        "personaVersion": written.get("version"),
        "provider": written.get("provider"),
        "model": written.get("model"),
    }


class ElementUpdateRequest(BaseModel):
    displayName: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    aliases: list[str] = Field(default_factory=list, max_length=8)
    provider: str = "claude"
    model: str | None = Field(default=None, max_length=80)
    dna: str = Field(min_length=1, max_length=200_000)


class ElementTestRequest(BaseModel):
    input: str = Field(min_length=1, max_length=4000)


def _claimed_element(slug: str, principal: Principal) -> tuple[Element, dict]:
    """An element born from the UI, for its author. Image elements are not editable here."""
    if not _element_author(principal):
        raise HTTPException(status_code=403, detail="no puedes editar elementos")
    element = get_registry().resolve(slug)
    claim = claim_for(element.atomic_number) if element is not None else None
    if element is None or claim is None:
        raise HTTPException(status_code=404, detail="ese elemento no se creó desde la app")
    return element, claim


def _engine_error(e: PersonaWriteError) -> HTTPException:
    return HTTPException(status_code=e.status if e.status in (404, 422) else 502, detail=f"el motor: {e}")


@router.get("/elements/{slug}/persona")
async def read_element(slug: str, principal: Principal = Depends(get_principal)) -> dict:
    element, claim = _claimed_element(slug, principal)
    try:
        persona = await get_persona(claim["personaId"])
    except PersonaWriteError as e:
        raise _engine_error(e) from e
    return {
        "atomicNumber": element.atomic_number,
        "symbol": element.symbol,
        "slug": element.slug,
        "displayName": element.display_name,
        "description": element.description,
        "aliases": list(element.aliases),
        "personaId": claim["personaId"],
        "provider": persona.get("provider"),
        "model": persona.get("model"),
        "dna": persona.get("dna"),
        "version": persona.get("version"),
    }


@router.put("/elements/{slug}")
async def update_element(
    slug: str, req: ElementUpdateRequest, principal: Principal = Depends(get_principal)
) -> dict:
    """A new persona version on the engine, then the slot's name, text and aliases."""
    element, claim = _claimed_element(slug, principal)
    edited = {
        **claim,
        "displayName": req.displayName.strip(),
        "description": (req.description or "").strip() or None,
        "aliases": [a.strip().lower() for a in req.aliases if a.strip()],
    }
    try:
        written = await put_persona(
            claim["personaId"],
            {
                "display_name": edited["displayName"],
                "provider": req.provider,
                "model": req.model,
                "dna": req.dna,
                "created_by": hashlib.sha256(principal.sub.encode("utf-8")).hexdigest()[:32],
            },
        )
    except PersonaWriteError as e:
        raise _engine_error(e) from e
    try:
        replace_claim(edited)
    except ElementsRegistryError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    logger.info("element_updated z=%s persona=%s version=%s", element.atomic_number, claim["personaId"], written.get("version"))
    return {"slug": element.slug, "personaVersion": written.get("version")}


@router.delete("/elements/{slug}", status_code=204)
async def delete_element(slug: str, principal: Principal = Depends(get_principal)) -> Response:
    """Empty the slot first, so it never points at a persona the engine dropped."""
    element, claim = _claimed_element(slug, principal)
    try:
        release_slot(element.atomic_number)
    except ElementsRegistryError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    try:
        await delete_persona(claim["personaId"])
    except PersonaWriteError as e:
        logger.warning("element_persona_orphaned persona=%s status=%s", claim["personaId"], e.status)
    logger.info("element_deleted z=%s persona=%s", element.atomic_number, claim["personaId"])
    return Response(status_code=204)


@router.post("/elements/{slug}/test")
async def test_element(slug: str, req: ElementTestRequest, principal: Principal = Depends(get_principal)) -> dict:
    """One turn as a probe: tagged in the engine's memory, never mined for facts."""
    element, claim = _claimed_element(slug, principal)
    started = time.monotonic()
    output, error = "", None
    async for event in stream_external_turn(
        persona_id=claim["personaId"],
        user_text=req.input,
        session_uuid=f"probe-{datetime.now(UTC):%Y%m%d}-{element.slug}-{uuid.uuid4().hex[:8]}",
        user_id="probe-element-editor",
    ):
        if event.get("type") == "result":
            output = (event.get("result") or {}).get("text") or output
        elif event.get("type") == "text":
            output += event.get("text") or ""
        elif event.get("type") == "error":
            error = event.get("message")
    if error and not output:
        raise HTTPException(status_code=502, detail=error)
    return {"output": output, "latency_ms": int((time.monotonic() - started) * 1000)}
