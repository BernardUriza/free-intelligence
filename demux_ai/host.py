"""Host launcher — explicit persona selection + boot.

The demux host's one runtime job: pick a persona explicitly (CLI flag or the
``KHIMERAS_PERSONA`` env var, default ``DEFAULT_PERSONA``) and transfer control
to that persona's app entrypoint. It resolves the entrypoint string via importlib
so the host never statically imports a persona (the boundary ratchet stays at
zero) and so the persona's own ``__main__`` import-time setup (structlog-first)
runs exactly as it does under ``python -m personas.<id>``.

This is the spine of the demux thesis: Insult stops being "the system" and
becomes ONE persona the host selects — the same way ALICE is selected.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable

import structlog

from demux_ai.registry import (
    DEFAULT_PERSONA,
    PersonaApp,
    all_persona_apps,
    get_persona_app,
)
from shared.logging_setup import configure_structlog

log = structlog.get_logger()

PERSONA_ENV = "KHIMERAS_PERSONA"


def resolve_persona(explicit: str | None = None) -> PersonaApp:
    """Resolve which persona to boot, explicitly.

    Precedence: ``explicit`` arg > ``KHIMERAS_PERSONA`` env > ``DEFAULT_PERSONA``.
    Raises ``ValueError`` with the known ids on an unregistered selection — the
    host fails fast and loud rather than silently booting the wrong persona.
    """
    persona_id = (explicit or os.getenv(PERSONA_ENV) or DEFAULT_PERSONA).strip().lower()
    app = get_persona_app(persona_id)
    if app is None:
        known = ", ".join(sorted(a.persona_id for a in all_persona_apps()))
        raise ValueError(f"unknown persona '{persona_id}'; known personas: {known}")
    return app


def _load_entrypoint(entrypoint: str) -> Callable[[], object]:
    """Resolve a ``module:callable`` string to the callable, via importlib.

    Importing the module triggers the persona's import-time setup (structlog),
    which is exactly why the host delegates to ``personas.<id>.__main__`` instead
    of reaching for ``.bot`` directly.
    """
    module_name, _, attr = entrypoint.partition(":")
    if not module_name or not attr:
        raise ValueError(f"malformed entrypoint '{entrypoint}'; expected 'module:callable'")
    module = importlib.import_module(module_name)
    fn = getattr(module, attr, None)
    if not callable(fn):
        raise ValueError(f"entrypoint '{entrypoint}' does not resolve to a callable")
    return fn


def launch(explicit: str | None = None) -> None:
    """Select a persona and hand control to its app entrypoint."""
    configure_structlog()
    app = resolve_persona(explicit)
    log.info("demux_host_launch", persona=app.persona_id, entrypoint=app.entrypoint)
    boot = _load_entrypoint(app.entrypoint)
    boot()
