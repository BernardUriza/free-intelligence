"""User-fact engine — LLM extraction + the ADD-only merge that guards it.

Shared, persona-neutral (like `persona_core/style.py`): the facts a persona
learns about a user live in ONE `principal_facts` table that every persona reads,
so the engine that grows it belongs here, never in a persona package.

Two provenance tiers write to that table:
- `source='agent'` — the persona's in-band `[REMEMBER:]` marker
  (`persona_core.remember_marker`). Model-chosen, a pure INSERT.
- `source='auto'` — THIS module: the automatic backstop that catches facts the
  model did NOT mark explicitly. Runs one-shot on the runner's `/v1/judge`
  (`persona_core.runner.judge_client`), so no direct Anthropic key is needed.

## The P0 this module exists to not re-arm

`memory.save_facts` REPLACES the whole `source='auto'` snapshot (DELETE … WHERE
source='auto', then reinsert). The extractor, however, only ever SEES a SUBSET of
the stored facts (the prompt's top-N). So a naive `save_facts(extractor_output)`
hard-deletes every auto fact the extractor didn't echo back — every turn, with no
recovery (P0, 2026-06-03: a user's auto-facts could never grow past ~10).

`merge_facts_additive` is the guard: union the extractor's output onto the
COMPLETE live auto set (`memory.get_auto_facts`) so the snapshot handed to
`save_facts` is always a SUPERSET of what was already stored. Extraction can only
ADD. Never call `save_facts` with a raw extractor subset.

The prompt is CONTENT, not code: it lives in `prompts_md/facts_extraction.md` and
is loaded mtime-aware per call, so editing it hot-reloads with no redeploy
(playbook: prompts-as-content-not-code, P0). It is an ENGINE prompt (it extracts
facts ABOUT a user), not a persona's voice — hence `prompts_md/`, not
`shared/personas/guidance/`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

import httpx
import structlog

from persona_core.prompts import PromptCache, load_prompt

log = structlog.get_logger()

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts_md"
_CACHE: PromptCache = {}

__all__ = [
    "PROMPTS_DIR",
    "build_facts_prompt",
    "extract_facts",
    "merge_facts_additive",
    "norm_fact",
]


# The judge's request schema caps user_text at 256K chars (`JudgeRequest`), and a
# whale user's COMPLETE fact set blows straight through it: 3,345 facts / 300K
# chars → HTTP 422 on EVERY extraction, so the user's facts can never grow again
# (found 2026-07-20: Bernard frozen since the 07-14 purge). The extractor never
# needed the full set — the ADD-only merge unions against the complete live auto
# set regardless; the prompt's existing-facts section only helps the LLM avoid
# re-extracting RECENT knowledge. Newest-first budgets keep the payload bounded
# and the background cost sane.
EXISTING_FACTS_CHAR_BUDGET = 24_000
CONVERSATION_CHAR_BUDGET = 30_000


def _fit_lines(lines: list[str], budget: int, *, keep_tail: bool = False) -> list[str]:
    """Accumulate lines until `budget` chars. keep_tail=True keeps the LAST lines
    (for conversation, where the newest messages matter most)."""
    picked: list[str] = []
    total = 0
    for line in reversed(lines) if keep_tail else lines:
        total += len(line) + 1
        if total > budget:
            break
        picked.append(line)
    return picked[::-1] if keep_tail else picked


class UtilityClient(Protocol):
    """The minimal surface `extract_facts` needs. `RunnerJudgeClient` satisfies
    it — the function is agnostic to the concrete client, it only requires a
    `utility_call` returning an object with `.text` + `.stop_reason`."""

    async def utility_call(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        *,
        model: str | None = ...,
        max_tokens: int = ...,
    ) -> Any: ...


async def extract_facts(
    llm: UtilityClient,
    model: str | None,
    user_name: str,
    existing_facts: list[dict],
    recent_messages: list[dict],
) -> list[dict]:
    """Extract/update user facts from recent conversation via a one-shot LLM call.

    Returns a list of fact dicts with 'fact' and 'category' keys. On ANY failure
    (judge down, bad JSON, truncated output) it returns `existing_facts`
    UNCHANGED — a flaky extraction must never erase what is already stored.

    The caller MUST feed the result through `merge_facts_additive` against the
    full live auto set before persisting; this return value is a SUBSET view and
    is never safe to hand to `save_facts` directly.
    """
    existing_lines = [f"- [{f['category']}] {f['fact']}" for f in existing_facts]
    kept = _fit_lines(existing_lines, EXISTING_FACTS_CHAR_BUDGET)
    if len(kept) < len(existing_lines):
        log.info(
            "facts_prompt_existing_capped",
            user_name=user_name,
            shown=len(kept),
            total=len(existing_lines),
        )
    existing_str = "\n".join(kept) if kept else "(none)"
    conv_lines = [f"{m.get('user_name', 'persona')}: {m['content']}" for m in recent_messages[-10:]]
    conversation_str = "\n".join(_fit_lines(conv_lines, CONVERSATION_CHAR_BUDGET, keep_tail=True))
    user_prompt = (
        f"User display name: {user_name}\n\nExisting facts:\n{existing_str}\n\nRecent conversation:\n{conversation_str}"
    )

    try:
        response = await llm.utility_call(
            load_prompt(PROMPTS_DIR, "facts_extraction", _CACHE),
            [{"role": "user", "content": user_prompt}],
            model=model,
            max_tokens=4096,
        )
        raw = response.text.strip()
        if response.stop_reason == "max_tokens":
            log.warning("facts_extraction_truncated", user_name=user_name)
            return existing_facts

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

    except (json.JSONDecodeError, httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as e:
        # httpx.HTTPError covers the judge transport path (timeout, 5xx from
        # /v1/judge). On any failure we keep existing_facts untouched so a flaky
        # extraction never erases what the marker path already saved.
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
    auto facts the extractor didn't echo back (see the module docstring).

    `existing` is also deduped by `norm_fact` (PR-1 facts dedup, 2026-06-11):
    the live snapshot had accumulated byte-identical copies 20.8x over distinct
    facts (31,590 rows vs 1,517 distinct in prod), and `merged = list(existing)`
    re-inserted every copy on each save. Folding exact-normalized copies loses no
    distinct fact. Near-miss rewordings are NOT collapsed — that remains the
    consolidator's job, gated separately.

    The remaining trade-off is deliberate ("que no elimine nada absolutamente"):
    the extractor cannot *correct* an auto fact in place — a reworded correction
    lands as an additional row. That cost is accepted; silent data loss is not.
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
    """Build a system-prompt section with the user's known facts.

    When called with semantically-searched facts (via `search_facts_semantic`),
    the facts are already filtered to the most relevant ones for the current
    message. When called with all facts (fallback), all facts are included.
    """
    if not facts:
        return ""
    lines = [f"- [{f['category']}] {f['fact']}" for f in facts]
    return f"\n\n## What you know about {user_name} (use naturally, don't list these)\n" + "\n".join(lines)
