"""CLI entry point: python -m insult run

IMPORTANT: structlog must be configured BEFORE any insult module is imported,
because modules do `log = structlog.get_logger()` at import time.
"""

import asyncio
import os

import structlog


def _metrics_processor(logger, method_name, event_dict):
    """Structlog processor that feeds events to the dashboard metrics collector."""
    from insult.core.metrics import record_event

    record_event(event_dict)
    return event_dict


# Pick renderer based on LOG_FORMAT env var (json for KQL, console for local dev)
_log_format = os.environ.get("LOG_FORMAT", "console").lower()
_renderer = structlog.processors.JSONRenderer() if _log_format == "json" else structlog.dev.ConsoleRenderer()

# Configure structlog FIRST — before any insult.* import
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        _metrics_processor,
        _renderer,
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,  # Don't cache — ensures all loggers use this config
)

# NOW import everything else
import typer  # noqa: E402

log = structlog.get_logger()
app = typer.Typer(help="Insult — Discord bot con memoria longitudinal + Claude API")


@app.command()
def run():
    """Start the Discord bot."""
    from insult.bot import run as bot_run

    bot_run()


@app.command()
def db_stats():
    """Show memory database statistics."""
    from insult.config import settings
    from insult.core.memory import MemoryStore

    async def _stats():
        store = MemoryStore(settings.db_path)
        await store.connect()
        stats = await store.get_stats()
        await store.close()
        return stats

    stats = asyncio.run(_stats())
    typer.echo(f"Total messages: {stats['total_messages']}")
    typer.echo(f"Unique users:   {stats['unique_users']}")
    typer.echo(f"Channels:       {stats['unique_channels']}")


@app.command()
def db_clean(
    before_days: int = typer.Option(90, help="Delete messages older than N days"),
    dry_run: bool = typer.Option(True, help="Preview without deleting"),
):
    """Clean old messages from memory database."""
    import time

    from insult.config import settings
    from insult.core.memory import MemoryStore

    cutoff = time.time() - (before_days * 86400)

    async def _clean():
        store = MemoryStore(settings.db_path)
        await store.connect()

        if dry_run:
            await store._ensure_connection()
            cursor = await store._db.execute("SELECT COUNT(*) FROM messages WHERE timestamp < ?", (cutoff,))
            row = await cursor.fetchone()
            typer.echo(f"[DRY RUN] Would delete {row[0]} messages older than {before_days} days")
        else:
            count = await store.delete_before(cutoff)
            typer.echo(f"Deleted {count} messages older than {before_days} days")

        await store.close()

    asyncio.run(_clean())


@app.command()
def consolidate_facts(
    user_id: str = typer.Option("", help="Limit to one user_id; empty = all users with facts"),
    dry_run: bool = typer.Option(False, help="Compute the plan without applying it"),
):
    """Run the Mem0-style consolidator over user_facts (Phase 1, v3.6.0).

    Scheduled to run every 2 days via Azure Container App job. Manual
    invocation is fine for ad-hoc curation, dry-runs against prod, or
    testing the LLM judge prompt without touching the DB.

    When AZURE_STORAGE_CONNECTION_STRING is set (i.e. running in the
    Azure Container App Job environment with an ephemeral disk), this
    command downloads the live DB from blob storage before consolidating
    and uploads the modified copy back at the end. The race-detection
    in upload_db (skip_if_remote_newer=True) means a bot-write that
    happened during consolidation will preserve the bot's version and
    log a warning instead of clobbering the new messages.
    """
    import anthropic

    from insult.config import settings
    from insult.core.backup import download_db, is_azure_configured, upload_db
    from insult.core.memory import MemoryStore
    from insult.core.memory_consolidator import (
        consolidate_all_users,
        consolidate_user_facts,
    )

    async def _run():
        # Job execution context: pull the live DB from Azure Blob first so
        # we don't operate on an empty ephemeral disk. Local dev (no
        # AZURE_STORAGE_CONNECTION_STRING) skips the download and uses
        # whatever's at settings.db_path.
        downloaded = False
        if is_azure_configured():
            downloaded = await download_db(settings.db_path)

        store = MemoryStore(settings.db_path)
        await store.connect()
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
        try:
            if user_id:
                report = await consolidate_user_facts(
                    user_id,
                    memory=store,
                    llm_client=client,
                    model=settings.summary_model,
                    dry_run=dry_run,
                )
                reports = [report]
            else:
                # Build user_id → display name map for the dream diary.
                # Falls back to user_id if the user has never sent a message.
                name_resolver = await _resolve_user_names(store)
                reports = await consolidate_all_users(
                    memory=store,
                    llm_client=client,
                    model=settings.summary_model,
                    dry_run=dry_run,
                    name_resolver=name_resolver,
                )
        finally:
            await store.close()

        # Push the curated DB back to Blob Storage. Skipped on dry_run
        # (nothing to upload) and when we're not in the Azure environment.
        if downloaded and not dry_run:
            uploaded = await upload_db(settings.db_path, skip_if_remote_newer=True)
            if not uploaded:
                log.warning(
                    "consolidator_upload_skipped",
                    reason="upload_db returned False — race with bot or upload failed",
                )

        return reports

    reports = asyncio.run(_run())
    typer.echo(f"\n{'DRY RUN — ' if dry_run else ''}Consolidation report ({len(reports)} users)")
    typer.echo("=" * 60)
    for r in reports:
        ops = r.counts_by_op()
        typer.echo(
            f"user={r.user_id}  in={r.facts_in:>3} out={r.facts_out:>3}  "
            f"NOOP={ops['NOOP']:>2} DELETE={ops['DELETE']:>2} UPDATE={ops['UPDATE']:>2}  "
            f"tokens={r.haiku_input_tokens}+{r.haiku_output_tokens}  "
            f"{r.duration_ms}ms" + (f"  ERROR={r.error}" if r.error else "")
        )


@app.command(name="moltbook-register")
def moltbook_register(
    name: str = typer.Option("Insult", help="Agent name as it will appear on Moltbook"),
    description: str = typer.Option(
        "Discord bot with longitudinal memory of two human users. "
        "Abrasive, curious, relational. Stack: Python + Claude.",
        help="One-paragraph agent description shown to other agents on Moltbook",
    ),
):
    """Self-register Insult on Moltbook (https://www.moltbook.com/skill.md flow).

    POSTs name + description to /api/v1/agents/register, prints the API
    key (ONCE — Moltbook does not let you recover it), the claim_url
    Bernard must visit to verify ownership, and the verification_code
    he must post on X to activate the agent.

    Run this once. Then save MOLTBOOK_API_KEY to Azure secret +
    .env, restart the bot, and the carretera both-ways picks up
    automatically once moltbook_inbound_enabled / outbound_enabled
    flip on.
    """
    from insult.core.sources.base import SourceError
    from insult.core.sources.moltbook import MoltbookSource

    async def _register() -> dict[str, str]:
        return await MoltbookSource.register_agent(name, description)

    try:
        result = asyncio.run(_register())
    except SourceError as e:
        typer.echo(f"\n❌ Moltbook rejected the registration:\n   {e}\n", err=True)
        raise typer.Exit(code=1) from e
    except ValueError as e:
        typer.echo(f"\n❌ Bad input: {e}\n", err=True)
        raise typer.Exit(code=2) from e

    typer.echo("\n✅ Moltbook agent registered\n")
    typer.echo(f"   Name:        {name}")
    typer.echo(f"   Verification code (post on X): {result['verification_code']}")
    typer.echo(f"   Claim URL:   {result['claim_url']}\n")
    typer.echo("To activate:")
    typer.echo("  1. Open the claim URL above and verify your email")
    typer.echo(f"  2. Post a tweet on X containing the verification code: {result['verification_code']}")
    typer.echo("  3. Moltbook will mark the agent as verified, the API key starts working\n")
    typer.echo("⚠️  API KEY — SAVE THIS NOW (Moltbook does NOT let you recover it):\n")
    typer.echo(f"     {result['api_key']}\n")
    typer.echo("Then store it in BOTH places:")
    typer.echo(
        '  • Azure secret:   az containerapp secret set -n insult-bot -g insult-rg --secrets "moltbook-api-key=<key>"'
    )
    typer.echo("  • Local .env:     MOLTBOOK_API_KEY=<key>\n")


async def _resolve_user_names(store) -> dict[str, str]:
    """Map user_id → most recent user_name from the messages table.

    The dream diary reads better with names ("Alex", "Bernard") than with
    Discord snowflake ids. Querying ``messages`` is dirt-cheap (indexed)
    and we only need the latest known name per user.
    """
    db = store._db
    if db is None:
        return {}
    cursor = await db.execute(
        "SELECT user_id, user_name FROM messages "
        "WHERE id IN ("
        "  SELECT MAX(id) FROM messages WHERE role = 'user' GROUP BY user_id"
        ")"
    )
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


if __name__ == "__main__":
    app()
