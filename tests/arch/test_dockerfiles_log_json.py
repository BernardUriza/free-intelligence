"""Observability invariant — every shipped image logs JSON, never ANSI console.

Prod P0 (2026-07-08): NO Container App set ``LOG_FORMAT``, so
``shared.logging_setup.configure_structlog`` fell back to ``ConsoleRenderer``
and every prod log line carried ANSI escapes INSIDE its key=value pairs::

    \\e[36moutcome\\e[0m=\\e[35mfailed\\e[0m

The escapes are invisible in any viewer that strips them (``scripts/kql.sh``
does), so the logs LOOK clean while every KQL predicate over a field matches
zero rows. Consequences, all silent:

  * ``insult-turn-failure-rate`` (sev 2) could never fire — its predicates
    ``Log_s has 'chat_turn_end'`` and ``has 'outcome=failed'`` both returned 0.
  * ``invite-accepted-without-completion`` computed ``accepted`` = 0 forever.
  * ``docs/kql_queries.md`` documents ``parse_json(Log_s)``, which returned
    nothing at all, because prod never emitted JSON.

A container logs to a machine, not to a terminal. Pinning ``LOG_FORMAT=json`` in
the image (rather than in an Azure env var somebody must remember) makes the
guarantee travel with the artifact. This test is the ratchet.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SHIPPED_DOCKERFILES = [
    "Dockerfile.gateway",
    "infra/azure/runner.Dockerfile",
]

_ENV_LOG_FORMAT = re.compile(r"^\s*ENV\s+LOG_FORMAT\s*=\s*(\S+)", re.MULTILINE)


@pytest.mark.parametrize("dockerfile", SHIPPED_DOCKERFILES)
def test_image_pins_json_logging(dockerfile: str) -> None:
    path = REPO_ROOT / dockerfile
    assert path.exists(), f"{dockerfile} missing — update SHIPPED_DOCKERFILES"

    matches = _ENV_LOG_FORMAT.findall(path.read_text())
    assert matches, (
        f"{dockerfile} does not pin `ENV LOG_FORMAT=json`. Without it structlog "
        "renders ANSI-coloured console output and every KQL field predicate "
        "(including the Azure alert rules) silently matches zero rows."
    )
    assert matches[-1] == "json", f"{dockerfile} sets LOG_FORMAT={matches[-1]!r}, expected 'json'"


def test_console_renderer_is_the_default_only_outside_containers() -> None:
    """Resistance case: the fallback must STAY console for local dev.

    Pinning JSON in the image is the fix; changing the library default would make
    interactive `python -m personas.insult run` unreadable.
    """
    source = (REPO_ROOT / "shared" / "logging_setup" / "structlog_config.py").read_text()
    assert 'os.environ.get("LOG_FORMAT", "console")' in source, (
        "The local-dev default must remain 'console'. If this moved, update the docstring and this test together."
    )
