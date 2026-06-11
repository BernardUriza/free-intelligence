"""Extract and manage persistent user facts via LLM.

**Safety-net path alongside the persona's in-band ``[REMEMBER: <fact>]``
marker (`insult/core/remembers.py`).** The agent runner decides what's
worth remembering during the turn and emits the marker (source='agent');
``stages.py`` parses + persists it. This module is the AUTOMATIC backstop
that catches facts the model did *not* mark explicitly (source='auto').

``stages.py`` injects a ``RunnerJudgeClient`` (OAuth Max via the runner's
/v1/judge); this backstop catches facts the model forgot to mark in-band.
The marker path is primary; this is the automatic safety net.

The injected client only needs a ``utility_call`` returning an object
with ``.text`` + ``.stop_reason`` — ``RunnerJudgeClient`` satisfies that
contract.
"""

import json
from typing import Any, Protocol

import anthropic
import httpx
import structlog

from insult.core.prompts_loader import load_prompt

log = structlog.get_logger()


class _UtilityClient(Protocol):
    """The minimal surface extract_facts needs. RunnerJudgeClient satisfies
    this — the function is agnostic to the concrete client, it only requires
    a ``utility_call`` returning an object with ``.text`` + ``.stop_reason``."""

    async def utility_call(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        *,
        model: str | None = ...,
        max_tokens: int = ...,
    ) -> Any: ...


async def extract_facts(
    llm: _UtilityClient,
    model: str,
    user_name: str,
    existing_facts: list[dict],
    recent_messages: list[dict],
) -> list[dict]:
    """Extract/update user facts from recent conversation using LLM.

    Returns a list of fact dicts with 'fact' and 'category' keys.

    ``llm`` is any client exposing ``utility_call`` (a RunnerJudgeClient in
    prod, a mock in tests) — the output is structured JSON parsed downstream,
    so character_break detection + language_cure are the wrong tools here.
    Cache hits still apply when the system prompt is stable across users.
    """
    existing_str = "\n".join(f"- [{f['category']}] {f['fact']}" for f in existing_facts) if existing_facts else "(none)"

    conversation_str = "\n".join(f"{m.get('user_name', 'Insult')}: {m['content']}" for m in recent_messages[-10:])

    user_prompt = (
        f"User display name: {user_name}\n\nExisting facts:\n{existing_str}\n\nRecent conversation:\n{conversation_str}"
    )

    try:
        response = await llm.utility_call(
            load_prompt("facts_extraction"),
            [{"role": "user", "content": user_prompt}],
            model=model,
            max_tokens=4096,
        )
        raw = response.text.strip()
        if response.stop_reason == "max_tokens":
            log.warning("facts_extraction_truncated", user_name=user_name)
            return existing_facts

        # Parse JSON — handle markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        facts = json.loads(raw)
        if not isinstance(facts, list):
            log.warning("facts_extraction_bad_format", raw=raw[:200])
            return existing_facts

        valid = [
            {"fact": f["fact"], "category": f.get("category", "general")}
            for f in facts
            if isinstance(f, dict) and "fact" in f
        ]
        log.info("facts_extracted", user_name=user_name, count=len(valid))
        return valid

    except (json.JSONDecodeError, anthropic.APIError, httpx.HTTPError, KeyError, IndexError) as e:
        # httpx.HTTPError covers the RunnerJudgeClient transport path (timeout,
        # 5xx from /v1/judge). On any failure we keep existing_facts untouched
        # so a flaky extraction never erases what the marker path already saved.
        log.warning("facts_extraction_failed", error=str(e), error_type=type(e).__name__, user_name=user_name)
        return existing_facts


def norm_fact(s: str) -> str:
    """Normalize a fact's text for dedup: lowercase, whitespace-collapsed."""
    return " ".join(s.lower().split())


def merge_facts_additive(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], list[dict]]:
    """Union `incoming` facts onto `existing`, deduping by normalized text.

    ADD-only over DISTINCT facts: every distinct existing fact is preserved
    (first occurrence kept verbatim); only genuinely-new facts are appended.
    Returns ``(merged, added)``.

    This is the guard against `save_facts`' snapshot-replace silently dropping
    auto facts the extractor didn't echo back. The extractor only ever sees a
    SUBSET of stored auto facts (the prompt's semantic top-N, or — in the
    `!syncfacts` path — `get_facts` which extract may compress), yet
    `save_facts` REPLACES the full `source='auto'` snapshot. A naive
    ``save_facts(extractor_output)`` therefore hard-deletes every auto fact the
    extractor omitted, with no recovery (P0, 2026-06-03).

    `existing` is also deduped by `norm_fact` (PR-1 facts dedup, 2026-06-11):
    the live snapshot had accumulated byte-identical copies 20.8x over distinct
    facts (31,590 rows vs 1,517 distinct in prod), and `merged = list(existing)`
    re-inserted every copy on each save. Folding exact-normalized copies loses
    no distinct fact — the first save per user after this change rewrites the
    live `source='auto'` snapshot in deduplicated form. That snapshot is
    derived current state, not history: soft-deleted rows are untouched and
    near-miss rewordings are NOT collapsed (that remains the consolidator's
    job, gated separately).

    The remaining trade-off is deliberate per the operator's directive ("que
    no elimine nada absolutamente"): the extractor still cannot *correct* an
    auto fact in place — a reworded correction lands as an additional row.
    That cost is accepted; silent data loss is not.
    """
    seen: set[str] = set()
    merged: list[dict] = []
    for f in existing:
        text = f.get("fact", "")
        if not text:
            continue
        key = norm_fact(text)
        if key in seen:
            continue
        seen.add(key)
        merged.append(f)
    added: list[dict] = []
    for f in incoming:
        text = f.get("fact", "")
        if not text:
            continue
        key = norm_fact(text)
        if key in seen:
            continue
        seen.add(key)
        row = {"fact": text, "category": f.get("category", "general")}
        merged.append(row)
        added.append(row)
    return merged, added


def build_facts_prompt(user_name: str, facts: list[dict]) -> str:
    """Build a system prompt section with the user's known facts.

    When called with semantically-searched facts (via search_facts_semantic),
    the facts are already filtered to the most relevant ones for the current
    message. When called with all facts (fallback), all facts are included.

    Callers should use semantic search when len(facts) > 5 to avoid bloating
    the system prompt with irrelevant facts.
    """
    if not facts:
        return ""

    lines = [f"- [{f['category']}] {f['fact']}" for f in facts]
    return f"\n\n## What you know about {user_name} (use naturally, don't list these)\n" + "\n".join(lines)
