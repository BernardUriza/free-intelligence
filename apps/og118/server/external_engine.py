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


def render_outbound(data: dict) -> str:
    """The part of the engine's turn that IS message content: the text, plus the
    persona's GIFs as markdown images the chat renders inline.

    Since server-bot F5 the engine returns the `OutboundTurn` it assembled, not
    just its text. A GIF (from the persona's own catalog) is content, so it goes
    in the body. A reaction is NOT content — it is a gesture on the message, the
    way Discord shows it under the bubble — so it never gets folded in here: it
    rides the `result` event as `reactions` (see `outbound_reactions`) and
    fi-glass renders it as chips. An engine predating F5 has neither field and
    renders exactly as before.
    """
    text = str(data.get("text", "")).strip()
    gifs = [str(u).strip() for u in (data.get("gif_urls") or []) if str(u).strip().startswith("https://")]
    parts: list[str] = []
    if text:
        parts.append(text)
    parts.extend(f"![gif]({url})" for url in gifs)
    return "\n\n".join(parts)


def outbound_reactions(data: dict) -> list[str]:
    """The emoji the persona reacted with, as the engine reported them."""
    return [str(r).strip() for r in (data.get("reactions") or []) if str(r).strip()]


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
        # Which surface emitted `user_id`: the engine resolves (surface, id) to
        # its canonical principal before it reads memory (server-bot F2).
        "surface": "og118",
    }
    if session_uuid:
        payload["session_uuid"] = session_uuid
    # og118 has no turn pipeline of its own, so the engine runs it (server-bot
    # F3): it stores the turn, runs the guardian and grows the user's facts.
    # Only for a real person in a real conversation — a legacy-bearer caller or
    # a turn with no conversation id would pile every stranger into one memory.
    if user_id and session_uuid:
        payload["pipeline"] = "runner"
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

    text = render_outbound(data)
    reactions = outbound_reactions(data)
    if not text and not reactions:
        # server-bot F5 names why a turn came back empty ("markers_only",
        # "brain_empty"); an engine predating it says nothing.
        reason = str(data.get("empty_reason") or "").strip()
        detail = f" ({reason})" if reason else ""
        yield {"type": "error", "message": f"external engine returned an empty answer{detail}"}
        return
    if text:
        yield {"type": "text", "text": text}
    # The engine reports the model it ran (e.g. claude-sonnet-4-6). Settle the turn
    # with a `result` so that provenance reaches the client the same way the local
    # path delivers it — the answer says what produced it, on both routes. The text
    # is repeated (the reducer replaces, never appends), and usage/session stay out:
    # the frontend has no use for them and they are not the UI's business. The
    # persona's reactions ride here structured: a reaction-only turn is a settled
    # turn with empty text and a gesture, not an error.
    result: dict = {"text": text, "model": data.get("model")}
    if reactions:
        result["reactions"] = reactions
    yield {"type": "result", "result": result}
