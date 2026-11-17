"""The gate, as a caller on Bernard's machine reaches it — stdlib only, so any `python3` runs it.

Both MCP servers here (`projects_mcp.py`, `persona_mcp.py`) are thin: every tool is
one HTTP call to AIRE's door (`gate.bernarduriza.com`), carrying the door token
read from a file at call time. Nothing is stored here and nothing is decided here;
the daemon owns the data and the rules ([[write-only-daemon]]).

Env:
    AIRE_GATE_URL     the door's origin (default https://gate.bernarduriza.com)
    AIRE_TOKEN_FILE   a file holding the door token, raw or as `AIRE_AUTH_TOKEN=<token>`
                      (default ~/.secrets/aire-llm-token.txt)
"""

from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Iterator

DEFAULT_URL = "https://gate.bernarduriza.com"
DEFAULT_TOKEN_FILE = "~/.secrets/aire-llm-token.txt"
TIMEOUT_S = 60
TURN_TIMEOUT_S = 600


class GateError(Exception):
    """The door answered with an error — its status and detail, never the token."""


def gate_url() -> str:
    url = os.environ.get("AIRE_GATE_URL", DEFAULT_URL).rstrip("/")
    local = url.startswith(("http://127.0.0.1", "http://localhost"))
    if not (url.startswith("https://") or local):
        raise ValueError(f"AIRE_GATE_URL must be https (or a localhost dev box), got {url!r}")
    return url


def token() -> str:
    raw = pathlib.Path(os.environ.get("AIRE_TOKEN_FILE", DEFAULT_TOKEN_FILE)).expanduser().read_text(encoding="utf-8")
    for line in raw.splitlines():
        if line.startswith("AIRE_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return raw.strip()


def quote(*parts: str) -> str:
    """Path segments, each escaped; a doc id keeps its slashes as path separators."""
    return "/".join(urllib.parse.quote(p, safe="/") for p in parts)


def _request(method: str, path: str, body: Any = None, query: dict | None = None) -> urllib.request.Request:
    url = gate_url() + path + (("?" + urllib.parse.urlencode(query)) if query else "")
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)  # noqa: S310
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Content-Type", "application/json")
    return req


def call(method: str, path: str, body: Any = None, query: dict | None = None, raw: bool = False) -> Any:
    """One request to the door: JSON back, or the body as text when `raw` (an artifact).
    A non-2xx becomes a GateError carrying the door's detail."""
    try:
        with urllib.request.urlopen(_request(method, path, body, query), timeout=TIMEOUT_S) as resp:  # noqa: S310
            payload = resp.read().decode("utf-8")
            return payload if raw else json.loads(payload)
    except urllib.error.HTTPError as exc:
        raise GateError(f"{exc.code} {_detail(exc)}") from None


def _detail(exc: urllib.error.HTTPError) -> str:
    try:
        return str(json.loads(exc.read().decode("utf-8")).get("detail", ""))
    except (ValueError, AttributeError):
        return exc.reason or ""


def sse(method: str, path: str, body: Any) -> Iterator[tuple[str, Any]]:
    """The message door's event stream as (event, data) pairs."""
    try:
        resp = urllib.request.urlopen(_request(method, path, body), timeout=TURN_TIMEOUT_S)  # noqa: S310
    except urllib.error.HTTPError as exc:
        raise GateError(f"{exc.code} {_detail(exc)}") from None
    with resp:
        yield from parse_sse(line.decode("utf-8") for line in resp)


def parse_sse(lines: Any) -> Iterator[tuple[str, Any]]:
    event, data = "message", []
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line:
            if data:
                yield event, _json_or_text("\n".join(data))
            event, data = "message", []
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        yield event, _json_or_text("\n".join(data))


def _json_or_text(raw: str) -> Any:
    try:
        return json.loads(raw)
    except ValueError:
        return raw


Http = Callable[..., Any]
Stream = Callable[..., Iterator[tuple[str, Any]]]
