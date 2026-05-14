"""DI container — creates and wires all dependencies."""

from __future__ import annotations

from dataclasses import dataclass

import discord
import structlog
from discord.ext import commands

from insult.config import Settings, settings
from insult.core.llm import LLMClient
from insult.core.llm.agent_client import AgentRunnerClient
from insult.core.memory import MemoryStore
from insult.core.siesta import SiestaPoller

log = structlog.get_logger()


@dataclass
class Container:
    """Holds all app dependencies. Passed to cogs via constructor injection."""

    settings: Settings
    memory: MemoryStore
    llm: LLMClient
    bot: commands.Bot
    siesta: SiestaPoller
    agent_client: AgentRunnerClient | None = None


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

    # Optional Agent SDK runner — only built when both URL and token are
    # configured. Caller (stages.py) further gates by user_id flag.
    agent_client: AgentRunnerClient | None = None
    runner_url = settings.insult_agent_runner_url
    runner_token = settings.insult_agent_runner_token.get_secret_value()
    if runner_url and runner_token:
        agent_client = AgentRunnerClient(runner_url=runner_url, runner_token=runner_token)
        log.info("agent_runner_client_configured", url=runner_url)
    else:
        log.info(
            "agent_runner_client_disabled",
            has_url=bool(runner_url),
            has_token=bool(runner_token),
        )

    return Container(
        settings=settings,
        memory=memory,
        llm=llm,
        bot=bot,
        siesta=siesta,
        agent_client=agent_client,
    )
