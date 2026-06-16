"""DI container — creates and wires all dependencies."""

from __future__ import annotations

from dataclasses import dataclass

import discord
import structlog
from discord.ext import commands

from khimeras_shared.runner.agent_client import AgentRunnerClient
from personas.insult.composition import create_memory_store
from personas.insult.config import Settings, settings
from personas.insult.core.contracts.history import ExpressionHistory
from personas.insult.core.contracts.memory import MemoryLifecyclePort
from personas.insult.core.llm.runner_judge_client import RunnerJudgeClient
from personas.insult.core.routing import OpusBudget
from personas.insult.core.siesta import SiestaPoller

log = structlog.get_logger()


@dataclass
class Container:
    """Holds all app dependencies. Passed to cogs via constructor injection.

    Two LLM surfaces, both backed by the agent runner (OAuth Max), no
    direct-Anthropic client anywhere:
      - ``agent_client`` (/v1/turn): the conversational turn engine. Every
        chat turn rides this.
      - ``judge_client`` (/v1/judge): one-shot, text-only utility calls
        (fact extraction, summaries, moltbook drafting/redaction, proactive
        check-ins, reminders). The caller supplies the system prompt, so
        persona-flavored aux work routes here too.
    Both are None only when the runner URL/token aren't configured; aux
    callers degrade gracefully when ``judge_client`` is None.
    """

    settings: Settings
    memory: MemoryLifecyclePort
    bot: commands.Bot
    siesta: SiestaPoller
    # Per-bot shared runtime singletons. They are mutated across turns, so
    # they must outlive any single turn — born here at the composition root
    # rather than mid-cog, alongside the rest of the host-wired runtime.
    expression_history: ExpressionHistory
    opus_budget: OpusBudget
    agent_client: AgentRunnerClient | None = None
    judge_client: RunnerJudgeClient | None = None


def create_app() -> Container:
    """Factory that wires everything together."""
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=settings.command_prefix, intents=intents)
    memory = create_memory_store(settings.postgres_url.get_secret_value())
    siesta = SiestaPoller()
    expression_history = ExpressionHistory()
    opus_budget = OpusBudget(cap=getattr(settings, "opus_24h_cap", 20))

    # The agent runner is the ONLY LLM surface. Both clients hit the same
    # Container App (OAuth Max); they only differ in endpoint:
    #   - agent_client → /v1/turn  (conversational turns)
    #   - judge_client → /v1/judge (one-shot utility: facts, summaries,
    #                               moltbook, proactive, reminders)
    # Built only when both URL and token are configured.
    agent_client: AgentRunnerClient | None = None
    judge_client: RunnerJudgeClient | None = None
    runner_url = settings.insult_agent_runner_url
    runner_token = settings.insult_agent_runner_token.get_secret_value()
    if runner_url and runner_token:
        agent_client = AgentRunnerClient(runner_url=runner_url, runner_token=runner_token)
        judge_client = RunnerJudgeClient(runner_url=runner_url, token=runner_token)
        log.info("agent_runner_client_configured", url=runner_url)
    else:
        log.warning(
            "agent_runner_client_disabled",
            has_url=bool(runner_url),
            has_token=bool(runner_token),
            note="no LLM backend wired — turns and aux LLM work will fail until runner is configured",
        )

    return Container(
        settings=settings,
        memory=memory,
        bot=bot,
        siesta=siesta,
        expression_history=expression_history,
        opus_budget=opus_budget,
        agent_client=agent_client,
        judge_client=judge_client,
    )
