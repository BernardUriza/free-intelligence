"""Host launcher — explicit persona selection + boot via the IoC contract.

The demux host's one runtime job: pick a persona explicitly (CLI flag or the
``KHIMERAS_PERSONA`` env var, default ``DEFAULT_PERSONA``) and boot it through
the neutral ``khimeras_shared.persona.app`` contract. It resolves the persona's
public ``PersonaAppFactory`` entrypoint string via importlib, calls it to get a
``PersonaApp``, and runs that — so the host never statically imports a persona
(the boundary ratchet stays at zero) and never knows the persona's composition
root or DI container.

This is the spine of the demux thesis: Insult stops being "the system" and
becomes ONE persona the host selects — the same way ALICE is selected.
"""

from __future__ import annotations

import importlib
import os

import structlog

from demux_ai.registry import (
    DEFAULT_PERSONA,
    PersonaAppSpec,
    all_persona_apps,
    get_persona_app,
)
from khimeras_shared.persona.app import PersonaApp, PersonaAppFactory
from shared.logging_setup import configure_structlog

log = structlog.get_logger()

PERSONA_ENV = "KHIMERAS_PERSONA"


def resolve_persona(explicit: str | None = None) -> PersonaAppSpec:
    """Resolve which persona to boot, explicitly.

    Precedence: ``explicit`` arg > ``KHIMERAS_PERSONA`` env > ``DEFAULT_PERSONA``.
    Raises ``ValueError`` with the known ids on an unregistered selection — the
    host fails fast and loud rather than silently booting the wrong persona.
    """
    persona_id = (explicit or os.getenv(PERSONA_ENV) or DEFAULT_PERSONA).strip().lower()
    spec = get_persona_app(persona_id)
    if spec is None:
        known = ", ".join(sorted(a.persona_id for a in all_persona_apps()))
        raise ValueError(f"unknown persona '{persona_id}'; known personas: {known}")
    return spec


def _load_factory(entrypoint: str) -> PersonaAppFactory:
    """Resolve a ``module:callable`` string to the persona's PersonaAppFactory.

    Importing the factory module is cheap and side-effect-free by contract; the
    persona's heavier import-time setup (structlog-first, DI container) happens
    when the returned app is ``run()``.
    """
    module_name, _, attr = entrypoint.partition(":")
    if not module_name or not attr:
        raise ValueError(f"malformed entrypoint '{entrypoint}'; expected 'module:callable'")
    module = importlib.import_module(module_name)
    factory = getattr(module, attr, None)
    if not callable(factory):
        raise ValueError(f"entrypoint '{entrypoint}' does not resolve to a callable factory")
    return factory


def launch(explicit: str | None = None) -> None:
    """Select a persona and boot it through the PersonaAppFactory contract."""
    configure_structlog()
    spec = resolve_persona(explicit)
    log.info("demux_host_launch", persona=spec.persona_id, entrypoint=spec.entrypoint)
    factory = _load_factory(spec.entrypoint)
    app: PersonaApp = factory()
    app.run()
