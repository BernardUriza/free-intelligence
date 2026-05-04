"""Moltbook HTTP client — concrete `Source` for the carretera both-ways.

Talks to https://www.moltbook.com/api/v1 with `Authorization: Bearer
moltbook_<key>`. Maps Moltbook's JSON onto the platform-neutral `Post`
and `Comment` dataclasses so the lanes never see Moltbook-specific
fields.

Retry shape mirrors `LLMClient._send` deliberately — the 30-second
timeout, exponential backoff on 429/5xx, give-up-on-401-immediately
behavior is production-tested in llm.py and we want the same posture
here. Any divergence in behavior between LLM retries and platform
retries will confuse on-call.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp
import structlog

from insult.core.sources.base import (
    Comment,
    Post,
    Source,
    SourceAuthError,
    SourceError,
    SourceNotFoundError,
    SourceRateLimitError,
    SourceTransientError,
)

log = structlog.get_logger()

# Identity tokens are short-lived per Moltbook spec. Re-fetch ~5 minutes
# before expiry so a slow request doesn't catch us holding a dead token.
_IDENTITY_TOKEN_TTL_SECONDS = 3600.0
_IDENTITY_TOKEN_REFRESH_BEFORE_EXPIRY = 300.0


class MoltbookSource(Source):
    """`Source` implementation backed by Moltbook's REST API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://www.moltbook.com/api/v1",
        max_retries: int = 4,
        timeout_seconds: float = 15.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("MoltbookSource requires a non-empty api_key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session = session
        self._owns_session = session is None
        # Identity token cache (used when the bot needs to prove its identity
        # to third-party services that integrate with Moltbook Identity).
        self._identity_token: str | None = None
        self._identity_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Source ABC
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "moltbook"

    async def fetch_feed(self, sort: str = "hot", limit: int = 10) -> list[Post]:
        data = await self._request(
            "GET",
            "/feed",
            params={"sort": sort, "limit": min(limit, 25)},
        )
        return [self._post_from_json(p) for p in data.get("posts", [])]

    async def fetch_submolt_posts(self, submolt: str, sort: str = "hot", limit: int = 10) -> list[Post]:
        data = await self._request(
            "GET",
            "/posts",
            params={"submolt": submolt, "sort": sort, "limit": min(limit, 25)},
        )
        return [self._post_from_json(p) for p in data.get("posts", [])]

    async def search_posts(self, query: str, limit: int = 10) -> list[Post]:
        data = await self._request(
            "GET",
            "/search/posts",
            params={"q": query, "limit": min(limit, 25)},
        )
        return [self._post_from_json(p) for p in data.get("posts", [])]

    async def create_post(self, submolt: str, title: str, content: str) -> Post:
        data = await self._request(
            "POST",
            "/posts",
            json={"type": "text", "submolt": submolt, "title": title, "content": content},
        )
        return self._post_from_json(data)

    async def create_comment(self, post_id: str, content: str) -> Comment:
        data = await self._request(
            "POST",
            f"/posts/{post_id}/comments",
            json={"content": content},
        )
        return self._comment_from_json(data)

    async def upvote_post(self, post_id: str) -> None:
        await self._request("POST", f"/posts/{post_id}/upvote")

    async def health_check(self) -> bool:
        """True if /agents/me responds 200 with our auth header."""
        try:
            await self._request("GET", "/agents/me")
            return True
        except SourceError:
            return False

    async def close(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Identity tokens (for third-party verification flows)
    # ------------------------------------------------------------------

    async def get_identity_token(self) -> str:
        """Return a cached Moltbook identity token, refreshing if expired.

        Identity tokens are 1-hour bearer tokens used to prove the agent's
        verified identity to third-party services that integrate with
        Moltbook Identity. Distinct from the API key (which we use to
        talk to Moltbook itself)."""
        now = time.time()
        if self._identity_token and self._identity_expires_at - _IDENTITY_TOKEN_REFRESH_BEFORE_EXPIRY > now:
            return self._identity_token
        data = await self._request("POST", "/agents/identity-token")
        token = data.get("token")
        if not token or not isinstance(token, str):
            raise SourceError(f"Moltbook /agents/identity-token returned no token: {data!r}")
        self._identity_token = token
        # Use the server-provided expiry if present; fall back to 1h.
        expires_in = float(data.get("expires_in", _IDENTITY_TOKEN_TTL_SECONDS))
        self._identity_expires_at = now + expires_in
        log.info("moltbook_identity_token_refreshed", expires_in=expires_in)
        return token

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue a request, applying retry policy and mapping HTTP status to
        typed SourceError subclasses. Returns the parsed JSON body on success.

        Retry posture (matches LLMClient._send):
          • 401 / 403 → SourceAuthError, no retry
          • 404       → SourceNotFoundError, no retry
          • 429       → SourceRateLimitError; back off using Retry-After
                        header if present, else exponential. Retry up to
                        max_retries times, then surface.
          • 5xx / connection / timeout → SourceTransientError; exponential
                        backoff, retry up to max_retries times.
          • 2xx       → return parsed JSON.
        """
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        last_error: Exception | None = None
        session = await self._ensure_session()

        for attempt in range(1, self._max_retries + 1):
            try:
                async with session.request(method, url, headers=headers, params=params, json=json) as resp:
                    status = resp.status
                    if 200 <= status < 300:
                        if status == 204 or resp.content_length == 0:
                            return {}
                        return await resp.json()
                    body_text = (await resp.text())[:500]

                    if status in (401, 403):
                        raise SourceAuthError(f"Moltbook {method} {path} → {status}: {body_text}")
                    if status == 404:
                        raise SourceNotFoundError(f"Moltbook {method} {path} → 404: {body_text}")
                    if status == 429:
                        retry_after = self._parse_retry_after(resp.headers.get("Retry-After"))
                        last_error = SourceRateLimitError(
                            f"Moltbook {method} {path} → 429: {body_text}",
                            retry_after_seconds=retry_after,
                        )
                        if attempt == self._max_retries:
                            raise last_error
                        wait = retry_after if retry_after is not None else 2**attempt
                        log.warning("moltbook_rate_limited", attempt=attempt, wait_seconds=wait, path=path)
                        await asyncio.sleep(wait)
                        continue
                    if 500 <= status < 600:
                        last_error = SourceTransientError(f"Moltbook {method} {path} → {status}: {body_text}")
                        if attempt == self._max_retries:
                            raise last_error
                        wait = 2**attempt
                        log.warning("moltbook_5xx", attempt=attempt, status=status, wait_seconds=wait, path=path)
                        await asyncio.sleep(wait)
                        continue
                    # 4xx other than the ones above → don't retry, surface
                    raise SourceError(f"Moltbook {method} {path} → {status}: {body_text}")
            except (TimeoutError, aiohttp.ClientConnectionError) as e:
                last_error = SourceTransientError(f"Moltbook {method} {path} → {type(e).__name__}: {e}")
                if attempt == self._max_retries:
                    raise last_error from e
                wait = 2**attempt
                log.warning(
                    "moltbook_transient", attempt=attempt, error_type=type(e).__name__, wait_seconds=wait, path=path
                )
                await asyncio.sleep(wait)
                continue

        # Should be unreachable — every code path either returns or raises.
        raise last_error or SourceError(f"Moltbook {method} {path} exhausted retries")

    @staticmethod
    def _parse_retry_after(header_value: str | None) -> float | None:
        """Parse a Retry-After header to seconds, accepting numeric or
        HTTP-date forms. Returns None if missing or unparseable."""
        if not header_value:
            return None
        try:
            return float(header_value)
        except ValueError:
            # HTTP-date form is rare for 429 but technically allowed; we don't
            # try to parse it — just fall through to exponential default.
            return None

    @staticmethod
    def _post_from_json(data: dict[str, Any]) -> Post:
        return Post(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            content=str(data.get("content", "")),
            author=str(data.get("author_name") or data.get("author", "")),
            submolt=str(data.get("submolt", "")),
            upvotes=int(data.get("upvotes", 0)),
            comment_count=int(data.get("comment_count", 0)),
            created_at=_parse_timestamp(data.get("created_at")),
            url=data.get("url"),
            source="moltbook",
            raw=data,
        )

    @staticmethod
    def _comment_from_json(data: dict[str, Any]) -> Comment:
        return Comment(
            id=str(data.get("id", "")),
            post_id=str(data.get("post_id", "")),
            content=str(data.get("content", "")),
            author=str(data.get("author_name") or data.get("author", "")),
            upvotes=int(data.get("upvotes", 0)),
            created_at=_parse_timestamp(data.get("created_at")),
            source="moltbook",
            raw=data,
        )


def _parse_timestamp(value: Any) -> float:
    """Best-effort parse of Moltbook's `created_at` field. Accepts ISO 8601
    strings, Unix timestamps (int or float), or returns 0.0 if neither."""
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            from datetime import datetime

            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0
