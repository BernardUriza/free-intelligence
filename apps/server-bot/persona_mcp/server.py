"""Stdio MCP server that lets a Claude Code session talk to Bernard's personas AS Bernard.

`scripts/probe_turn.py` speaks as an amnesic `probe-*` principal on purpose; this
server is its opposite: every turn rides `/v1/turn/jobs` with `pipeline="runner"`
under Bernard's canonical principal, so the persona reads his facts and the turn
lands in his memory. Stdlib only, so any `python3` can launch it.

CLI for a session whose MCP config predates this server:
    python3 -I persona_mcp/server.py ask frugivoro "texto"   (or the text on stdin)

Env:
    PERSONA_RUNNER_URL        runner origin (default: the live thankfulmoss FQDN)
    PERSONA_RUNNER_TOKEN_FILE bearer file (default: ~/.secrets/discord-bot-agent-runner-token.txt)
    PERSONA_MCP_PRINCIPAL     user_id sent to the runner (default: Bernard's Discord snowflake)
    PERSONA_MCP_PERSONAS      comma list of personas exposed (default: frugivoro,insult)
    PERSONA_MCP_CHANNEL_PREFIX channel per persona is <prefix>-<persona> (default: claude-code)
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
DEFAULT_URL = "https://persona-runner.thankfulmoss-53b8b5c9.eastus2.azurecontainerapps.io"
DEFAULT_CREDENTIAL_FILE = "~/.secrets/discord-bot-agent-runner-token.txt"
BERNARD_PRINCIPAL = "907264175246569543"
POLL_SECONDS = 5.0
MAX_WAIT_SECONDS = 600.0
SUBMIT_READ_TIMEOUT_S = 200.0
POLL_WAIT_S = 25
POLL_READ_TIMEOUT_S = 60.0


def personas() -> list[str]:
    raw = os.environ.get("PERSONA_MCP_PERSONAS", "frugivoro,insult")
    return [p.strip() for p in raw.split(",") if p.strip()]


def runner_url() -> str:
    url = os.environ.get("PERSONA_RUNNER_URL", DEFAULT_URL).rstrip("/")
    if not url.startswith("https://"):
        raise ValueError(f"PERSONA_RUNNER_URL must be https, got {url!r}")
    return url


def runner_token() -> str:
    path = pathlib.Path(os.environ.get("PERSONA_RUNNER_TOKEN_FILE", DEFAULT_CREDENTIAL_FILE)).expanduser()
    return path.read_text(encoding="utf-8").strip()


def turn_body(persona: str, text: str, thread: str | None, job_id: str | None = None) -> dict[str, Any]:
    prefix = os.environ.get("PERSONA_MCP_CHANNEL_PREFIX", "claude-code")
    channel = f"{prefix}-{persona}" + (f"-{thread}" if thread else "")
    return {
        "persona_id": persona,
        "channel_id": channel,
        "user_id": os.environ.get("PERSONA_MCP_PRINCIPAL", BERNARD_PRINCIPAL),
        "user_name": "Bernard",
        "surface": "claude-code",
        "pipeline": "runner",
        "user_text": text,
        "job_id": job_id or uuid.uuid4().hex,
    }


def _http(
    method: str, path: str, body: dict[str, Any] | None = None, timeout: float = POLL_READ_TIMEOUT_S
) -> dict[str, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(runner_url() + path, data=data, method=method)  # noqa: S310
    req.add_header("Authorization", f"Bearer {runner_token()}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"), strict=False)


def ask(
    persona: str, text: str, thread: str | None = None, http=_http, sleep=time.sleep, clock=time.monotonic
) -> dict[str, Any]:
    if persona not in personas():
        raise ValueError(f"persona {persona!r} is not exposed; this server offers {personas()}")
    body = turn_body(persona, text, thread)
    deadline = clock() + MAX_WAIT_SECONDS
    job_id = _submit(body, deadline, http, sleep, clock)
    while clock() < deadline:
        try:
            status = http("GET", f"/v1/turn/jobs/{job_id}?wait_s={POLL_WAIT_S}", timeout=POLL_READ_TIMEOUT_S)
        except TimeoutError:
            continue
        if status.get("status") == "done":
            return status.get("response") or {}
        sleep(POLL_SECONDS)
    raise TimeoutError(f"job {job_id} still running after {MAX_WAIT_SECONDS:.0f}s")


def _submit(body: dict[str, Any], deadline: float, http, sleep, clock) -> str:
    """The runner scales to zero and the ingress holds the submit through the cold boot.

    The job_id is ours, so a timed-out submit is retried as the SAME turn, never a second one.
    """
    while True:
        try:
            return http("POST", "/v1/turn/jobs", body, timeout=SUBMIT_READ_TIMEOUT_S)["job_id"]
        except TimeoutError:
            if clock() >= deadline:
                raise
            sleep(POLL_SECONDS)


def tools_list() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "ask_persona",
                "description": (
                    "Talk to one of Bernard's personas as Bernard himself. The persona already knows his "
                    f"facts and history: do not re-introduce him. Personas: {', '.join(personas())}."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "persona": {"type": "string", "enum": personas()},
                        "text": {"type": "string", "description": "What Bernard says, in first person."},
                        "thread": {
                            "type": "string",
                            "description": "Optional slug for a separate conversation thread with that persona.",
                        },
                    },
                    "required": ["persona", "text"],
                },
            }
        ]
    }


def tools_call(params: dict[str, Any], asker=ask) -> dict[str, Any]:
    if params.get("name") != "ask_persona":
        return {"content": [{"type": "text", "text": f"unknown tool {params.get('name')!r}"}], "isError": True}
    args = dict(params.get("arguments") or {})
    try:
        resp = asker(str(args.get("persona", "")), str(args.get("text", "")), args.get("thread") or None)
    except (ValueError, TimeoutError, OSError, urllib.error.URLError, KeyError) as exc:
        return {"content": [{"type": "text", "text": f"ask_persona failed: {exc}"}], "isError": True}
    text = resp.get("text") or ""
    if not text.strip():
        reason = resp.get("empty_reason") or "empty reply"
        return {"content": [{"type": "text", "text": f"the persona did not answer: {reason}"}], "isError": True}
    return {"content": [{"type": "text", "text": f"{text}\n\n[model: {resp.get('model', '?')}]"}], "isError": False}


def handle(msg: dict[str, Any]) -> dict[str, Any] | None:
    method, id_ = msg.get("method"), msg.get("id")
    if id_ is None:
        return None
    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "personas", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = tools_list()
    elif method == "tools/call":
        result = tools_call(dict(msg.get("params") or {}))
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": f"method {method!r} not supported"}}
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def cli(argv: list[str]) -> int:
    persona, text = argv[0], " ".join(argv[1:]) or sys.stdin.read()
    out = tools_call({"name": "ask_persona", "arguments": {"persona": persona, "text": text}})
    sys.stdout.write(out["content"][0]["text"] + "\n")
    return 1 if out["isError"] else 0


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "ask":
        raise SystemExit(cli(sys.argv[2:]))
    for line in sys.stdin:
        if not line.strip():
            continue
        reply = handle(json.loads(line))
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
