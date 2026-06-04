"""fi-runner CLI — the shell-out surface for the runner framework.

A thin Typer wrapper so ANY process — a shell, a Makefile, a CI step, or a
non-Python backend (the Java/Spring portfolio via ``Runtime.exec``) — can run a
``fi_runner`` Runner WITHOUT importing Python and WITHOUT a persistent sidecar
service. It mirrors how fi-runner itself shells out to ``codex exec --json``::

    fi-runner exec "Summarize this repo" --backend codex --model gpt-4.1
    echo "70yo male, chest pain + dyspnea" | fi-runner exec - --persona-file medic.md
    fi-runner exec "What changed?" --json --session-id pr-42

Doctrine: mirrors `fi-coder` (free-intelligence/backend) — typed options,
example-rich help, stdin ``-`` piping, and exit-code propagation. This is the
**Python half of the conda+npm SSOT**: the TS/npm ``fi-runner`` CLI mirrors
these exact commands and flags over the same contract (see
``docs/SSOT_CONTRACT.md``).

Install the CLI extra + a backend harness, plus the codex binary::

    pip install 'fi-runner[cli,codex]'
    npm i -g @openai/codex
"""

from __future__ import annotations

import asyncio
import json as _json
import sys
from pathlib import Path
from typing import Optional

import typer

from . import ClaudeCodeBackend, CodexBackend, Runner, __version__

app = typer.Typer(
    help="fi-runner — backend-agnostic agent runner, as a shell-out CLI.",
    no_args_is_help=True,
    add_completion=False,
)

#: A neutral default so ``exec`` works with no ``--persona``; Runner rejects an
#: empty persona, so the CLI always supplies one.
_DEFAULT_PERSONA = "You are a precise, helpful agent. Answer the request directly."


def _read_prompt(prompt: str) -> str:
    """Resolve the prompt: ``-`` reads stdin (the fi-coder convention), else the
    literal argument."""
    if prompt == "-":
        return sys.stdin.read()
    return prompt


def _resolve_persona(persona: Optional[str], persona_file: Optional[Path]) -> str:
    if persona_file is not None:
        return persona_file.read_text(encoding="utf-8")
    return persona or _DEFAULT_PERSONA


def _build_backend(
    backend: str,
    model: Optional[str],
    azure_endpoint: Optional[str],
    azure_key_env: str,
):
    """Compose the AgentBackend. The harness SDK is pulled lazily by the backend
    on the first turn, so this stays cheap."""
    if backend == "claude":
        return ClaudeCodeBackend(default_model=model)
    if backend == "codex":
        # API-motor against Azure when an endpoint is given; else a ChatGPT login.
        return CodexBackend(
            default_model=model,
            azure_endpoint=azure_endpoint or None,
            azure_api_key_env=azure_key_env,
        )
    raise ValueError(f"unknown backend {backend!r} (expected 'codex' or 'claude')")


@app.command("exec")
def exec_turn(
    prompt: str = typer.Argument(..., help="Prompt text, or '-' to read from stdin."),
    backend: str = typer.Option("codex", "--backend", "-b", help="Agent harness: codex | claude."),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model / Azure deployment (e.g. gpt-4.1, claude-sonnet-4-5)."
    ),
    persona: Optional[str] = typer.Option(None, "--persona", help="System persona text."),
    persona_file: Optional[Path] = typer.Option(
        None, "--persona-file", help="Read the persona from a file (wins over --persona)."
    ),
    capability: list[str] = typer.Option(
        [], "--capability", "-c", help="fi-core capability wired as an MCP server (repeatable)."
    ),
    azure_endpoint: Optional[str] = typer.Option(
        None,
        "--azure-endpoint",
        envvar="FI_RUNNER_AZURE_ENDPOINT",
        help="Azure OpenAI v1 endpoint for codex API-motor mode (e.g. https://<res>.openai.azure.com/openai/v1).",
    ),
    azure_key_env: str = typer.Option(
        "AZURE_OPENAI_KEY", "--azure-key-env", help="Env var holding the Azure OpenAI API key."
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", "-s", help="Session id for stateful conversation continuity."
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit structured JSON {text, session_id, tool_calls} instead of plain text."
    ),
) -> None:
    """Run a single agent turn and print the result to stdout.

    Examples:
        fi-runner exec "Refactor the auth module" --backend codex --model gpt-4.1
        echo "70yo male, chest pain" | fi-runner exec - --persona-file medic.md
        fi-runner exec "What changed in this PR?" --json --session-id pr-42
    """
    text = _read_prompt(prompt)
    if not text.strip():
        typer.secho("error: empty prompt (nothing on the argument or stdin)", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    try:
        backend_obj = _build_backend(backend, model, azure_endpoint, azure_key_env)
        runner = Runner(
            backend=backend_obj,
            persona=_resolve_persona(persona, persona_file),
            capabilities=list(capability),
        )
        result = asyncio.run(runner.run(text, session_id=session_id))
    except Exception as exc:  # surface as a clean CLI error + nonzero exit
        typer.secho(f"error: {type(exc).__name__}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if as_json:
        payload = {
            "text": result.text,
            "session_id": result.session_id,
            "tool_calls": [getattr(tc, "name", str(tc)) for tc in (result.tool_calls or [])],
        }
        typer.echo(_json.dumps(payload, ensure_ascii=False))
    else:
        typer.echo(result.text)


@app.command("version")
def version() -> None:
    """Print the fi-runner version."""
    typer.echo(__version__)


def main() -> None:
    """console_scripts entrypoint (``fi-runner``)."""
    app()


if __name__ == "__main__":
    main()
