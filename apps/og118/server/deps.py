"""og118's dependency seams: who is calling, who answers, and where the data lives.

Routers pass these to ``Depends``; a consumer or a test swaps one through
``app.dependency_overrides``. Nothing here imports a router.
"""

from __future__ import annotations

import hmac
import logging
import os
from collections.abc import Callable

from fastapi import Header, HTTPException

from fi_runner import Runner
from fi_runner.auth import (
    AuthConfig,
    Auth0Validator,
    Principal,
    legacy_principal,
    make_auth_dependency,
)
from fi_runner.rag_store import RagStoreClient
import push
from conversations import ConversationStore
from elements_registry import Element, get_registry
from projects import ProjectRegistry
from runner import build_runner
from stt import STTProvider
from stt import build_provider as build_stt_provider
from tts import TTSProvider
from tts import build_provider as build_tts_provider

# A child of uvicorn's logger: a bare "og118" logger has no handler and every INFO line
# (which client build is alive, element audits) vanished in production.
logger = logging.getLogger("uvicorn.error").getChild("og118")

# Auth gate. OG118_AUTH_MODE picks the level (default `bearer` = today's behavior,
# nothing changes until explicitly flipped — the lockout-prevention guarantee):
#   bearer → legacy shared OG118_ACCESS_TOKEN speed-bump (synthetic identity)
#   dual   → accept a valid Auth0 JWT OR the legacy bearer (zero-downtime cutover)
#   auth0  → Auth0 JWT only
# The Auth0 validation + dual-accept come from the fi_runner.auth framework
# primitive (the og118-Gate-3 canary). `principal.sub` is the account_id that
# owns projects (PROJ-ACCOUNT-1).
_ACCESS_TOKEN = os.getenv("OG118_ACCESS_TOKEN")
_AUTH_MODE = os.getenv("OG118_AUTH_MODE", "bearer").lower()

# OG118_PROYECTOS — la feature de Proyectos (workspaces con corpus de documentos)
# APAGADA por default. Bernard dejó de usarla el 2026-08-29 y pidió esconderla en
# vez de borrarla, para retomarla después.
#
# El apagado NO es un `if` dentro de cada handler: las 7 rutas viven en su propio
# `projects_router`, que `create_app()` monta SÓLO con el flag prendido. Apagado,
# las rutas no existen y el 404 es real, no simulado — y `corpus_id` deja de
# atarse al turno, así que ningún prompt promete documentos que nadie va a leer.
#
# La rama prendida está CUBIERTA POR TESTS (`test_projects_flag.py`), y eso no es
# decoración: el bug del corpus del 2026-08-29 existió porque había un `else` que
# nadie corría. Una feature apagada sin test de su rama viva es esa misma trampa
# esperando a que alguien la prenda.
def proyectos_activos() -> bool:
    """Lee el flag EN CADA LLAMADA, no al importar.

    Una constante de módulo obligaría a `importlib.reload` para probar la otra
    rama, y una recarga de `app` en una sesión de pytest le derrama estado a las
    suites que corren después — se probó, y contaminó siete tests ajenos. Leer
    el entorno cuesta nanosegundos y `create_app()` ya es la costura por-consumer
    documentada, así que la rama se prueba llamando, no recargando."""
    return os.getenv("OG118_PROYECTOS", "0").strip().lower() in ("1", "true", "yes", "on")


_AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
_AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
_auth0_validator = (
    Auth0Validator(AuthConfig(domain=_AUTH0_DOMAIN, audience=_AUTH0_AUDIENCE))
    if _AUTH0_DOMAIN and _AUTH0_AUDIENCE
    else None
)


def _bearer_dep(authorization: str | None = Header(default=None)) -> Principal:
    """Legacy speed-bump: open when no token is set (local dev), else require the
    shared bearer. Identity is the synthetic legacy principal."""
    if _ACCESS_TOKEN:
        expected = f"Bearer {_ACCESS_TOKEN}"
        if not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="invalid or missing access token")
    return legacy_principal()


def _build_principal_impl() -> Callable[..., Principal]:
    if _AUTH_MODE == "bearer":
        return _bearer_dep
    if _AUTH_MODE == "dual":
        return make_auth_dependency(_auth0_validator, legacy_bearer=_ACCESS_TOKEN)
    if _AUTH_MODE == "auth0":
        return make_auth_dependency(_auth0_validator)
    raise RuntimeError(f"OG118_AUTH_MODE must be bearer|dual|auth0 (got {_AUTH_MODE!r})")


_principal_impl = _build_principal_impl()


def warn_about_auth() -> None:
    """Say at startup when the configured auth mode leaves routes open or unusable."""
    if _AUTH_MODE == "bearer" and not _ACCESS_TOKEN:
        logger.warning(
            "OG118_AUTH_MODE=bearer with OG118_ACCESS_TOKEN unset: routes are OPEN. "
            "Fine for local dev; MUST set the token (or a real mode) in any cloud deploy."
        )
    if _AUTH_MODE in ("dual", "auth0") and _auth0_validator is None:
        logger.error(
            "OG118_AUTH_MODE=%s but AUTH0_DOMAIN/AUTH0_AUDIENCE are unset — every "
            "request would 401. Set them or revert to bearer mode.", _AUTH_MODE
        )

def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """The authenticated caller for a request, per OG118_AUTH_MODE. Overridable
    in tests via app.dependency_overrides (like get_rag_store). `principal.sub`
    is the account_id used for project ownership."""
    return _principal_impl(authorization=authorization)


_runner = build_runner()


def _runner_and_element(element_token: str | None) -> tuple[Runner, Element | None]:
    """Resolve (Runner, Element) for this turn. Unknown/blank/non-active → the base
    og118 runner + None (the turn is byte-identical to no-element)."""
    el = get_registry().resolve(element_token)
    if el is None or not el.is_active:
        return _runner, None
    # Todo elemento activo corre en el motor remoto (la rama externa de
    # chat_stream), así que aquí nunca se construye un runner por elemento: se
    # devuelve el base como placeholder sin uso. El catálogo garantiza el
    # binding — un elemento activo sin él no carga (PERSONA-SSOT-2).
    return _runner, el


RunnerSelector = Callable[[str | None], tuple[Runner, Element | None]]


def get_runner_selector() -> RunnerSelector:
    """Quién contesta este turno — inyectable, como la identidad y los proyectos.

    og118 elige por "elemento": un token del request selecciona la persona. Un
    consumer puede tener OTRO criterio; fenix sirve dos públicos desde el mismo
    servidor (el mostrador cotiza, las PC del cibercafé resuelven tareas) y la
    persona correcta depende de quién llama, no de un token que el cliente
    manda.

    Sin este punto de inyección el consumer sólo tendría dos salidas: quemar un
    slot de la tabla periódica —118 y contados— en la persona de otro producto,
    o reimplementar /chat/stream entero para cambiar una línea.
    """
    return _runner_and_element


def base_runner() -> Runner:
    """The og118 companion runner, read at call time so a test can swap it."""
    return _runner

# Built once from the ambient env. None when OG118_TTS_* / OG118_STT_* is
# unset/incomplete — the voice routes turn that into an explicit 503, never a
# crash.
_tts_provider = build_tts_provider()
_stt_provider = build_stt_provider()


def get_tts_provider() -> TTSProvider | None:
    """Dependency seam: returns the configured provider (or None). Overridable in
    tests via app.dependency_overrides so they never touch the network or need a
    real key."""
    return _tts_provider


def get_stt_provider() -> STTProvider | None:
    """Dependency seam for STT: returns the configured provider (or None).
    Overridable in tests via app.dependency_overrides, exactly like its TTS
    twin, so the contract is exercised without the network or a real key."""
    return _stt_provider


_rag_store: RagStoreClient | None = None


def get_rag_store() -> RagStoreClient:
    """Dependency seam: the project corpus store (ingest/search), built lazily on
    first use and reused — HDF5 loads its on-disk index at construction. Backend +
    path resolve from FI_RAG_BACKEND / FI_RAG_STORE_PATH (hdf5 + hashing zero-model
    by default). Overridable in tests via app.dependency_overrides so they hit a
    tmp store, never prod.

    On the AIRE route the corpus lives in AIRE's Postgres instead, and this ONE
    seam is where that is decided — `AireCorpusClient` matches this interface
    method for method, so the four call sites (upload, list, delete, the
    external-engine fold) stay untouched.

    That it is one seam is the whole point. On 2026-08-24 only HALF the data path
    moved: the model searched AIRE while the upload kept writing to the local file,
    so the corpus was always empty and og118 told a user their working upload had
    failed. Two stores for one surface is what produced that, and choosing the
    store in one place is what stops it recurring — see [[both-ends-of-the-data-path]]."""
    global _rag_store
    if _rag_store is None:
        # Sin rama. La local escribía en un HDF5 del contenedor que, desde la
        # consolidación en AIRE (2026-08-29), NADIE lee: la búsqueda del agente
        # entra por la puerta y aterriza en la Postgres de AIRE. Dejar el `else`
        # habría reconstruido exactamente el bug del 24-ago —la subida en una
        # repisa, la búsqueda en otra— con la diferencia de que esta vez la rama
        # muerta era la que corría por default.
        from fi_runner.aire_corpus import AireCorpusClient

        _rag_store = AireCorpusClient(os.getenv("OG118_AIRE_PROJECT", "og118"))
    return _rag_store


_project_registry: ProjectRegistry | None = None


def get_project_registry() -> ProjectRegistry:
    """Dependency seam: the server-authoritative project↔owner↔corpus map (JSON
    on the Azure Files volume). Path from OG118_PROJECT_REGISTRY_PATH, defaulting
    next to FI_RAG_STORE_PATH. Overridable in tests via app.dependency_overrides
    so they hit a tmp registry, never prod."""
    global _project_registry
    if _project_registry is None:
        default = os.path.join(
            os.path.dirname(os.getenv("FI_RAG_STORE_PATH", "/opt/fi/data/fi_rag_store.h5")),
            "projects.json",
        )
        _project_registry = ProjectRegistry(os.getenv("OG118_PROJECT_REGISTRY_PATH", default))
    return _project_registry


_conversation_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    """Dependency seam: the per-account cloud conversation store (one JSON per
    conversation on the Azure Files volume). Root from OG118_CONVERSATIONS_PATH,
    defaulting next to FI_RAG_STORE_PATH. Overridable in tests."""
    global _conversation_store
    if _conversation_store is None:
        default = os.path.join(
            os.path.dirname(os.getenv("FI_RAG_STORE_PATH", "/opt/fi/data/fi_rag_store.h5")),
            "conversations",
        )
        _conversation_store = ConversationStore(os.getenv("OG118_CONVERSATIONS_PATH", default))
    return _conversation_store


_device_store: push.DeviceStore | None = None


def get_device_store() -> push.DeviceStore:
    """The APNs tokens of each account, next to its conversations. Overridable in tests."""
    global _device_store
    if _device_store is None:
        default = os.path.join(
            os.path.dirname(os.getenv("FI_RAG_STORE_PATH", "/opt/fi/data/fi_rag_store.h5")), "devices"
        )
        _device_store = push.DeviceStore(os.getenv("OG118_DEVICES_PATH", default))
    return _device_store
