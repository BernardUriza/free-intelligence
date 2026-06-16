"""CLI entry point for the demux host: ``python -m demux_ai run [--persona ID]``.

The host's runtime job is *explicit* persona selection. It does NOT import any
persona statically (the boundary ratchet locks demux_ai→persona at zero); it
resolves and boots the chosen persona's app entrypoint via ``demux_ai.host``.

Today this is purely additive: ``python -m personas.insult run`` keeps working
unchanged, and running the host with no flag boots Insult (the current default).
"""

from __future__ import annotations

import typer

from demux_ai.host import launch
from demux_ai.registry import DEFAULT_PERSONA, all_persona_apps

app = typer.Typer(help="Khimeras demux host — selects and boots a persona explicitly")


@app.command()
def run(
    persona: str = typer.Option(
        DEFAULT_PERSONA,
        "--persona",
        "-p",
        envvar="KHIMERAS_PERSONA",
        help="Which persona app to boot (e.g. insult, alice).",
    ),
) -> None:
    """Select a persona explicitly and start its Discord bot."""
    launch(persona)


@app.command(name="list-personas")
def list_personas() -> None:
    """List the runnable persona apps the host can boot."""
    for a in all_persona_apps():
        marker = "  (default)" if a.persona_id == DEFAULT_PERSONA else ""
        typer.echo(f"{a.persona_id}\t{a.display_name}\t{a.entrypoint}{marker}")


if __name__ == "__main__":
    app()
