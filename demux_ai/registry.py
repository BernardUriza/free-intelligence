"""Canonical registry of runnable persona *applications* the host can boot.

This is the HOST's view of personas: which top-level persona apps exist and how
to launch each one. It is deliberately NEUTRAL — every entrypoint is a dotted
``module:callable`` *string* pointing at a persona's public
``khimeras_shared.persona.app.PersonaAppFactory``, never an ``import personas.*``.
The host resolves it lazily via importlib only at launch time (see
``demux_ai.host``), so the host keeps ZERO static dependency on persona
internals, enforced by
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
class PersonaAppSpec:
    """Host-side metadata for a runnable persona app (NOT the app itself — that
    is ``khimeras_shared.persona.app.PersonaApp``, built by the factory)."""

    persona_id: str  # selection key (CLI flag / KHIMERAS_PERSONA env value)
    display_name: str  # human-facing label
    # The persona's public PersonaAppFactory as a dotted "module:callable" string
    # (PR-3c). The host resolves it with importlib at launch, calls it to get a
    # PersonaApp, and runs that — depending only on the khimeras_shared.persona.app
    # contract, never on a persona internal.
    entrypoint: str


# The current de-facto default: `python -m personas.insult run` is the primary
# process today, so selecting nothing boots Insult. Making this explicit is the
# only "behavior change" PR-3 introduces — and it preserves today's default.
DEFAULT_PERSONA = "insult"


PERSONA_APPS: dict[str, PersonaAppSpec] = {
    "insult": PersonaAppSpec(
        persona_id="insult",
        display_name="Insult",
        entrypoint="personas.insult.persona_app:build_app",
    ),
    "alice": PersonaAppSpec(
        persona_id="alice",
        display_name="ALICE",
        entrypoint="personas.alice.persona_app:build_app",
    ),
}


def get_persona_app(persona_id: str) -> PersonaAppSpec | None:
    """Return the PersonaAppSpec for an id, or None if not registered."""
    return PERSONA_APPS.get(persona_id)


def all_persona_apps() -> list[PersonaAppSpec]:
    """All registered runnable persona apps."""
    return list(PERSONA_APPS.values())
