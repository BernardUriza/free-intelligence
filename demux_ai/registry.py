"""Canonical registry of runnable persona *applications* the host can boot.

This is the HOST's view of personas: which top-level persona apps exist and how
to launch each one. It is deliberately NEUTRAL — every entrypoint is a dotted
``module:callable`` *string*, never an ``import personas.*``. The host resolves
it lazily via importlib only at launch time (see ``demux_ai.host``), so the host
keeps ZERO static dependency on persona internals, enforced by
``tests/arch/test_arch_import_boundaries.py::test_demux_ai_never_imports_personas``
(locked strict at zero).

Distinct from ``shared/personas/registry.py``: that registry models *sibling*
personas that share ONE brain (the insult-runner) via ``persona_id`` and run
under the gateway. This registry models full runnable persona *applications*
(each its own Discord bot user + process), which is a host/launch concern. The
two never overlap — Insult and ALICE are runnable apps here; Vultur is a sibling
there.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaApp:
    persona_id: str  # selection key (CLI flag / KHIMERAS_PERSONA env value)
    display_name: str  # human-facing label
    # The persona app's entrypoint as a dotted "module:callable" string. The host
    # imports the persona's `__main__` (not `.bot`) so the persona's import-time
    # setup — structlog-first configuration — runs exactly as under
    # `python -m personas.<id>`. Resolved with importlib at launch; never a static
    # import (keeps the host→persona boundary at zero).
    entrypoint: str


# The current de-facto default: `python -m personas.insult run` is the primary
# process today, so selecting nothing boots Insult. Making this explicit is the
# only "behavior change" PR-3 introduces — and it preserves today's default.
DEFAULT_PERSONA = "insult"


PERSONA_APPS: dict[str, PersonaApp] = {
    "insult": PersonaApp(
        persona_id="insult",
        display_name="Insult",
        entrypoint="personas.insult.__main__:run",
    ),
    "alice": PersonaApp(
        persona_id="alice",
        display_name="ALICE",
        entrypoint="personas.alice.__main__:run",
    ),
}


def get_persona_app(persona_id: str) -> PersonaApp | None:
    """Return the PersonaApp for an id, or None if not registered."""
    return PERSONA_APPS.get(persona_id)


def all_persona_apps() -> list[PersonaApp]:
    """All registered runnable persona apps."""
    return list(PERSONA_APPS.values())
