"""Cross-channel awareness via periodic channel summaries.

**DEPRECATED (v3.9.25, 2026-05-14)** — replaced by the workspace
renderer (`insult/agent/workspace_renderer.py`) which mirrors
Postgres → markdown every 60s and the agent runner's on-demand
Read/Grep over `messages/{channel_id}.md`. The persona's
"Cross-Channel Awareness" clause instructs the agent to read those
files when the user references another channel, replacing the
periodic Haiku summary pass. With ``LEGACY_LLM_ENABLED=false`` the
call here returns empty. Safe to delete once we confirm the agent
naturally reads workspace files on cross-channel queries.

Provides LLM-based channel summarization and a "Server Pulse" digest
that gives the bot awareness of what's happening across all channels.
"""

import time

import structlog

log = structlog.get_logger()

SUMMARIZATION_PROMPT = (
    "You are a concise summarizer for a Discord server. "
    "Summarize the recent activity in channel #{channel_name} in 2-3 sentences. "
    "Focus on: main topics discussed, who's involved, any notable events or decisions. "
    "Write in the same language the messages use (usually Spanish). "
    "Be factual and brief — this is for internal context, not for users to read."
)

# 24 hours in seconds
_TWENTY_FOUR_HOURS = 86400


async def summarize_channel(llm, model: str, channel_name: str, messages: list[dict]) -> str:
    """Call LLM to summarize recent channel activity.

    Routes through the runner's one-shot /v1/judge (utility_call) — runs on
    OAuth Max without the user-facing guards that don't apply to internal
    summaries.

    Args:
        llm: a client exposing ``utility_call`` (RunnerJudgeClient in prod).
        model: Model name (e.g. claude-haiku-4-5-20251001).
        channel_name: Human-readable channel name.
        messages: List of message dicts with user_name, role, content, timestamp.

    Returns:
        Summary string (2-3 sentences).
    """
    if not messages:
        return ""

    # Format messages for the summarizer
    formatted = "\n".join(f"{m['user_name']}: {m['content'][:200]}" for m in messages[-50:])

    prompt = SUMMARIZATION_PROMPT.replace("{channel_name}", channel_name)

    try:
        response = await llm.utility_call(
            prompt,
            [{"role": "user", "content": f"Messages from #{channel_name}:\n\n{formatted}"}],
            model=model,
            max_tokens=150,
        )
        return response.text.strip()
    except Exception:
        log.exception("channel_summarization_failed", channel=channel_name)
        return ""


def build_server_pulse(
    summaries: list[dict],
    current_message: str = "",
    max_chars: int = 1200,
) -> str:
    """Format channel summaries into a compact digest for the system prompt.

    Args:
        summaries: List of summary dicts from get_channel_summaries().
        current_message: Current user message for relevance scoring.
        max_chars: Maximum character budget for the pulse.

    Returns:
        Formatted pulse string, or "" if no relevant summaries.
    """
    if not summaries:
        return ""

    now = time.time()

    # Filter out summaries older than 24h
    recent_summaries = [s for s in summaries if (now - s["updated_at"]) < _TWENTY_FOUR_HOURS]
    if not recent_summaries:
        return ""

    # Extract significant words from current message for relevance scoring
    significant_words = set()
    if current_message:
        significant_words = {w.lower() for w in current_message.split() if len(w) > 3}

    # Score summaries by keyword overlap + recency
    scored = []
    for s in recent_summaries:
        # Keyword relevance score
        summary_words = {w.lower() for w in s["summary"].split() if len(w) > 3}
        channel_words = {w.lower() for w in s["channel_name"].split("-") if len(w) > 3}
        all_words = summary_words | channel_words
        keyword_score = len(significant_words & all_words) if significant_words else 0

        # Recency score (0-1, higher = more recent)
        age_hours = (now - s["updated_at"]) / 3600
        recency_score = max(0, 1 - (age_hours / 24))

        # Combined score: keywords matter more than recency
        total_score = keyword_score * 3 + recency_score
        scored.append((total_score, s))

    # Sort by score descending, take top 5
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:5]]

    if not top:
        return ""

    # Format the pulse
    lines = [
        "## Server Pulse (what's happening in other channels)\n"
        "This is BACKGROUND CONTEXT ONLY. Do NOT address people from other channels "
        "in your current response. Do NOT confuse names or topics from other channels "
        "with the person you're talking to right now."
    ]
    char_count = len(lines[0])

    for s in top:
        age_hours = (now - s["updated_at"]) / 3600
        age_str = f"hace {int(age_hours * 60)}min" if age_hours < 1 else f"hace {int(age_hours)}h"

        line = f"- #{s['channel_name']} ({age_str}, {s['message_count']} msgs): {s['summary']}"

        if char_count + len(line) + 1 > max_chars:
            break
        lines.append(line)
        char_count += len(line) + 1

    # Need at least one channel summary beyond the header
    if len(lines) < 2:
        return ""

    return "\n".join(lines)


def filter_by_permissions(summaries: list[dict], accessible_channel_ids: set[str]) -> list[dict]:
    """Filter summaries to only include channels the user can access.

    Args:
        summaries: List of summary dicts.
        accessible_channel_ids: Set of channel ID strings the user can read.

    Returns:
        Filtered list of summaries.
    """
    return [s for s in summaries if s["channel_id"] in accessible_channel_ids]
