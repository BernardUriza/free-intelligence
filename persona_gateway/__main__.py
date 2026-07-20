"""CLI: `python -m persona_gateway run` starts all configured persona-bots."""

from __future__ import annotations

import sys

if __name__ == "__main__":
    # Accept an optional "run" verb for parity with `python -m insult run`.
    arg = sys.argv[1] if len(sys.argv) > 1 else "run"
    if arg != "run":
        print(f"unknown command: {arg}\nusage: python -m persona_gateway run", file=sys.stderr)
        sys.exit(2)
    from shared.logging_setup import configure_structlog

    configure_structlog()

    from persona_gateway.gateway import run

    run()
