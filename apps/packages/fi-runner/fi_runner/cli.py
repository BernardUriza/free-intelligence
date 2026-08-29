"""fi-runner CLI — the shell-out surface for the runner framework.

A thin Typer wrapper so ANY process — a shell, a Makefile, a CI step, or a
non-Python backend (the Java/Spring portfolio via ``Runtime.exec``) — can run a
``fi_runner`` Runner WITHOUT importing Python and WITHOUT a persistent sidecar
service. It mirrors how fi-runner itself shells out to ``codex exec --json``::

    fi-runner exec "Summarize this repo" --model claude-sonnet-4-5
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

from . import AIREBackend, Runner, __version__

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
    project: str,
    model: Optional[str],
    mode: str,
    tools: tuple[str, ...],
):
    """Compose the AgentBackend. One door now: AIRE. The HTTP client is pulled
    lazily on the first turn, so this stays cheap.

    ``--backend claude|codex`` is gone with the local SDK/CLI hosts (see
    :mod:`fi_runner.backends`); what used to be a harness choice is now the
    door's MODE, which is a genuinely different question — ``complete`` grants
    no builtins, ``agent`` grants file+web tools caged to the casita."""
    return AIREBackend(
        project=project,
        default_model=model,
        default_mode=mode,
        registry_tools=tools,
    )


@app.command("exec")
def exec_turn(
    prompt: str = typer.Argument(..., help="Prompt text, or '-' to read from stdin."),
    project: str = typer.Option(
        "fi-runner", "--project", "-p", envvar="FI_RUNNER_AIRE_PROJECT",
        help="AIRE casita this turn runs in ([A-Za-z0-9_-], 128 max).",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model the door pins for the turn (e.g. claude-sonnet-4-5)."
    ),
    mode: str = typer.Option(
        "complete", "--mode",
        help="Door mode: complete (no builtins) | agent (Read/Write/Glob/Grep/WebSearch/WebFetch, caged; never Bash).",
    ),
    persona: Optional[str] = typer.Option(None, "--persona", help="System persona text."),
    persona_file: Optional[Path] = typer.Option(
        None, "--persona-file", help="Read the persona from a file (wins over --persona)."
    ),
    capability: list[str] = typer.Option(
        [], "--capability", "-c",
        help="AIRE registry tool this turn requests by NAME (repeatable). The door 422s any name outside its registry.",
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
        fi-runner exec "Refactor the auth module" --model claude-sonnet-4-5
        echo "70yo male, chest pain" | fi-runner exec - --persona-file medic.md
        fi-runner exec "What changed in this PR?" --json --session-id pr-42
    """
    text = _read_prompt(prompt)
    if not text.strip():
        typer.secho("error: empty prompt (nothing on the argument or stdin)", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    try:
        # `capability` names AIRE registry tools, so it rides the BACKEND, not
        # `Runner.capabilities` — the latter spawns local MCP subprocesses that
        # cannot cross the door.
        runner = Runner(
            backend=_build_backend(project, model, mode, tuple(capability)),
            persona=_resolve_persona(persona, persona_file),
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
