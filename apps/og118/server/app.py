"""og118 server — FastAPI + SSE over fi-runner's run_stream.

This module builds the app: middleware, the routers under ``routes/`` and the
dependency seams a consumer overrides (re-exported from ``deps``).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fi_runner.auth import Principal
from fi_runner.events import SCHEMA_VERSION
import deps
from deps import (
    get_conversation_store,
    get_device_store,
    get_file_store,
    get_principal,
    get_project_registry,
    get_rag_store,
    get_runner_selector,
    get_stt_provider,
    get_tts_provider,
    proyectos_activos,
)
from mcp_background import router as mcp_background_router
from routes import chat, conversations, devices, elements, files, projects, voice

__all__ = [
    "Principal",
    "app",
    "create_app",
    "get_conversation_store",
    "get_device_store",
    "get_file_store",
    "get_principal",
    "get_project_registry",
    "get_rag_store",
    "get_runner_selector",
    "get_stt_provider",
    "get_tts_provider",
]

# Allowed CORS origins, comma-separated. Defaults to the local Next dev server; cloud sets the SWA origin.
_DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("OG118_ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()
]

# Outer wall: per-endpoint caps run AFTER the body is in memory, so a 500 MB PUT was resident before any rejected it.
# Sized for the largest legitimate body: 4 images of 5 MB, base64-inflated (~27 MB), plus the JSON envelope.
MAX_REQUEST_BODY_BYTES = 32 * 1024 * 1024


async def cap_request_body(request: Request, call_next):
    """Reject an oversized body from its Content-Length, before reading it.

    A client that omits Content-Length (chunked) still passes through — the
    per-endpoint caps remain the authoritative check. This is a cheap outer wall
    against the pathological case, not a replacement for them.
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "detail": {
                    "code": "REQUEST_TOO_LARGE",
                    "message": (
                        f"request body exceeds the "
                        f"{MAX_REQUEST_BODY_BYTES // (1024 * 1024)} MB limit"
                    ),
                }
            },
        )
    return await call_next(request)


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    deps.warn_about_auth()
    yield


router = APIRouter()

@router.get("/health")
async def health() -> dict:
    """`schema` is the stream contract this server speaks: a native client that
    cannot be redeployed with it compares before trusting what it parses."""
    return {"ok": True, "schema": SCHEMA_VERSION}


def create_app(dependencies: list | None = None) -> FastAPI:
    """Una instancia NUEVA e independiente del servidor de og118.

    Existe porque `apps/fenix` monta este runtime y necesita endurecer rutas que
    og118 sirve abiertas (`/conversations`, `/projects`): al hacerlo sobre el
    objeto `app` compartido, la mutación viajaba a og118 — verificado, con
    FENIX_ADMIN_TOKEN en el entorno rompía 12 de sus propios tests, porque en
    una sesión de pytest ambos módulos comparten proceso.

    `include_router` construye APIRoute nuevos por instancia, así que las rutas
    de una app no son las de la otra y `dependency_overrides` es por-app. Un
    consumer toma la suya y la modifica sin tocar la de nadie.
    """
    # `dependencies` corren en toda ruta de ESTA instancia: así endurece un consumer las rutas que og118 sirve abiertas.
    # Mutar los APIRoute heredados dejó de servir: desde FastAPI 0.141 dos apps que incluyen el mismo router los comparten.
    application = FastAPI(
        title="og118 server",
        version="0.0.0",
        lifespan=_lifespan,
        dependencies=dependencies or [],
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.middleware("http")(cap_request_body)
    for area in (elements, chat, devices, voice, conversations, files):
        application.include_router(area.router)
    application.include_router(router)
    application.include_router(mcp_background_router)
    if proyectos_activos():
        application.include_router(projects.router)
    return application

# La instancia de og118. `uvicorn app:app` y sus tests siguen apuntando aquí.
app = create_app()
