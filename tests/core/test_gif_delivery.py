"""The GIF ships as its OWN bare message — no version tag, no chunking.

Discord unfurls a GIF cleanly only when the URL stands alone; the `-# ᵛ…`
suffix `send_chunked` appends would hang text off the embed. Same "sidecar, not
a turn" shape as the host's transcript echo.

Mutator rule: positive (the GIF is a separate send carrying the bare URL, and
the marker never reaches the channel) + resistance (a reply that is ONLY a
marker still posts the GIF, and a GIF whose send fails never costs the reply
that already landed).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

URL = "https://tenor.com/view/dance-gif-813685"
CATALOG = f"fiesta: {URL}\n"


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(reply_text: str) -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=MagicMock(id=1))
    channel.typing = MagicMock(return_value=_Typing())
    return channel


async def _run(client: PersonaClient, channel) -> None:
    await client._turns.run_and_deliver(
        channel=channel,
        channel_id="1489180895264116736",
        user_id="907264175246569543",
        guild_id="G1",
        channel_name="general",
        messages=[{"role": "user", "content": "hola"}],
        bot_user_id="1488415576551325906",
    )


async def test_gif_is_a_separate_bare_message_and_the_marker_never_ships():
    client = _client("Eso amerita [GIF: fiesta] carnal.")
    channel = _channel()
    with patch("persona_core.gifs.load_guidance", return_value=CATALOG):
        await _run(client, channel)

    sent = [c.args[0] for c in channel.send.await_args_list]
    assert URL in sent, "el GIF debe salir como su propio mensaje"
    assert not any("[GIF:" in s for s in sent), "el marcador nunca llega al canal"
    gif_msg = next(s for s in sent if s == URL)
    assert "ᵛ" not in gif_msg, "el GIF va sin version tag"


async def test_a_reply_that_is_only_a_gif_still_posts_it():
    """RESISTANCE: stripping the marker empties the text — the old early-return
    would have dropped the whole turn."""
    client = _client("[GIF: fiesta]")
    channel = _channel()
    with patch("persona_core.gifs.load_guidance", return_value=CATALOG):
        await _run(client, channel)
    assert [c.args[0] for c in channel.send.await_args_list] == [URL]


async def test_a_failing_gif_send_never_costs_the_reply():
    client = _client("Toma [GIF: fiesta] y ahí lo dejo.")
    channel = _channel()

    async def _send(piece):
        if piece == URL:
            raise RuntimeError("missing permissions")
        return MagicMock(id=1)

    channel.send = AsyncMock(side_effect=_send)
    with patch("persona_core.gifs.load_guidance", return_value=CATALOG):
        await _run(client, channel)

    sent = " ".join(str(c.args[0]) for c in channel.send.await_args_list)
    assert "ahí lo dejo" in sent
    client.memory.store.assert_awaited()


async def test_unknown_tag_sends_no_gif_but_keeps_the_text():
    client = _client("Toma [GIF: no_existe] pues.")
    channel = _channel()
    with patch("persona_core.gifs.load_guidance", return_value=CATALOG):
        await _run(client, channel)
    sent = [str(c.args[0]) for c in channel.send.await_args_list]
    assert not any(s.startswith("https://") for s in sent)
    assert any("pues" in s for s in sent)
