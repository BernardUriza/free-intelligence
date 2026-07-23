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
change tracked separately): ``ALICE_INVITE_URL`` points at the gateway's
`/invite`; ``INSULT_TO_ALICE_TOKEN`` is the shared bearer token.
"""

from __future__ import annotations

import os

import httpx
import structlog

log = structlog.get_logger()


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
    url = os.environ.get("ALICE_INVITE_URL", "http://localhost:8788/invite")
    token = os.environ.get("INSULT_TO_ALICE_TOKEN", "")

    # Always log entry so we can prove the function executed even when the
    # outcome is silent (e.g. early returns). Token length only, never the
    # value. URL host visible because internal Container App DNS is not
    # secret.
    log.info(
        "invoke_alice_called",
        channel_id=channel_id,
        url_host=url.split("/")[2] if "//" in url else "?",
        token_len=len(token),
    )

    if not token:
        log.warning("invoke_alice_no_token_configured")
        return False

    reason = tool_input.get("reason", "").strip()
    if not reason:
        log.warning("invoke_alice_empty_reason")
        return False

    payload = {
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

    try:
        # follow_redirects=True because Azure Container Apps internal ingress
        # 301s http→https. Without this httpx returns the 301 as-is and we
        # treat the redirect as a rejection. Discovered v3.9.13 in prod logs:
        # `invoke_alice_rejected status: 301 body: ""`.
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 202:
            log.info(
                "invoke_alice_accepted",
                channel_id=channel_id,
                reason_preview=reason[:80],
            )
            return True
        log.warning(
            "invoke_alice_rejected",
            status=resp.status_code,
            body=resp.text[:200],
        )
        return False
    except httpx.HTTPError as e:
        log.warning("invoke_alice_http_error", error=str(e), error_type=type(e).__name__)
        return False
    except Exception as e:
        # Catch-all so the caller's tracked-task wrapper sees a clean
        # `background_task_ok` only when we genuinely succeeded.
        log.exception("invoke_alice_unexpected_error", error=str(e), error_type=type(e).__name__)
        return False
