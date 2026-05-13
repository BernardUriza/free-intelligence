"""structlog configuration shared between Insult and ALICE.

Both bots configure structlog in their `__main__.py` BEFORE any project
import so the logger factories are bound to the shared processor chain.
The base processors are identical (contextvars merge, level annotation,
stack info, exc info, ISO timestamp, JSON or console renderer based on
`LOG_FORMAT`). What differs is the auxiliary processors each bot wants
to inject — Insult appends a metrics processor that feeds events to the
dashboard collector; ALICE doesn't have a dashboard yet and injects
nothing. We expose that as an explicit `processors_extra` parameter
instead of forcing a base class hierarchy.
"""

from shared.logging_setup.structlog_config import configure_structlog

__all__ = ["configure_structlog"]
