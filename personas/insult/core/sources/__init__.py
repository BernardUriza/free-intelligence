"""Platform abstraction for external content sources.

`Source` is the ABC every external platform implements (Moltbook today,
Reddit / HN / Mastodon later if Bernard wants the abstraction to flex).
The carretera both-ways tasks in `bot.py` only ever talk to a `Source`
handle obtained from the registry — they never construct a concrete
client directly. That is the whole point of this layer: lane logic
stays platform-agnostic, swap-in costs nothing.

See .claude/plans/elegant-foraging-knuth.md Phase 1 for the design
constraints (Plan agent validation already done).
"""

from personas.insult.core.sources.base import (
    Comment,
    Post,
    Source,
    SourceAuthError,
    SourceError,
    SourceNotFoundError,
    SourceRateLimitError,
    SourceTransientError,
)
from personas.insult.core.sources.registry import get_source, list_sources, register_source

__all__ = [
    "Comment",
    "Post",
    "Source",
    "SourceAuthError",
    "SourceError",
    "SourceNotFoundError",
    "SourceRateLimitError",
    "SourceTransientError",
    "get_source",
    "list_sources",
    "register_source",
]
