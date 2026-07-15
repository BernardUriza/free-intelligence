"""CLI entry for the omnipresent host: ``python -m demux_ai host``.

Recreated post-purga (the old one booted `personas.insult` and died with it). Now
it starts the host receiver over the tested `HostDispatchLoop` + the gpt-4.1
router. Dormant without ``HOST_DISCORD_TOKEN`` (the cutover atom).
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Khimeras demux host")


@app.command()
def host() -> None:
    """Start the omnipresent host receiver (needs HOST_DISCORD_TOKEN)."""
    from demux_ai.host_client import run_host
    from demux_ai.llm_shadow_router import DirectAzureLLMRouter

    run_host(DirectAzureLLMRouter())


if __name__ == "__main__":
    app()
