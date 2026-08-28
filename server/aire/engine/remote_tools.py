"""Remote tools (#48) — HTTP MCP servers the CALLER hosts and the door wires.

The registry doctrine holds: no command ever crosses the wire. What a turn may
carry is ``{name, url, headers?}``, and the trust decision is the OPERATOR's —
the url's origin must sit in ``AIRE_REMOTE_TOOL_ORIGINS`` (comma-separated
``https://host[:port]``), or the turn is refused. The headers carry the
caller's own bearer to its own server: a secret in transit, never printed —
no error this module raises may echo a header value.
"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlsplit

from .contract import RemoteTool

NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
MAX_TOOLS = 4
MAX_HEADERS = 8


class BadRemoteTool(Exception):
    """A remote_tools entry the door must refuse — the message is log-safe."""


def _allowed_origins() -> frozenset[str]:
    raw = os.environ.get("AIRE_REMOTE_TOOL_ORIGINS", "")
    return frozenset(o.strip().rstrip("/").lower() for o in raw.split(",") if o.strip())


def _clean_url(url: Any) -> str:
    if not isinstance(url, str) or len(url) > 512:
        raise BadRemoteTool("remote tool url must be a string (<=512 chars)")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise BadRemoteTool("remote tool url must be plain https")
    origin = f"https://{parts.netloc}".lower()
    if origin not in _allowed_origins():
        raise BadRemoteTool(f"origin {origin} is not in AIRE_REMOTE_TOOL_ORIGINS")
    return url


def _clean_headers(raw: Any) -> tuple[tuple[str, str], ...]:
    headers = raw or {}
    ok = (isinstance(headers, dict) and len(headers) <= MAX_HEADERS
          and all(isinstance(k, str) and isinstance(v, str)
                  and len(k) <= 64 and len(v) <= 512
                  and not set("\r\n") & set(k + v) for k, v in headers.items()))
    if not ok:
        raise BadRemoteTool(f"remote tool headers must be a small flat str map "
                            f"(<= {MAX_HEADERS} entries, no newlines)")
    return tuple(sorted(headers.items()))


def clean_remote_tools(raw: Any) -> tuple[RemoteTool, ...]:
    """Validate the door's `remote_tools` field into vetted specs, or refuse."""
    if raw is None or raw == []:
        return ()
    if not isinstance(raw, list) or len(raw) > MAX_TOOLS:
        raise BadRemoteTool(f"remote_tools must be a list of at most {MAX_TOOLS} specs")
    from .tools import REGISTRY
    out: list[RemoteTool] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise BadRemoteTool("each remote tool must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not NAME.match(name):
            raise BadRemoteTool("remote tool name must match ^[a-z][a-z0-9_]{0,31}$")
        if name in REGISTRY or name in seen:
            raise BadRemoteTool(f"remote tool name {name!r} collides with the registry or repeats")
        seen.add(name)
        out.append(RemoteTool(name=name, url=_clean_url(item.get("url")),
                              headers=_clean_headers(item.get("headers"))))
    return tuple(out)


def mount_remote_tools(kwargs: dict[str, Any], remote: tuple[RemoteTool, ...]) -> None:
    """Wire the vetted specs into the SDK options — wired, never executed.

    Each becomes a ``{type: "http"}`` config: the agent's tool calls travel as
    outbound HTTPS to the caller's own server (where its credentials live — the
    droplet keeps holding none). Allowed whole-server, same as the registry."""
    if not remote:
        return
    servers = kwargs.setdefault("mcp_servers", {})
    allowed = list(kwargs["allowed_tools"])
    for rt in remote:
        config: dict[str, Any] = {"type": "http", "url": rt.url}
        if rt.headers:
            config["headers"] = dict(rt.headers)
        servers[rt.name] = config
        allowed.append(f"mcp__{rt.name}")
    kwargs["allowed_tools"] = allowed
