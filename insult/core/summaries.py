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

import structlog

# build_server_pulse / filter_by_permissions are pure stdlib helpers; they moved
# to the neutral `insult.core.server_pulse` module so the host can import them
# without crossing the host→smart boundary. Re-exported here for backwards
# compatibility (this module keeps the one LLM function, summarize_channel).
from insult.core.server_pulse import build_server_pulse, filter_by_permissions

log = structlog.get_logger()

__all__ = [
    "build_server_pulse",
    "filter_by_permissions",
    "summarize_channel",
]

SUMMARIZATION_PROMPT = (
    "You are a concise summarizer for a Discord server. "
    "Summarize the recent activity in channel #{channel_name} in 2-3 sentences. "
    "Focus on: main topics discussed, who's involved, any notable events or decisions. "
    "Write in the same language the messages use (usually Spanish). "
    "Be factual and brief — this is for internal context, not for users to read."
)


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
