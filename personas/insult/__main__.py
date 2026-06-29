"""CLI entry point: python -m insult run

IMPORTANT: structlog must be configured BEFORE any insult module is imported,
because modules do `log = structlog.get_logger()` at import time.
"""

import asyncio

import structlog

from shared.logging_setup import configure_structlog


def _metrics_processor(logger, method_name, event_dict):
    """Structlog processor that feeds events to the dashboard metrics collector."""
    from personas.insult.core.metrics import record_event

    record_event(event_dict)
    return event_dict


# Configure structlog FIRST — before any insult.* import. The metrics
# processor is Insult-specific (feeds the dashboard); the base chain
# (timestamps, levels, contextvars, renderer) lives in shared/.
configure_structlog(processors_extra=[_metrics_processor])

# NOW import everything else
import typer  # noqa: E402

log = structlog.get_logger()
app = typer.Typer(help="Insult — Discord bot con memoria longitudinal + Claude API")


@app.command()
def run():
    """Start the Discord bot."""
    from personas.insult.bot import run as bot_run

    bot_run()


@app.command()
def db_stats():
    """Show memory database statistics."""
    from personas.insult.composition import create_memory_store
    from personas.insult.config import settings

    async def _stats():
        store = create_memory_store(settings.postgres_url.get_secret_value())
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

    from personas.insult.composition import create_memory_store
    from personas.insult.config import settings

    cutoff = time.time() - (before_days * 86400)

    async def _clean():
        store = create_memory_store(settings.postgres_url.get_secret_value())
        await store.connect()

        if dry_run:
            count = await store.count_before(cutoff)
            typer.echo(f"[DRY RUN] Would delete {count} messages older than {before_days} days")
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

    Post-PG migration: writes directly to the shared Postgres database
    (no more blob download/upload). Safe to run concurrently with the
    live bot — Postgres handles MVCC; the SQLite single-writer race is
    gone.
    """

    from personas.insult.composition import consolidate_all_users, consolidate_user_facts, create_memory_store
    from personas.insult.config import settings

    async def _run():
        # Post-PG migration: no more blob download/upload — the consolidator
        # writes straight to the shared Postgres database. Concurrent runs
        # with the live bot are safe because Postgres handles MVCC; the
        # SQLite single-writer race is gone.
        store = create_memory_store(settings.postgres_url.get_secret_value())
        await store.connect()
        # v3.9.82: consolidator delegates LLM execution to the runner's
        # /v1/judge endpoint instead of holding its own Anthropic API
        # key. Shape B per memory:[[mcp-shape-b-canonical]] — fi-core
        # builds + parses, the runner executes, this job orchestrates.
        # No ANTHROPIC_API_KEY needed; OAuth Max lives ONLY in the runner.
        from personas.insult.core.llm.runner_judge_client import RunnerJudgeClient

        runner_url = settings.insult_agent_runner_url
        runner_token = settings.insult_agent_runner_token.get_secret_value()
        if not runner_url or not runner_token:
            raise RuntimeError(
                "Consolidator requires INSULT_AGENT_RUNNER_URL + "
                "INSULT_AGENT_RUNNER_TOKEN env vars. Set them on the job:\n"
                "  az containerapp job secret set -n fact-consolidation -g insult-rg \\\n"
                "      --secrets agent-runner-token=<TOKEN>\n"
                "  az containerapp job update -n fact-consolidation -g insult-rg \\\n"
                "      --set-env-vars INSULT_AGENT_RUNNER_URL=https://persona-runner... \\\n"
                "                     INSULT_AGENT_RUNNER_TOKEN=secretref:agent-runner-token"
            )
        llm = RunnerJudgeClient(runner_url=runner_url, token=runner_token)
        try:
            if user_id:
                report = await consolidate_user_facts(
                    user_id,
                    memory=store,
                    llm=llm,
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
                    llm=llm,
                    model=settings.summary_model,
                    dry_run=dry_run,
                    name_resolver=name_resolver,
                )
        finally:
            await llm.aclose()
            await store.close()

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
    from personas.insult.core.sources.base import SourceError
    from personas.insult.core.sources.moltbook import MoltbookSource

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
    Discord snowflake ids. Delegates to the messages repo (which owns the
    SQL) so the CLI never reaches into private store internals."""
    return await store.get_latest_username_per_user()


if __name__ == "__main__":
    app()
