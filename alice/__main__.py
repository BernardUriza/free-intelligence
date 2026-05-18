"""CLI entry point for ALICE: `python -m alice run`.

Configures structlog before any project-internal import so all loggers
share the same processor chain — same pattern as Insult's `__main__.py`.
"""

from __future__ import annotations

from shared.logging_setup import configure_structlog


# Metrics processor: every structlog event also lands in the in-process
# ring buffer + counters that `alice/bot.py::_metrics_upload` periodically
# uploads to Azure Blob `alice-bot/metrics.json` for the multi-bot
# dashboard. Same pattern as Insult's __main__.py.
def _metrics_processor(_logger, _method_name, event_dict):
    import contextlib

    with contextlib.suppress(Exception):
        # Never let metrics break logging.
        from alice.core.metrics import record_event

        record_event(event_dict)
    return event_dict


configure_structlog(processors_extra=[_metrics_processor])

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
