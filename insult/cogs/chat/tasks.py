"""Background-task orchestration: tracked spawning + fact extraction.

The tracked-spawn wrapper exists so EVERY background task emits a terminal
`background_task_ok` / `background_task_cancelled` / `background_task_failed`
log with a duration, regardless of whether the inner body logged on its
own. Before this wrapper was introduced, reactions or fact extraction that
failed silently left zero trace.
"""

from __future__ import annotations

import asyncio
import time

import structlog

from insult.core.facts import extract_facts, merge_facts_additive
from insult.core.guild_setup import post_facts_to_channel

log = structlog.get_logger()


def spawn_tracked_task(
    coro,
    registry: set[asyncio.Task],
    *,
    name: str | None = None,
) -> asyncio.Task:
    """Create an asyncio task that always logs its terminal state.

    `registry` is a mutable set owned by the cog so completed tasks are
    discarded automatically (prevents unbounded memory growth and stops
    asyncio from warning about un-awaited tasks). `name` is the semantic
    label for logs; falls back to the coroutine's __qualname__.
    """
    label = name or getattr(coro, "__qualname__", "unknown")
    spawn_started = time.monotonic()

    async def _tracked() -> None:
        try:
            await coro
            log.debug(
                "background_task_ok",
                task=label,
                duration_ms=int((time.monotonic() - spawn_started) * 1000),
            )
        except asyncio.CancelledError:
            log.info(
                "background_task_cancelled",
                task=label,
                duration_ms=int((time.monotonic() - spawn_started) * 1000),
            )
            raise
        except Exception:
            log.exception(
                "background_task_failed",
                task=label,
                duration_ms=int((time.monotonic() - spawn_started) * 1000),
            )

    task = asyncio.create_task(_tracked())
    registry.add(task)
    task.add_done_callback(registry.discard)
    return task


async def extract_user_facts(
    llm,
    summary_model: str,
    memory,
    bot,
    user_id: str,
    user_name: str,
    existing_facts: list[dict],
    recent: list[dict],
    guild_id: str | None = None,
    channel_name: str = "",
) -> None:
    """Run fact extraction against recent turns and persist any new facts.

    Posts safe additions to the system channel so the operator can audit
    what Insult is remembering without having to curl the debug endpoint.

    `llm` is the RunnerJudgeClient (the runner's one-shot /v1/judge) — fact
    extraction goes through its utility_call so the work runs on OAuth Max
    without a direct-Anthropic key and skips the user-facing guards.
    """
    try:
        new_facts = await extract_facts(llm, summary_model, user_name, existing_facts, recent)
        # P0 (2026-06-03): `existing_facts` is only the semantic top-N subset
        # injected into the prompt, but `memory.save_facts` REPLACES the whole
        # auto snapshot (DELETE … WHERE source='auto'). Saving `new_facts`
        # verbatim hard-deletes every auto fact outside the subset, every turn,
        # with no recovery — the real reason auto-facts never grew past ~10
        # ("Alex explains the same thing every day"). Union onto the COMPLETE
        # live auto set so extraction can only ADD, never destroy.
        all_auto = await memory.get_auto_facts(user_id)
        merged, added = merge_facts_additive(all_auto, new_facts)
        if added:
            await memory.save_facts(user_id, merged)
            log.info("facts_extracted_additive", user_id=user_id, added=len(added), total_auto=len(merged))
            if guild_id:
                await post_facts_to_channel(
                    bot,
                    memory,
                    guild_id,
                    user_name,
                    merged,
                    all_auto,
                    channel_name,
                )
    except Exception:
        log.exception("facts_extraction_background_failed", user_id=user_id)
