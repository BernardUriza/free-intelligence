"""Insult → ALICE bridge.

Tool spec + handler that lets Insult invite ALICE into a conversation
when the turn needs lucidity / clinical empathy / longitudinal mirroring
that doesn't fit Insult's confrontational register.

The tool is purely additive: it does NOT change Insult's normal response
flow. When the LLM emits an `invoke_alice` call, Insult ALSO writes her
own response (if any) AND fires an HTTP POST to ALICE's `/invite`
endpoint in the background. ALICE replies asynchronously into the same
channel — Insult doesn't wait, doesn't block, doesn't get her answer
back. Both bots see each other's outputs via the shared `messages`
table on subsequent turns.

Design note: this is the inverse of LiteLLM-style multi-LLM routing.
We're NOT picking between Anthropic and OpenAI for the SAME turn. We're
letting two specialized bots co-inhabit the conversation, each
generating their own turn when summoned. The /histerical-search of
2026-05-13 found this is the pattern that production AI tools converged
on (Cursor + Claude Code + Codex composed, not unified).
"""

from __future__ import annotations

import os

import httpx
import structlog

log = structlog.get_logger()

# Tool definition in Anthropic-tool-use schema (compatible with the
# `tools=[...]` arg of `messages.create`). Insult's LLM sees this and
# can emit `{"name": "invoke_alice", "input": {"reason": "...", ...}}`.
INVOKE_ALICE_TOOL: dict = {
    "name": "invoke_alice",
    "description": (
        "Invita a ALICE — un bot hermano especializado en lucidez y empatía clínica — "
        "a este canal cuando la conversación necesita una mirada distinta a la tuya. "
        "Úsalo cuando: (a) hay sufrimiento emocional sostenido que ya no se beneficia "
        "de tu filo, (b) la persona necesita un espejo no-confrontacional para ver "
        "patrones longitudinales, (c) la conversación está tocando temas clínicos "
        "(crisis, terapia, salud mental) donde tu register puede sentirse fuera de lugar, "
        "(d) Bernard o Alex te lo piden explícitamente. NO la uses para delegar trabajo "
        "que tú deberías hacer — ALICE complementa, no reemplaza. Tras invitarla, sigue "
        "respondiendo tú si tienes algo que aportar; ella responderá asíncronamente y "
        "ambas voces convivirán en el hilo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": (
                    "Razón concreta por la que invitas a ALICE. Va dirigida a ELLA, no al "
                    "usuario. Sé específico: 'Bernard está minimizando ansiedad de Alex y "
                    "yo estoy disparando análisis técnico cuando se necesita escucha' es "
                    "útil; 'ayuda' no es útil."
                ),
                "minLength": 20,
                "maxLength": 800,
            },
        },
        "required": ["reason"],
    },
}


async def execute_invoke_alice(
    tool_input: dict,
    *,
    channel_id: str,
    guild_id: str | None = None,
    channel_name: str | None = None,
) -> bool:
    """Fire-and-forget POST to ALICE's /invite endpoint.

    Returns True if the request was accepted (202), False otherwise.
    Errors are logged but don't propagate to the caller — ALICE failing
    to wake up is not a reason to fail Insult's turn. The user already
    got Insult's response; ALICE arriving late is acceptable, ALICE not
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
