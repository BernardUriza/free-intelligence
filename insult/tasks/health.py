"""Health-check background loop (every 60s).

Logs latency / guild / message counts and, when Azure is configured,
piggybacks the dashboard-data upload onto the same tick.
"""

from __future__ import annotations

import structlog
from discord.ext import tasks

from insult.core.backup import is_azure_configured
from insult.core.metrics import upload_dashboard_data

log = structlog.get_logger()


def build_health_check(bot, memory) -> tasks.Loop:
    """Return the (unstarted) health-check loop bound to ``bot`` + ``memory``."""

    @tasks.loop(seconds=60)
    async def _health_check():
        try:
            stats = await memory.get_stats()
            latency_ms = round(bot.latency * 1000)
            guilds = len(bot.guilds)
            log.info(
                "health_check",
                latency_ms=latency_ms,
                guilds=guilds,
                total_messages=stats["total_messages"],
                unique_users=stats["unique_users"],
            )
            # Upload dashboard data to Azure Blob (piggyback on health check)
            if is_azure_configured():
                all_facts = await memory.get_all_facts()
                await upload_dashboard_data(latency_ms, guilds, stats, all_facts=all_facts)
        except Exception:
            log.exception("health_check_failed")

    return _health_check
