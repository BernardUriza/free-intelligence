"""og118 external engine proxy (ENGINE-BINDING-ADR-1, external_http_engine).

When an element binds to an external FI engine — the already-running Vultur
runner for Oxígeno, the Insult runner for Yodo — og118 does NOT run a local turn.
It proxies the user text to that engine's `POST /v1/turn` and surfaces the
answer. The engine owns its own persona (selected by `persona_id`) and threads
context in a long-lived session keyed by `channel_id` — its `session_uuid` field
is accepted for schema compat but IGNORED (persona_runner v3.9.31+). So og118
sends the og118 conversation id AS `channel_id` (one og118 thread ⇒ one engine
session; a shared constant would pool every user's conversations into ONE Claude
session — cross-account context bleed) and replays the capped client history so
the engine can seed a FRESH session (reaped idle slot, replica restart, element
switched mid-conversation) with the thread it never saw. This is single-shot
(the engine returns one LLMResponse, not an FI event stream), so an external
element shows NO glass-box plan/step trace — that is the documented trade of
reusing a live engine instead of copying it.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx

RUNNER_URL = os.getenv("OG118_EXTERNAL_RUNNER_URL", "").rstrip("/")
RUNNER_TOKEN = os.getenv("OG118_EXTERNAL_RUNNER_TOKEN", "")
# 95s read ceiling — ABOVE the engine's own TURN_TIMEOUT_S (90s) so the engine
# is always the one that cuts, with its typed 502, never this proxy mid-turn.
# The prior 45s (set when every turn shared one always-warm slot) is below the
# measured legitimate worst case now that each conversation opens its own
# engine session: cold-start first turns measured 8.3s / 40.1s / 15.8s live on
# 2026-07-06 (persona load + router + history fold). The ingress-held-POST
# concern that motivated shortening still holds — which is why this tracks the
# engine's ceiling instead of returning to the old open-ended 120s.
_TIMEOUT = httpx.Timeout(95.0, connect=10.0)

# Same caps fi_runner applies to client-replayed history on the local path
# (Runner.client_history_max_messages/_chars). The external path bypasses
# fi_runner, so the cap is enforced here before the payload leaves og118.
HISTORY_MAX_MESSAGES = 20
HISTORY_MAX_CHARS = 16_000
_HISTORY_ROLES = frozenset({"user", "assistant"})


def is_configured() -> bool:
    return bool(RUNNER_URL and RUNNER_TOKEN)


def cap_history(history: list[dict] | None) -> list[dict]:
    """Bound the replayed thread the way fi_runner.sanitize_history does on the
    local path: role-allowlisted, newest-first budget, chronological output."""
    if not history:
        return []
    kept: list[dict] = []
    total = 0
    for msg in reversed(history[-HISTORY_MAX_MESSAGES:]):
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if role not in _HISTORY_ROLES or not content:
            continue
        if total + len(content) > HISTORY_MAX_CHARS:
            break
        kept.append({"role": role, "content": content})
        total += len(content)
    kept.reverse()
    return kept


async def stream_external_turn(
    *,
    persona_id: str,
    user_text: str,
    session_uuid: str | None,
    user_id: str | None,
    history: list[dict] | None = None,
) -> AsyncIterator[dict]:
    """Proxy one turn to the external engine and yield og118 stream events.

    Yields og118-native event dicts (the same shape the local runner emits, so the
    frontend hook maps them unchanged): a single `text` event with the full answer,
    then `done`. On any failure yields a single secret-free `error` event."""
    if not is_configured():
        yield {"type": "error", "message": "external engine not configured (OG118_EXTERNAL_RUNNER_URL/TOKEN unset)"}
        return

    payload: dict = {
        # The engine's continuity key is channel_id (one long-lived SDK session
        # per channel — persona_runner ignores session_uuid). og118's conversation
        # id IS the channel: per-thread continuity, zero cross-user sharing.
        "channel_id": session_uuid or "0",
        "user_id": user_id or "0",
        "user_text": user_text,
        "persona_id": persona_id,
    }
    if session_uuid:
        payload["session_uuid"] = session_uuid
    # Replayed client history (untrusted context, never authorization — same
    # doctrine as the local path). The engine folds it only when it opens a
    # fresh session for this channel; engines predating the field ignore it.
    capped = cap_history(history)
    if capped:
        payload["history"] = capped

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
