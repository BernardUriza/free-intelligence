"""CLI entry point for ALICE: `python -m alice run`.

Configures structlog before any project-internal import so all loggers
share the same processor chain — same pattern as Insult's `__main__.py`.
"""

from __future__ import annotations

from shared.logging_setup import configure_structlog

# ALICE doesn't have a metrics dashboard (yet); pass no extra processors.
# When she gets one, drop the metrics processor in here — same shape as
# Insult's __main__.py.
configure_structlog(processors_extra=None)

import typer  # noqa: E402

from alice.bot import run as bot_run  # noqa: E402

app = typer.Typer(help="ALICE — Artificial Lucid Intelligence for Cognitive Empathy")


@app.command()
def run() -> None:
    """Start the ALICE Discord bot + /invite REST server."""
    bot_run()


@app.command()
def version() -> None:
    """Print ALICE's version (forces Typer into subcommand mode)."""
    from alice import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
