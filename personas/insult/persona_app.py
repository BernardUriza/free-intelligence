"""Insult's public PersonaApp factory — the host's persona-internals-free handle.

PR-3c (IoC contract): the demux host boots Insult through ``build_app`` (a
``PersonaAppFactory``) instead of reaching into Insult's composition root. The
runnable app delegates to Insult's existing ``__main__`` entrypoint, which owns
the structlog-first setup + DI container assembly — so behavior is unchanged and
``composition.py`` stays an internal Insult detail.
"""

from __future__ import annotations

from dataclasses import dataclass

from khimeras_shared.persona.app import PersonaApp


@dataclass(frozen=True)
class InsultApp:
    persona_id: str = "insult"

    def run(self) -> None:
        # Imported lazily so building the app stays cheap and side-effect-free;
        # `__main__` performs Insult's structlog-first configuration at import.
        from personas.insult.__main__ import run as _run

        _run()


def build_app() -> PersonaApp:
    """PersonaAppFactory for Insult."""
    return InsultApp()
