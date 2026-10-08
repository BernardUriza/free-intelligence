"""The narrow slice of the live persona-bot that workers depend on.

Workers need exactly two things off the running `PersonaClient`: `get_channel`
(to resolve a stored channel id) and its `user` (for the stored author id). Typing
that dependency as a structural `Protocol` — not the concrete `PersonaClient` —
keeps the graph acyclic (workers never import the client) and lets a test pass a
trivial fake host. `discord.Client` satisfies it structurally, so the real client
is passed as-is.
"""

from __future__ import annotations

from typing import Protocol

import discord


class GatewayHost(Protocol):
    """What a worker uses off the live persona-bot."""

    user: discord.ClientUser | None

    def get_channel(self, channel_id: int, /) -> discord.abc.GuildChannel | discord.abc.PrivateChannel | None: ...


def host_bot_id(host: GatewayHost) -> str:
    """The bot's own user id as a string for storage, or "0" before login."""
    return str(host.user.id) if host.user else "0"
