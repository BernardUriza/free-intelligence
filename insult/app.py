"""DI container — creates and wires all dependencies."""

from __future__ import annotations

from dataclasses import dataclass

import discord
from discord.ext import commands

from insult.config import Settings, settings
from insult.core.llm import LLMClient
from insult.core.memory import MemoryStore
from insult.core.siesta import SiestaPoller


@dataclass
class Container:
    """Holds all app dependencies. Passed to cogs via constructor injection."""

    settings: Settings
    memory: MemoryStore
    llm: LLMClient
    bot: commands.Bot
    siesta: SiestaPoller


def create_app() -> Container:
    """Factory that wires everything together."""
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=settings.command_prefix, intents=intents)
    memory = MemoryStore(settings.postgres_url.get_secret_value())
    llm = LLMClient(
        api_key=settings.anthropic_api_key.get_secret_value(),
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        cure_model=settings.summary_model,  # Haiku for language cure (step 7c)
    )
    siesta = SiestaPoller()

    return Container(settings=settings, memory=memory, llm=llm, bot=bot, siesta=siesta)
