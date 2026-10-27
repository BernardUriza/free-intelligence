"""What a Codex client is born with, and whether this box has a Codex at all.
The operator names the binary in `AIRE_CODEX_COMMAND` (a JSON list or a shell
string): the environment defines what runs, the wire only names it — the ACP
roster's trust split (#48, #49). The credential is the rotor's `codex/*` slot
(#53): `CODEX_HOME` for a plan seat, `CODEX_API_KEY` for the metered fallback,
handed to the process as `env` on top of the daemon's own."""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass, field

from .base import Birth

NAME = "codex"
ENV = "AIRE_CODEX_COMMAND"
DEFAULT_MODEL = "gpt-6-astra"
DEFAULT_EFFORT = "medium"


def command() -> tuple[str, ...]:
    """The operator's binary and any leading flags; empty when the box has no
    Codex, and then `providers()` never lists the name."""
    raw = os.environ.get(ENV, "").strip()
    if not raw:
        return ()
    parts = json.loads(raw) if raw.startswith("[") else shlex.split(raw)
    if not isinstance(parts, list) or not all(isinstance(p, str) and p for p in parts):
        raise ValueError(f"{ENV} must be a command: a JSON list or a shell string")
    return tuple(parts)


def enabled() -> bool:
    return bool(command())


@dataclass(frozen=True)
class CodexOptions:
    command: tuple[str, ...]
    cwd: str
    project_key: str
    session_uuid: str
    allow_tools: bool
    model: str
    effort: str
    env: dict[str, str] = field(default_factory=dict)


def build_options(birth: Birth) -> CodexOptions:
    """`spec.model` picks the weights per turn; the operator's defaults fill
    the rest. `agent` mode is the only one that may write its casita."""
    from .claude import project_key_for_directory
    return CodexOptions(command=command(), cwd=birth.cwd,
                        project_key=project_key_for_directory(birth.cwd),
                        session_uuid=birth.session_uuid,
                        allow_tools=birth.spec.mode == "agent",
                        model=birth.spec.model or os.environ.get("AIRE_CODEX_MODEL", DEFAULT_MODEL),
                        effort=os.environ.get("AIRE_CODEX_EFFORT", DEFAULT_EFFORT),
                        env=dict(birth.credential_env or {}))
