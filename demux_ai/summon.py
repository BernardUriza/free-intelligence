"""Host-side sibling summon — the persona-gateway `/invite` client.

`summon_persona` fires an HTTP POST to the persona gateway's `/invite`
endpoint in the background. The summoned persona replies asynchronously into
the same channel — the caller doesn't wait, doesn't block, doesn't get the
answer back. All personas see each other's outputs via the shared `messages`
table on subsequent turns.

This is HOST functionality (summoning a persona is routing, not persona
behavior), which is why it lives in `demux_ai` and not inside any persona
package. Moved out of `personas/insult/core/alice_tool.py` (2026-07-14): the
client was never ALICE-specific — it summons ANY gateway persona via
`persona_id` — and the plumbing pipeline is host code that got stranded in the
Insult package during the demux.

Callers, all marker/policy driven (there is no Anthropic tool-use definition —
the agent runner returns no tool_calls):

- the `[INVITE: reason]` marker path (``personas/insult/cogs/chat/invites.py``);
- the LLM router cutover stage (implicit turns routed to a sibling);
- the runner-down failover in ``_stage_call_llm``.

Env contract (names are legacy wire config, renaming them is an Azure ops
change tracked separately): ``GATEWAY_INVITE_URL`` points at the gateway's
`/invite`; ``GATEWAY_INVITE_TOKEN`` is the shared bearer token.
"""

from __future__ import annotations

import os

import httpx
import structlog

log = structlog.get_logger()

# Container Apps' ingress HOLDS a request open while a scaled-to-zero replica
# boots instead of refusing it, so a SLEEPING gateway looks like a hang, never
# like a connection error — the only signal is latency. (Same trap
# `khimeras_shared.stt` documents for susurro, and the reason the runner client
# splits its budget the same way in `khimeras_shared/runner/agent_client.py`.)
#
# A flat 5s budget therefore turned "the gateway is cold" into a DROPPED summon:
# the persona simply never arrived and `summon_http_error` was the only trace.
# min=1 hides it most of the time but does NOT remove it — every deploy, every
# revision swap and every restart hands the host a gateway that is still booting,
# and a boot measured on this environment takes ~20-35s.
#
# Splitting the budget keeps the fast failure where it belongs: a gateway that
# is genuinely unreachable still dies on CONNECT in seconds, while the read
# waits out the boot. Safe because this call is fire-and-forget in the
# background — no user turn blocks on it (see `summon_persona`'s docstring).
#
# This fix does NOT make persona-gateway safe to scale to zero, and nobody
# should read it as a licence to try: the gateway holds each persona's Discord
# websocket, and a DM never produces an `/invite` to wake it (Discord isolates
# DM channels per bot user, so the host cannot see a DM — see
# `persona_gateway/routing.py::should_respond`). Scaled to zero the personas are
# simply offline and every DM dies unheard, which is the 2026-07-27 "en su app
# no contestan" incident reached through a different door. min=1 there is a
# product requirement, not a cost oversight.
SUMMON_CONNECT_TIMEOUT_S = 5.0
SUMMON_READ_TIMEOUT_S = 90.0

# `summon_and_wait` holds the request open for the WHOLE turn: the gateway's
# runner call is budgeted at 240s (`first_turn_timeout_s`), plus chunk pacing.
# Below that, a slow-but-alive turn would be reported "unreachable" and retried
# on top of itself — the double reply this whole seam exists to avoid.
SUMMON_WAIT_READ_TIMEOUT_S = 300.0

# Outcomes a turn can end in, as the host sees them. The first three mean the
# persona took the turn (a 202 says nothing more than "scheduled" — that is the
# whole reason `summon_and_wait` exists); the rest are the host's to act on.
TURN_TAKEN = frozenset({"invited", "delivered", "empty"})


def _build_payload(
    reason: str,
    *,
    channel_id: str,
    guild_id: str | None,
    channel_name: str | None,
    persona_id: str | None,
    invited_by: str | None,
    trigger_message_id: str | None,
    trigger_transcript: str,
) -> dict:
    payload: dict = {
        "channel_id": channel_id,
        "guild_id": guild_id,
        "channel_name": channel_name,
        "reason": reason,
    }
    if persona_id:
        payload["persona_id"] = persona_id
    if invited_by:
        payload["invited_by"] = invited_by
    if trigger_message_id:
        payload["trigger_message_id"] = trigger_message_id
    if trigger_transcript:
        payload["trigger_transcript"] = trigger_transcript
    return payload


async def _post_invite(payload: dict, *, read_timeout_s: float) -> str:
    """POST the invite and name what came back — never raises.

    ``"invited"`` (202), ``"delivered"`` / ``"empty"`` / ``"failed"`` (the
    awaited outcomes the gateway reports on ``wait``), ``"rejected"`` (any
    other status), ``"unreachable"`` (transport error) or ``"error"``.
    """
    url = os.environ.get("GATEWAY_INVITE_URL", "http://localhost:8788/invite")
    token = os.environ.get("GATEWAY_INVITE_TOKEN", "")
    channel_id = payload["channel_id"]
    reason = payload["reason"]

    # Always log entry so we can prove the function executed even when the
    # outcome is silent (e.g. early returns). Token length only, never the
    # value. URL host visible because internal Container App DNS is not
    # secret.
    log.info(
        "summon_called",
        channel_id=channel_id,
        url_host=url.split("/")[2] if "//" in url else "?",
        token_len=len(token),
        wait=bool(payload.get("wait")),
    )
    if not token:
        log.warning("summon_no_token_configured")
        return "rejected"

    try:
        # follow_redirects=True because Azure Container Apps internal ingress
        # 301s http→https. Without this httpx returns the 301 as-is and we
        # treat the redirect as a rejection. Discovered v3.9.13 in prod logs:
        # `summon_rejected status: 301 body: ""`.
        timeout = httpx.Timeout(read_timeout_s, connect=SUMMON_CONNECT_TIMEOUT_S)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 202:
            log.info("summon_accepted", channel_id=channel_id, reason_preview=reason[:80])
            return "invited"
        if resp.status_code in (200, 502) and payload.get("wait"):
            outcome = _awaited_outcome(resp)
            if outcome is not None:
                log.info("summon_outcome", channel_id=channel_id, outcome=outcome, status=resp.status_code)
                return outcome
        log.warning("summon_rejected", status=resp.status_code, body=resp.text[:200])
        return "rejected"
    except httpx.HTTPError as e:
        log.warning("summon_http_error", error=str(e), error_type=type(e).__name__)
        return "unreachable"
    except Exception as e:
        # Catch-all so the caller's tracked-task wrapper sees a clean
        # `background_task_ok` only when we genuinely succeeded.
        log.exception("summon_unexpected_error", error=str(e), error_type=type(e).__name__)
        return "error"


def _awaited_outcome(resp: httpx.Response) -> str | None:
    try:
        outcome = resp.json().get("status")
    except ValueError:
        return None
    return outcome if outcome in ("delivered", "empty", "failed") else None


async def summon_persona(
    tool_input: dict,
    *,
    channel_id: str,
    guild_id: str | None = None,
    channel_name: str | None = None,
    persona_id: str | None = None,
    invited_by: str | None = None,
    trigger_message_id: str | None = None,
    trigger_transcript: str = "",
) -> bool:
    """Fire-and-forget POST to the gateway's /invite endpoint.

    Returns True if the request was accepted (202), False otherwise.
    Errors are logged but don't propagate to the caller — a sibling failing
    to wake up is not a reason to fail the current turn. The user already
    got a response; the sibling arriving late is acceptable, the sibling not
    arriving at all is also acceptable (just suboptimal).
    """
    reason = tool_input.get("reason", "").strip()
    if not reason:
        log.warning("summon_empty_reason")
        return False
    payload = _build_payload(
        reason,
        channel_id=channel_id,
        guild_id=guild_id,
        channel_name=channel_name,
        persona_id=persona_id,
        invited_by=invited_by,
        trigger_message_id=trigger_message_id,
        trigger_transcript=trigger_transcript,
    )
    return await _post_invite(payload, read_timeout_s=SUMMON_READ_TIMEOUT_S) == "invited"


async def summon_and_wait(
    tool_input: dict,
    *,
    channel_id: str,
    guild_id: str | None = None,
    channel_name: str | None = None,
    persona_id: str | None = None,
    invited_by: str | None = None,
    trigger_message_id: str | None = None,
    trigger_transcript: str = "",
) -> str:
    """Summon a persona and stay on the line until its turn ends.

    The host owns reception, so it owns what happens when the persona it chose
    cannot answer — and a 202 at scheduling time told it nothing. This POSTs
    with ``wait: true`` and returns the turn's real outcome (see
    `_post_invite`), which `demux_ai.fallback` turns into a retry or a
    host-voiced notice. Same never-raises contract as `summon_persona`.
    """
    reason = tool_input.get("reason", "").strip()
    if not reason:
        log.warning("summon_empty_reason")
        return "rejected"
    payload = _build_payload(
        reason,
        channel_id=channel_id,
        guild_id=guild_id,
        channel_name=channel_name,
        persona_id=persona_id,
        invited_by=invited_by,
        trigger_message_id=trigger_message_id,
        trigger_transcript=trigger_transcript,
    )
    payload["wait"] = True
    return await _post_invite(payload, read_timeout_s=SUMMON_WAIT_READ_TIMEOUT_S)
