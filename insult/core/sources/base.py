"""Source ABC + shared dataclasses + error types.

The contract is intentionally small. We expose only what the carretera
lanes need today (fetch / search / post / comment / upvote / health). If
a future platform needs reply-to-comment or DM, it goes here as a new
abstract method and ALL concrete sources update at once — that's the
whole reason for the ABC.

Errors are typed so callers can be specific in their retry / surrender
logic. Generic 5xx and auth failures should NOT be retried the same way:
auth keeps failing forever, 5xx might recover in seconds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class SourceError(Exception):
    """Base for any platform error. Concrete sources raise subclasses."""


class SourceAuthError(SourceError):
    """401 / 403. The configured API key is invalid or expired. Do NOT retry."""


class SourceRateLimitError(SourceError):
    """429. Caller should back off using `retry_after_seconds` if provided."""

    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class SourceTransientError(SourceError):
    """5xx / connection / timeout. Retryable with exponential backoff."""


class SourceNotFoundError(SourceError):
    """404. Post deleted, submolt removed, user banned. Do NOT retry."""


# ---------------------------------------------------------------------------
# Dataclasses — platform-neutral representations
# ---------------------------------------------------------------------------


@dataclass
class Post:
    """A single post. Concrete sources map their schema onto this shape so
    downstream curation / digest rendering doesn't care which platform it
    came from. `raw` carries the original payload for sources that need to
    reach extra fields without breaking the abstraction."""

    id: str
    title: str
    content: str
    author: str
    submolt: str  # community / subreddit / channel — whatever the platform calls it
    upvotes: int
    comment_count: int
    created_at: float  # Unix timestamp
    url: str | None = None
    source: str = ""  # filled by the Source on output
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Comment:
    id: str
    post_id: str
    content: str
    author: str
    upvotes: int
    created_at: float
    source: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# The ABC
# ---------------------------------------------------------------------------


class Source(ABC):
    """A pluggable external content platform.

    Two responsibilities:
      • READ — fetch_feed, fetch_submolt_posts, search_posts (INBOUND lane)
      • WRITE — create_post, create_comment, upvote_post (OUTBOUND lane)

    Plus `health_check` for graceful degradation when an upstream API
    starts misbehaving."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform identifier used by the registry, e.g. 'moltbook'."""

    @abstractmethod
    async def fetch_feed(self, sort: str = "hot", limit: int = 10) -> list[Post]:
        """Fetch the personalized / global feed."""

    @abstractmethod
    async def fetch_submolt_posts(self, submolt: str, sort: str = "hot", limit: int = 10) -> list[Post]:
        """Fetch posts from a specific community."""

    @abstractmethod
    async def search_posts(self, query: str, limit: int = 10) -> list[Post]:
        """Free-text search."""

    @abstractmethod
    async def create_post(self, submolt: str, title: str, content: str) -> Post:
        """Publish a new post."""

    @abstractmethod
    async def create_comment(
        self, post_id: str, content: str, *, parent_id: str | None = None
    ) -> Comment:
        """Reply to an existing post. If `parent_id` is given the new
        comment is a reply to that comment (threaded), otherwise it's a
        top-level comment on the post."""

    @abstractmethod
    async def upvote_post(self, post_id: str) -> None:
        """Signal approval of a post. Idempotent at the platform level."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the platform is reachable + auth is valid. Used by
        background tasks to short-circuit before doing expensive work."""

    async def close(self) -> None:
        # Default no-op: simple sources (no persistent connection) inherit
        # this and skip overriding. HTTP-backed sources like Moltbook DO
        # override to close the aiohttp session. Intentionally NOT marked
        # @abstractmethod — adding @abstractmethod would force every future
        # in-memory or stateless Source to write `async def close: pass`.
        return None
