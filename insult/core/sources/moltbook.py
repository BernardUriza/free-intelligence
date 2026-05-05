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
        verify_llm_solver: Any = None,
    ) -> None:
        if not api_key:
            raise ValueError("MoltbookSource requires a non-empty api_key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session = session
        self._owns_session = session is None
        # Optional async callable that maps a challenge_text → answer string.
        # When set, _auto_verify uses it INSTEAD of the regex solver — the
        # verification_code is single-use (a wrong answer burns it forever),
        # so an LLM is more reliable than chasing every English math
        # phrasing in regex. Falls back to the regex solver if it raises.
        self._verify_llm_solver = verify_llm_solver
        log.info(
            "moltbook_source_constructed",
            base_url=self._base_url,
            has_verify_llm_solver=verify_llm_solver is not None,
        )
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
        # The search endpoint returns {"results": [...]}, not "posts" — be
        # liberal in what we accept so a future API rename to "posts"
        # doesn't break the client either.
        rows = data.get("results") or data.get("posts") or []
        return [self._post_from_json(p) for p in rows]

    async def create_post(self, submolt: str, title: str, content: str) -> Post:
        data = await self._request(
            "POST",
            "/posts",
            json={"type": "text", "submolt": submolt, "title": title, "content": content},
        )
        inner = data.get("post") if isinstance(data.get("post"), dict) else data
        await self._auto_verify(inner)
        return self._post_from_json(inner)

    async def create_comment(self, post_id: str, content: str, *, parent_id: str | None = None) -> Comment:
        payload: dict[str, Any] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        data = await self._request(
            "POST",
            f"/posts/{post_id}/comments",
            json=payload,
        )
        inner = data.get("comment") if isinstance(data.get("comment"), dict) else data
        await self._auto_verify(inner)
        return self._comment_from_json(inner)

    async def _auto_verify(self, content_obj: dict[str, Any]) -> None:
        """If a freshly-created post/comment ships a verification challenge,
        solve the lobster math and POST /verify so the content goes from
        `pending` to `published`. Failure is logged but doesn't propagate
        — the underlying create succeeded; verification can be retried.

        Important: the verification_code is SINGLE-USE. A wrong answer burns
        it (subsequent /verify calls return 409 'Already answered'). So we
        log the answer we tried and the body of any error so a wrong solve
        is diagnosable without needing to repro."""
        verification = content_obj.get("verification")
        if not isinstance(verification, dict):
            return
        code = verification.get("verification_code")
        challenge = verification.get("challenge_text")
        content_id = content_obj.get("id")
        if not isinstance(code, str) or not isinstance(challenge, str):
            log.warning("moltbook_verification_malformed", verification=verification)
            return
        from insult.core.sources._moltbook_verify import solve_math_challenge

        # Prefer LLM solver when available — see _verify_llm_solver docstring.
        answer: str | None = None
        log.info(
            "moltbook_verification_path",
            content_id=content_id,
            has_llm_solver=self._verify_llm_solver is not None,
        )
        if self._verify_llm_solver:
            try:
                llm_answer = await self._verify_llm_solver(challenge)
                log.info(
                    "moltbook_verification_llm_returned",
                    content_id=content_id,
                    raw=llm_answer if isinstance(llm_answer, str) else type(llm_answer).__name__,
                )
                if isinstance(llm_answer, str) and llm_answer.strip():
                    answer = llm_answer.strip()
            except Exception:
                log.exception(
                    "moltbook_verification_llm_failed",
                    challenge=challenge[:300],
                    content_id=content_id,
                )
        if answer is None:
            try:
                answer = solve_math_challenge(challenge)
            except Exception:
                log.exception(
                    "moltbook_verification_solve_failed",
                    challenge=challenge[:300],
                    content_id=content_id,
                )
                return
        log.info(
            "moltbook_verification_attempt",
            content_id=content_id,
            answer=answer,
            challenge=challenge[:300],
        )
        try:
            await self._request("POST", "/verify", json={"verification_code": code, "answer": answer})
            log.info(
                "moltbook_verification_solved",
                content_id=content_id,
                answer=answer,
            )
        except SourceError as e:
            # SourceError carries the upstream body_text (e.g. the "Incorrect
            # answer" hint). Surface it so we know whether to expand the
            # solver or whether the API is doing something else.
            log.error(
                "moltbook_verification_post_failed",
                content_id=content_id,
                answer=answer,
                challenge=challenge[:300],
                error=str(e)[:500],
            )

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
    # Agent registration (no API key — this IS the call that obtains one)
    # ------------------------------------------------------------------

    @classmethod
    async def register_agent(
        cls,
        name: str,
        description: str,
        *,
        base_url: str = "https://www.moltbook.com/api/v1",
        timeout_seconds: float = 30.0,
        session: aiohttp.ClientSession | None = None,
    ) -> dict[str, str]:
        """Self-register a new agent on Moltbook. Per
        https://www.moltbook.com/skill.md this is the path agents take
        to bootstrap themselves: no API key required, just name +
        description.

        Returns a flat dict with the keys an operator needs:
          - api_key: starts with "moltbook_"; SAVE IT IMMEDIATELY,
            Moltbook does not let you recover it
          - claim_url: send the human there to verify ownership via X
          - verification_code: human posts this on X to activate

        The Moltbook response is wrapped in {"agent": {...}, "important":
        "..."}; we unwrap for caller convenience and validate every field
        is present and non-empty so a malformed server response surfaces
        as SourceError instead of silently returning blanks."""
        if not name.strip():
            raise ValueError("register_agent requires a non-empty name")
        if not description.strip():
            raise ValueError("register_agent requires a non-empty description")
        url = f"{base_url.rstrip('/')}/agents/register"
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        body = {"name": name, "description": description}

        owns_session = session is None
        sess = session or aiohttp.ClientSession(timeout=timeout)
        try:
            async with sess.post(url, headers=headers, json=body) as resp:
                status = resp.status
                text_body = (await resp.text())[:500]
                if 200 <= status < 300:
                    data = await resp.json()
                else:
                    if status in (401, 403):
                        raise SourceAuthError(f"register_agent → {status}: {text_body}")
                    if status == 429:
                        retry_after = cls._parse_retry_after(resp.headers.get("Retry-After"))
                        raise SourceRateLimitError(
                            f"register_agent → 429: {text_body}", retry_after_seconds=retry_after
                        )
                    if 500 <= status < 600:
                        raise SourceTransientError(f"register_agent → {status}: {text_body}")
                    raise SourceError(f"register_agent → {status}: {text_body}")
        finally:
            if owns_session:
                await sess.close()

        agent = data.get("agent") if isinstance(data, dict) else None
        if not isinstance(agent, dict):
            raise SourceError(f"register_agent: malformed response, no 'agent' object: {data!r}")
        api_key = agent.get("api_key")
        claim_url = agent.get("claim_url")
        verification_code = agent.get("verification_code")
        if not isinstance(api_key, str) or not api_key.startswith("moltbook_"):
            raise SourceError(f"register_agent: missing or invalid api_key in response: {agent!r}")
        if not isinstance(claim_url, str) or not claim_url:
            raise SourceError(f"register_agent: missing claim_url in response: {agent!r}")
        if not isinstance(verification_code, str) or not verification_code:
            raise SourceError(f"register_agent: missing verification_code in response: {agent!r}")
        log.info(
            "moltbook_agent_registered",
            name=name,
            verification_code=verification_code,
            api_key_prefix=api_key[:12],  # never log the full key
        )
        return {
            "api_key": api_key,
            "claim_url": claim_url,
            "verification_code": verification_code,
        }

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
        # author can be a flat string OR an object {id, name, ...}; submolt
        # likewise (search endpoint returns {id, name, displayName}, feed
        # sometimes returns a bare slug). Always project to a string.
        author_raw = data.get("author_name") or data.get("author") or ""
        if isinstance(author_raw, dict):
            author_raw = author_raw.get("name") or ""
        submolt_raw = data.get("submolt") or ""
        if isinstance(submolt_raw, dict):
            submolt_raw = submolt_raw.get("name") or ""
        return Post(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            content=str(data.get("content", "")),
            author=str(author_raw),
            submolt=str(submolt_raw),
            upvotes=int(data.get("upvotes", 0)),
            comment_count=int(data.get("comment_count", 0)),
            created_at=_parse_timestamp(data.get("created_at") or data.get("createdAt")),
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
