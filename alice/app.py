"""DI container for ALICE.

Mirrors the shape of `insult/app.py` so anyone reading both bots
recognizes the pattern: `Container` dataclass holds settings, memory,
llm client, and the Discord bot. Cogs receive the container in their
constructor; tests mock the container.

Container assembly is lazy on lifecycle methods (`connect_memory`,
`build_bot`) so unit tests can construct a Container without I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

import discord
import structlog
from discord.ext import commands

from alice.config import AliceSettings, settings
from alice.core.clinical_reflection import ClinicalReflector
from alice.core.llm import AliceLLMClient
from alice.core.memory import AliceMemory
from alice.core.persona_loader import PersonaLoader, get_persona_loader

log = structlog.get_logger()


@dataclass
class Container:
    """Holds the live dependencies. Created once at process boot."""

    settings: AliceSettings
    memory: AliceMemory
    llm: AliceLLMClient
    persona: PersonaLoader
    bot: commands.Bot
    # Clinical Reflection Layer (backend clínico) — only wired when a
    # clinician-only channel is configured; None disables it.
    clinical: ClinicalReflector | None = None


def create_container() -> Container:
    """Wire dependencies. Pure construction — no network I/O yet."""
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!alice ", intents=intents)

    # The clinical layer is opt-in: only built when a clinician-only channel
    # exists to receive it (so it never has nowhere safe to go).
    clinical = ClinicalReflector() if settings.clinical_channel_id else None

    return Container(
        settings=settings,
        memory=AliceMemory(),
        llm=AliceLLMClient(),
        persona=get_persona_loader(),
        bot=bot,
        clinical=clinical,
    )
