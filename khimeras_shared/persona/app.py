"""Neutral persona-app contract — the inversion that lets the host orchestrate
without knowing a persona's internals (PR-3c).

The demux host (``demux_ai``) must boot a persona without importing its
composition root, its DI container, or any ``personas.<id>.core.*`` module
(enforced at zero by ``tests/arch/test_arch_import_boundaries.py``). The
inversion: each persona exposes a PUBLIC factory conforming to
``PersonaAppFactory``; the host resolves that factory through the registry and
calls it to get a ``PersonaApp`` it can ``run()`` — depending only on this
contract, never on the persona's wiring.

Distinct from ``PersonaRuntimeConfig`` (env-backed infra: DSN, runner URL/token)
in the same package: that is neutral runtime *config*; this is the neutral
runtime *entrypoint* shape.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PersonaApp(Protocol):
    """A fully-assembled, runnable persona application."""

    def run(self) -> None:
        """Boot the persona's Discord bot. Blocks until shutdown."""
        ...


@runtime_checkable
class PersonaAppFactory(Protocol):
    """Builds a persona's runnable app from process env/config.

    The host calls this through the registry entrypoint; it never imports the
    persona's composition root or any persona internals. A persona's factory is
    free to do its own import-time setup (e.g. structlog-first) when it builds.
    """

    def __call__(self) -> PersonaApp: ...
