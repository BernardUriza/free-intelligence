"""Extract and manage persistent user facts via LLM.

After each conversation exchange, we ask the LLM to extract/update
interesting facts about the user. Facts are stored in SQLite and
injected into the system prompt so Insult always knows who it's
talking to — even across sessions.
"""

import json

import anthropic
import structlog

from insult.core.llm import LLMClient
from insult.core.prompts_loader import load_prompt

log = structlog.get_logger()


async def extract_facts(
    llm: LLMClient,
    model: str,
    user_name: str,
    existing_facts: list[dict],
    recent_messages: list[dict],
) -> list[dict]:
    """Extract/update user facts from recent conversation using LLM.

    Returns a list of fact dicts with 'fact' and 'category' keys.

    Uses LLMClient.utility_call (not chat) because the output is
    structured JSON parsed downstream — character_break detection +
    language_cure are wrong tools for that path. Cache hits still apply
    when the system prompt is stable across users.
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

    except (json.JSONDecodeError, anthropic.APIError, KeyError, IndexError) as e:
        log.warning("facts_extraction_failed", error=str(e), user_name=user_name)
        return existing_facts


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
