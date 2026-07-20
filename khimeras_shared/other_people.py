"""Facts about the OTHER participants of a channel, as a prompt block.

The runner rebuilds the AUTHOR's facts from its own filesystem (via the
`user_id` it receives), so a persona always knows who it is talking TO. It has
no such path for the people being talked ABOUT: facts about other channel
participants only ever existed in the plumbing-built prompt. Without this block
a persona recalls Alex when Alex writes (her `user_id`) yet answers "no me lo
has contado" when Bernard asks ABOUT her — the 2026-06-03 failure.

`AgentRunnerClient.chat(other_people=...)` already forwards the rendered block
as a prefix on the `user_text` the runner DOES read. This module is the missing
producer: it gathers the facts and renders them.

Died with `personas/insult` in the 2f8d9ad purge and is restored here as a
persona-agnostic shared capability. The header prose lives in
`prompts_md/other_people_header.md` — it is model-facing CONTENT, not code
(the pre-purge version inlined it in Python; that violation is not restored).
"""

from typing import Protocol

import structlog

from khimeras_shared.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt

log = structlog.get_logger()

_CACHE: PromptCache = {}

MAX_OTHER_PARTICIPANTS = 9


class _ParticipantFactsSource(Protocol):
    async def get_channel_participants(self, channel_id: str, limit: int = 10) -> list[dict]: ...

    async def get_facts_for_injection(self, user_id: str, auto_limit: int = 10) -> list[dict]: ...


def format_other_people_block(facts: dict[str, list[dict]]) -> str:
    """Render the participants' facts under the authoritative header.

    No extra per-person cap: `get_facts_for_injection` already bounds each list
    (all curated facts + the freshest auto ones). Re-capping here would drop
    curated facts again — the exact 2026-06-03 regression this path exists to
    fix. Returns "" for empty input so the caller can pass None downstream.
    """
    if not facts:
        return ""
    header = load_prompt(SHARED_PROMPTS_DIR, "other_people_header", _CACHE)
    lines = [
        f"- {name}: {'; '.join(f['fact'] for f in person_facts)}"
        for name, person_facts in facts.items()
        if person_facts
    ]
    if not lines:
        return ""
    return header + "\n" + "\n".join(lines)


async def load_other_participants_facts(
    memory: _ParticipantFactsSource,
    channel_id: str,
    *,
    exclude_user_id: str,
    limit: int = MAX_OTHER_PARTICIPANTS,
) -> dict[str, list[dict]]:
    """Curated-first facts for up to `limit` OTHER recent participants.

    The author is excluded — their own facts reach the model through the
    runner's own rebuild, and duplicating them here would invite the
    cross-attribution the header warns against.

    Best-effort: any fault returns {} and the turn ships without the block,
    never mute (same fail-safe posture as the guidance path).
    """
    out: dict[str, list[dict]] = {}
    try:
        participants = await memory.get_channel_participants(channel_id, limit=limit + 1)
        for participant in participants:
            participant_id = str(participant.get("user_id") or "")
            if not participant_id or participant_id == exclude_user_id:
                continue
            if len(out) >= limit:
                break
            facts = await memory.get_facts_for_injection(participant_id)
            if facts:
                out[participant.get("user_name") or participant_id] = facts
    except Exception:
        log.exception("other_participants_facts_failed", channel_id=channel_id)
        return {}
    return out


async def other_people_block_for_turn(
    memory: _ParticipantFactsSource,
    channel_id: str,
    *,
    exclude_user_id: str,
) -> str | None:
    """Load + render in one fail-safe call for the turn path. None when empty."""
    facts = await load_other_participants_facts(memory, channel_id, exclude_user_id=exclude_user_id)
    block = format_other_people_block(facts) or None
    if block:
        log.info(
            "other_people_block_built",
            channel_id=channel_id,
            participants=len(facts),
            facts_total=sum(len(v) for v in facts.values()),
            block_chars=len(block),
        )
    return block
