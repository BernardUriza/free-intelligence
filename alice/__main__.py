"""CLI entry point for ALICE: `python -m alice run`.

Configures structlog before any project-internal import so all loggers
share the same processor chain — same pattern as Insult's `__main__.py`.
"""

from __future__ import annotations

import os

import structlog

# Match Insult's log format conventions so KQL queries that scan logs
# can target both bots with the same parsers.
_log_format = os.environ.get("LOG_FORMAT", "console").lower()
_renderer = structlog.processors.JSONRenderer() if _log_format == "json" else structlog.dev.ConsoleRenderer()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        _renderer,
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

import typer  # noqa: E402

from alice.bot import run as bot_run  # noqa: E402

app = typer.Typer(help="ALICE — Artificial Lucid Intelligence for Cognitive Empathy")


@app.command()
def run() -> None:
    """Start the ALICE Discord bot + /invite REST server."""
    bot_run()


if __name__ == "__main__":
    app()
