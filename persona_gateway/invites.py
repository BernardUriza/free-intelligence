"""Invite turns — helpers for the gateway's ported /invite entry point.

An invite has no summoning user message: the host router (or Insult's REST
call) names a channel and a reason, and the persona reads the thread. These
helpers resolve the channel, phrase the instruction turn, and fetch the
Discord message that triggered the invite so reactions and attachments have a
real target. `respond_to_invite` on the client stays pure orchestration.
"""

from __future__ import annotations

import contextlib

import discord
import structlog

log = structlog.get_logger()


async def resolve_messageable(client: discord.Client, channel_id: str) -> discord.abc.Messageable | None:
    """Channel id → a channel this persona can post in, else None (logged)."""
    channel = client.get_channel(int(channel_id))
    if channel is None:
        with contextlib.suppress(discord.HTTPException):
            channel = await client.fetch_channel(int(channel_id))
    if isinstance(channel, discord.abc.Messageable):
        return channel
    return None


def invite_instruction(invited_by: str, reason: str) -> str:
    """The instruction injected as the FRESHEST turn — context, not a user message."""
    if invited_by == "host_router":
        return (
            f"[El turno es tuyo: la conversación del canal es la que tú traías. Contexto: {reason}] "
            "Lee el hilo de arriba y responde directo al último mensaje, en tu voz."
        )
    return (
        f"[Insult te invitó a este turno. Razón: {reason}] "
        "Lee el hilo de arriba y responde con la mirada que esa razón pide."
    )


async def fetch_trigger(
    channel: discord.abc.Messageable,
    trigger_message_id: str | None,
    *,
    persona_id: str,
    channel_id: str,
) -> discord.Message | None:
    """Fetch the Discord message that triggered this invite, best-effort.

    The summoner's wire carries the trigger id so the persona's `[REACT:]`
    markers land on it (2026-07-14 bug: without a resolved target the reactions
    die) and so its attachments can ride the turn (2026-07-16 bug: a
    host-routed turn about an image was blind without them). An unfetchable
    message degrades to a text-only turn, never a dead invite.
    """
    if not trigger_message_id:
        return None
    try:
        return await channel.fetch_message(int(trigger_message_id))
    except (discord.HTTPException, ValueError):
        log.warning(
            "persona_gateway_invite_trigger_fetch_failed",
            persona_id=persona_id,
            channel_id=channel_id,
            trigger_message_id=trigger_message_id,
        )
        return None
