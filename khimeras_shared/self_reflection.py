"""Self-reflection — a persona chooses which tastes become permanent.

The Generative-Agents reflection pattern applied to `agent_facts`: on a slow
cadence a judge reads the persona's OWN recent turns plus its existing
self-facts and returns the 0-N new facts that earned permanence. Whatever
survives is written with `provenance='self_declared'` — acquired and selected
by the persona, durable across every future session.

The prompt is CONTENT (`prompts_md/self_reflection.md`), the parse is code, and
the whole path is best-effort: any fault returns an empty list, never an error
that could take a drain loop down.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from khimeras_shared.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt

log = structlog.get_logger()

_CACHE: PromptCache = {}

MAX_TURN_CHARS = 500


def build_reflection_material(existing: list[dict], turns: list[dict]) -> str:
    """The user-message body the judge reads: existing facts + recent turns."""
    lines = ["## (1) Self-facts ya registrados"]
    if existing:
        lines.extend(f"- [{f.get('category', 'general')}] {f.get('fact', '')}" for f in existing)
    else:
        lines.append("(ninguno todavía)")
    lines.append("\n## (2) Turnos recientes de la persona")
    for t in turns:
        content = (t.get("content") or "").strip()[:MAX_TURN_CHARS]
        if content:
            lines.append(f"- {content}")
    return "\n".join(lines)


def parse_reflection(raw: str, max_facts: int) -> list[dict]:
    """Strict-ish parse of the judge's JSON. Anything malformed → []."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log.warning("self_reflection_bad_json", preview=text[:120])
        return []
    if not isinstance(data, list):
        return []
    facts: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        fact = str(item.get("fact") or "").strip()
        if not fact:
            continue
        category = str(item.get("category") or "general").strip().lower() or "general"
        facts.append({"fact": fact, "category": category})
        if len(facts) >= max_facts:
            break
    return facts


async def reflect_self_facts(
    judge_client: Any,
    persona_name: str,
    existing: list[dict],
    turns: list[dict],
    *,
    max_facts: int = 3,
) -> list[dict]:
    """One reflection pass. Returns the new self-facts (possibly []).

    Raises httpx.HTTPError on transport failure so the caller can decide NOT to
    advance the cadence gate (a failed pass retries; an empty pass does not).
    """
    system_prompt = (
        load_prompt(SHARED_PROMPTS_DIR, "self_reflection", _CACHE)
        .replace("{persona_name}", persona_name)
        .replace("{max_facts}", str(max_facts))
    )
    material = build_reflection_material(existing, turns)
    resp = await judge_client.utility_call(
        system_prompt,
        [{"role": "user", "content": material}],
        max_tokens=1024,
    )
    facts = parse_reflection(resp.text, max_facts)
    log.info(
        "self_reflection_judged",
        persona_name=persona_name,
        turns=len(turns),
        existing=len(existing),
        new_facts=len(facts),
    )
    return facts


__all__ = ["build_reflection_material", "parse_reflection", "reflect_self_facts"]
