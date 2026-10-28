"""PUT /v1/personas/{persona_id} — create or edit a persona without a deploy.

og118's `POST /elements` is the caller: it claims an empty slot and writes the
persona here with the runner's bearer. The row lands in Postgres and the next turn
for that id loads it (`engine/runtime_personas.py`).
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from persona_runner.api.turn_pipeline import get_memory
from persona_runner.core.auth import check_auth
from persona_runner.engine import runtime_personas

router = APIRouter()


class PersonaWrite(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    provider: str = "claude"
    model: str | None = None
    dna: str
    created_by: str | None = Field(default=None, max_length=200)


class PersonaWritten(BaseModel):
    persona_id: str
    version: int
    provider: str
    model: str | None


@router.put("/v1/personas/{persona_id}", response_model=PersonaWritten)
async def put_persona(persona_id: str, body: PersonaWrite, authorization: str | None = Header(default=None)):
    check_auth(authorization)
    memory = await get_memory()
    if memory is None:
        raise HTTPException(503, "persona store unavailable")
    try:
        version = await runtime_personas.save(
            memory.runtime_personas,
            persona_id=persona_id,
            display_name=body.display_name,
            provider=body.provider,
            model=body.model,
            dna=body.dna,
            created_by=body.created_by,
        )
    except runtime_personas.RuntimePersonaError as e:
        raise HTTPException(422, str(e)) from e
    persona = runtime_personas.lookup(persona_id)
    return PersonaWritten(persona_id=persona_id, version=version, provider=persona.provider, model=persona.model)
