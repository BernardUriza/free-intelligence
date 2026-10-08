"""CLI: `python -m demux_ai host` starts the omnipresent host receiver.

Recreated post-purga (the old one booted `personas.insult` and died with it). Now
it starts the host over the tested `HostDispatchLoop` + the gpt-4.1 router. Dormant
without ``HOST_DISCORD_TOKEN`` (the cutover atom). Plain-argv verb like
`python -m persona_gateway run` (Art. 6) — Typer collapses a single command.
"""

from __future__ import annotations

import sys

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "host"
    if arg != "host":
        print(f"unknown command: {arg}\nusage: python -m demux_ai host", file=sys.stderr)
        sys.exit(2)
    from shared.logging_setup import configure_structlog

    configure_structlog()

    from demux_ai.host_client import run_host
    from demux_ai.llm_shadow_router import DirectAzureLLMRouter

    run_host(DirectAzureLLMRouter())
