"""ALICE's public PersonaApp factory — symmetric to Insult's (PR-3c).

The demux host boots ALICE through ``build_app`` (a ``PersonaAppFactory``)
without importing ALICE's internals. The runnable app delegates to ALICE's
existing ``__main__`` entrypoint (structlog-first + bot lifecycle).
"""

from __future__ import annotations

from dataclasses import dataclass

from khimeras_shared.persona.app import PersonaApp


@dataclass(frozen=True)
class AliceApp:
    persona_id: str = "alice"

    def run(self) -> None:
        from personas.alice.__main__ import run as _run

        _run()


def build_app() -> PersonaApp:
    """PersonaAppFactory for ALICE."""
    return AliceApp()
