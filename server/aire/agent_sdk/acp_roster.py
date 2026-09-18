"""Which ACP agents this box may spawn, by NAME. The wire names a provider; the
ENVIRONMENT defines what that name runs — the same trust split as remote tools
(#48): no command ever crosses the wire.

`AIRE_ACP_AGENTS` is a JSON object, `{"claude-acp": {"command": ["claude-code-acp"],
"env": {}}, "qwen": ["qwen", "--acp"]}` — a bare list is a command with no env.
Read on every call: it is one env var, and a test sets it per case."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

ENV = "AIRE_ACP_AGENTS"
RESERVED = ("claude",)  # the native backend's name can never be an ACP agent


class BadRoster(Exception):
    """AIRE_ACP_AGENTS is malformed — an operator's mistake, never a caller's."""


@dataclass(frozen=True)
class AcpAgent:
    name: str
    command: tuple[str, ...]
    env: dict[str, str] = field(default_factory=dict)


def roster() -> dict[str, AcpAgent]:
    raw = os.environ.get(ENV, "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise BadRoster(f"{ENV} is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BadRoster(f"{ENV} must be a JSON object of name -> agent")
    return {name: _agent(name, cfg) for name, cfg in data.items()}


def _agent(name: str, cfg: object) -> AcpAgent:
    if name in RESERVED or not name or not name.replace("-", "").replace("_", "").isalnum():
        raise BadRoster(f"{ENV}: {name!r} is not a valid agent name")
    command = cfg.get("command") if isinstance(cfg, dict) else cfg
    env = cfg.get("env", {}) if isinstance(cfg, dict) else {}
    if (not isinstance(command, list) or not command
            or not all(isinstance(c, str) and c for c in command)):
        raise BadRoster(f"{ENV}: {name!r} needs a non-empty command list")
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                            for k, v in env.items()):
        raise BadRoster(f"{ENV}: {name!r} env must map strings to strings")
    return AcpAgent(name=name, command=tuple(command), env=dict(env))
