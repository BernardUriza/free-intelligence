"""The dedup judge — one Haiku call over the user's full fact snapshot.

Shape B per memory:[[mcp-shape-b-canonical]]: fi-core owns the fact RENDER, the
JSON parser, op-shape validation, and implicit-NOOP backfill; this module only
orchestrates build → execute → parse. The CONSERVATIVE system prompt (default-
NOOP, "NEVER DELETE health/identity/trauma") is OURS, lives as content in
``prompts_md/memory_consolidator_judge.md``, and overrides fi-core's Mem0-style
curator — the prompt that buried Alex's CPTSD/quetiapina/psiquiatra cluster.
"""

from __future__ import annotations

import anthropic
import structlog

from khimeras_shared.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt

log = structlog.get_logger()

_PROMPT_CACHE: PromptCache = {}

# Output cap for the judge LLM. The plan must reference every input fact id in
# exactly one op (NOOP/DELETE/UPDATE), and each op carries a short reason string
# — so output tokens scale linearly with input fact count. The original 2048 cap
# silently truncated mid-JSON for users with ≥80 facts (Alex/CPTSD case: 92 facts
# → judge_failed every run from 2026-04-26 through 2026-04-27). Haiku 4.5 supports
# up to 8192 output tokens; 4x the original headroom covers ~300+ facts/user.
JUDGE_MAX_OUTPUT_TOKENS = 8192


async def _call_judge(
    llm,
    model: str,
    facts: list[dict],
) -> tuple[list[dict] | None, int, int]:
    """Single Haiku call. Returns (plan, input_tokens, output_tokens).

    ``llm.utility_call`` is RunnerJudgeClient in prod, a mock in tests. fi-core's
    ``parse_consolidation_result`` validates op shape, drops malformed ops, and
    backfills implicit NOOPs, so a non-None plan is ready to apply.
    """
    from fi_core.persona.mcp_server import (
        build_consolidation_prompt,
        parse_consolidation_result,
    )

    prompt_spec = await build_consolidation_prompt(
        facts=facts,
        max_tokens_hint=JUDGE_MAX_OUTPUT_TOKENS,
    )

    try:
        response = await llm.utility_call(
            load_prompt(SHARED_PROMPTS_DIR, "memory_consolidator_judge", _PROMPT_CACHE),
            [{"role": "user", "content": prompt_spec["user_text"]}],
            model=model,
            max_tokens=prompt_spec["max_tokens"],
        )
    except (anthropic.APIError, anthropic.APIConnectionError) as e:
        log.warning("consolidator_judge_call_failed", error=str(e))
        return None, 0, 0
    if response.stop_reason == "max_tokens":
        log.warning(
            "consolidator_judge_truncated",
            facts_in=len(facts),
            max_tokens=prompt_spec["max_tokens"],
        )

    parsed = await parse_consolidation_result(
        raw_response=response.text,
        facts=facts,
    )
    if not parsed["ok"]:
        log.warning(
            "consolidator_judge_parse_failed",
            error=parsed["error"],
            raw_len=parsed["raw_len"],
        )
        return None, 0, 0
    return parsed["ops"], 0, 0
