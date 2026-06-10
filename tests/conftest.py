"""Shared fixtures for all tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from insult.core.contracts.history import ExpressionHistory
from insult.core.llm import LLMResponse
from insult.core.routing import OpusBudget
from insult.core.style import UserStyleProfile

# Pull in the Postgres-backed fixture (`pg_memory_store`) plus its supporting
# pytest-postgresql factories. The module is import-safe even when pg_ctl is
# absent — the `REQUIRES_PG` marker handles skipping per-test in that case.
from tests._pg_fixture import PG_CTL, REQUIRES_PG  # noqa: F401

if PG_CTL is not None:  # pragma: no cover — environment-dependent branch
    from tests._pg_fixture import (  # noqa: F401  (factories registered by-name)
        pg_memory_store,
        postgresql_proc,
        postgresql_socket,
    )

# --- Mock Container ---


@pytest.fixture
def mock_memory():
    """Mocked MemoryStore with async methods."""
    mem = AsyncMock()
    mem.store = AsyncMock()
    mem.get_recent = AsyncMock(return_value=[])
    mem.search = AsyncMock(return_value=[])
    mem.get_stats = AsyncMock(return_value={"total_messages": 0, "unique_users": 0, "unique_channels": 0})
    mem.get_profile = AsyncMock(return_value=UserStyleProfile())
    mem.update_profile = AsyncMock(return_value=UserStyleProfile())
    mem.build_context = MagicMock(return_value=[])
    mem.connect = AsyncMock()
    mem.close = AsyncMock()
    mem.get_channel_summaries = AsyncMock(return_value=[])
    mem.get_channel_activity_since = AsyncMock(return_value=[])
    mem.get_recent_for_summary = AsyncMock(return_value=[])
    mem.upsert_channel_summary = AsyncMock()
    # Reminder methods
    mem.save_reminder = AsyncMock(return_value=1)
    mem.get_pending_reminders = AsyncMock(return_value=[])
    mem.mark_reminder_delivered = AsyncMock()
    mem.update_reminder_time = AsyncMock()
    mem.get_channel_reminders = AsyncMock(return_value=[])
    mem.delete_reminder = AsyncMock(return_value=True)
    mem.get_channel_participants = AsyncMock(return_value=[])
    # Phase 1 (v3.0.0): disclosure, arcs, stances, contradictions
    mem.store_disclosure = AsyncMock()
    mem.get_arc = AsyncMock(return_value=None)
    mem.upsert_arc = AsyncMock()
    mem.store_stance = AsyncMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.store_contradiction = AsyncMock()
    # Guild config (v3.3.0)
    mem.get_guild_config = AsyncMock(return_value=None)
    mem.save_guild_config = AsyncMock()
    # SerenityOps sync (v3.8.0) — default to "user has never synced" so the
    # prompt builder skips the block entirely. Tests that want to exercise
    # the populated branch override this on the fixture.
    mem.get_latest_serenityops_snapshot = AsyncMock(return_value=None)
    mem.insert_serenityops_snapshot = AsyncMock(return_value=1)
    mem.create_sync_token = AsyncMock(return_value=1)
    mem.revoke_sync_tokens = AsyncMock(return_value=0)
    mem.resolve_sync_token = AsyncMock(return_value=None)
    return mem


@pytest.fixture
def mock_agent_client():
    """Mocked AgentRunnerClient — the turn backend (/v1/turn). `.chat`
    returns a default LLMResponse so turn tests that don't override it
    still get text through the pipeline."""
    client = AsyncMock()
    client.chat = AsyncMock(return_value=LLMResponse(text="Test response from Insult"))
    return client


@pytest.fixture
def mock_judge_client():
    """Mocked RunnerJudgeClient — the one-shot utility backend (/v1/judge)
    used by fact extraction, image summary, preset classifier, etc."""
    judge = AsyncMock()
    judge.utility_call = AsyncMock(return_value=LLMResponse(text="judge output"))
    return judge


@pytest.fixture
def mock_settings():
    """Mocked Settings object."""
    s = MagicMock()
    s.system_prompt = "You are Insult."
    s.memory_recent_limit = 50
    s.memory_relevant_limit = 5
    s.command_prefix = "!"
    s.llm_model = "claude-sonnet-4-20250514"
    s.discord_token = "fake-token"  # noqa: S105
    # Router feature flag OFF in tests — legacy single-model path.
    s.model_router_enabled = False
    s.casual_model = "claude-haiku-4-5-20251001"
    s.crisis_model = "claude-opus-4-7"
    s.opus_24h_cap = 20
    # Preset LLM classifier OFF in tests by default — the regex classifier
    # is the legacy behavior the existing test suite expects. Individual
    # tests that need to exercise the LLM middleware path can override
    # this flag on the fixture before instantiating the cog.
    s.preset_classifier_llm_enabled = False
    s.preset_classifier_model = "claude-haiku-4-5-20251001"
    s.preset_classifier_timeout_ms = 1500
    return s


@pytest.fixture
def mock_bot():
    """Mocked discord Bot."""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 999999
    bot.user.name = "Insult"
    bot.latency = 0.05
    bot.guilds = []
    return bot


@pytest.fixture
def mock_siesta():
    """SiestaPoller stub fixed to AWAKE — chat tests assume the bot is awake.

    Tests that need to exercise the siesta-skipped path can override
    ``cog.siesta.is_active`` to return True directly.
    """
    from insult.core.siesta import AWAKE

    siesta = MagicMock()
    siesta.is_active = MagicMock(return_value=False)
    siesta.get = MagicMock(return_value=AWAKE)
    return siesta


@pytest.fixture
def mock_container(mock_settings, mock_memory, mock_agent_client, mock_judge_client, mock_bot, mock_siesta):
    """Full mocked DI container — no `llm` field anymore; the turn rides
    `agent_client` and aux work rides `judge_client`."""
    container = MagicMock()
    container.settings = mock_settings
    container.memory = mock_memory
    container.agent_client = mock_agent_client
    container.judge_client = mock_judge_client
    container.bot = mock_bot
    container.siesta = mock_siesta
    # Real per-bot runtime singletons (mirrors app.Container) so the cog
    # forwards genuine objects into TurnRuntimeDeps, not MagicMock stand-ins.
    container.expression_history = ExpressionHistory()
    container.opus_budget = OpusBudget(cap=20)
    return container


@pytest.fixture
def mock_ctx():
    """Mocked discord.py Context with message.channel async methods."""
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.author.id = 123456
    ctx.author.display_name = "TestUser"
    ctx.channel.id = 789

    # mock_ctx.message simulates a discord.Message
    msg = MagicMock()
    msg.author = ctx.author
    msg.channel = MagicMock()
    msg.channel.id = 789
    msg.channel.send = AsyncMock()
    msg.channel.typing = MagicMock(return_value=AsyncMock())
    msg.channel.typing.return_value.__aenter__ = AsyncMock()
    msg.channel.typing.return_value.__aexit__ = AsyncMock(return_value=False)
    msg.attachments = []
    msg.add_reaction = AsyncMock()
    ctx.message = msg

    # Also set up ctx.typing for backwards compat
    ctx.typing = MagicMock(return_value=AsyncMock())
    ctx.typing.return_value.__aenter__ = AsyncMock()
    ctx.typing.return_value.__aexit__ = AsyncMock(return_value=False)
    return ctx
