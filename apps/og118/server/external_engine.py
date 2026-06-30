"""og118 external engine proxy (ENGINE-BINDING-ADR-1, external_http_engine).

When an element binds to an external FI engine — the already-running Vultur
runner for Oxígeno — og118 does NOT run a local turn. It proxies the user text to
that engine's `POST /v1/turn` and surfaces the answer. The engine owns its own
persona (selected by `persona_id`) and its own context (keyed by `session_uuid`),
so og118 sends only the message + the conversation key, never a persona or a
replayed history. This is single-shot (the engine returns one LLMResponse, not an
FI event stream), so an external element shows NO glass-box plan/step trace — that
is the documented trade of reusing a live engine instead of copying it.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx

RUNNER_URL = os.getenv("OG118_EXTERNAL_RUNNER_URL", "").rstrip("/")
RUNNER_TOKEN = os.getenv("OG118_EXTERNAL_RUNNER_TOKEN", "")
# 45s read ceiling (down from 120s): an interactive chat turn that takes longer
# is a failure to surface, not to wait on. Behind the ACA ingress a browser abort
# may not reach uvicorn as http.disconnect, so a shorter read timeout bounds how
# long a held POST (+ the engine's compute) survives a client that walked away.
_TIMEOUT = httpx.Timeout(45.0, connect=10.0)


def is_configured() -> bool:
    return bool(RUNNER_URL and RUNNER_TOKEN)


async def stream_external_turn(
    *,
    persona_id: str,
    user_text: str,
    session_uuid: str | None,
    user_id: str | None,
) -> AsyncIterator[dict]:
    """Proxy one turn to the external engine and yield og118 stream events.

    Yields og118-native event dicts (the same shape the local runner emits, so the
    frontend hook maps them unchanged): a single `text` event with the full answer,
    then `done`. On any failure yields a single secret-free `error` event."""
    if not is_configured():
        yield {"type": "error", "message": "external engine not configured (OG118_EXTERNAL_RUNNER_URL/TOKEN unset)"}
        return

    payload: dict = {
        "channel_id": "0",
        "user_id": user_id or "0",
        "user_text": user_text,
        "persona_id": persona_id,
    }
    # The engine threads context on session_uuid; reuse og118's conversation id so
    # the same og118 thread maps to one engine session (continuity without replay).
    if session_uuid:
        payload["session_uuid"] = session_uuid

    headers = {"Authorization": f"Bearer {RUNNER_TOKEN}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{RUNNER_URL}/v1/turn", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        yield {"type": "error", "message": f"external engine unreachable: {type(exc).__name__}"}
        return

    if resp.status_code != 200:
        yield {"type": "error", "message": f"external engine returned {resp.status_code}"}
        return

    try:
        data = resp.json()
    except ValueError:
        yield {"type": "error", "message": "external engine returned a non-JSON body"}
        return

    text = str(data.get("text", "")).strip()
    if not text:
        yield {"type": "error", "message": "external engine returned an empty answer"}
        return
    yield {"type": "text", "text": text}
