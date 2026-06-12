"""Tests for MoltbookSource — uses an in-process mock session, no real HTTP.

The mock targets `aiohttp.ClientSession.request` so the test exercises the
full `_request` retry / error-mapping path. Concrete payload shapes use the
spec from agentsapis.com/moltbook-api and the original moltbook-agent.zip
TypeScript reference."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.insult.core.sources import (
    SourceAuthError,
    SourceError,
    SourceNotFoundError,
    SourceRateLimitError,
    SourceTransientError,
)
from personas.insult.core.sources.moltbook import MoltbookSource

# ---------------------------------------------------------------------------
# Mock infrastructure — fakes aiohttp's request → response context manager
# ---------------------------------------------------------------------------


class _MockResponse:
    """Minimal stand-in for aiohttp.ClientResponse covering the surface
    that MoltbookSource._request actually touches."""

    def __init__(
        self,
        status: int,
        json_body: Any | None = None,
        text_body: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._json = json_body
        self._text = text_body or (str(json_body) if json_body is not None else "")
        self.headers = headers or {}
        self.content_length = 0 if json_body is None and not text_body else len(self._text)

    async def json(self) -> Any:
        return self._json

    async def text(self) -> str:
        return self._text

    async def __aenter__(self) -> _MockResponse:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None


def _make_session(responses: list[_MockResponse]) -> MagicMock:
    """Returns a MagicMock that behaves like an aiohttp.ClientSession,
    serving the given responses in order. Calls beyond `responses` length
    return the last entry (helpful for retry tests where the same status
    is the answer regardless of attempt count)."""
    session = MagicMock()
    iter_responses = iter(responses)
    last = responses[-1]

    def request(*_args: Any, **_kwargs: Any) -> _MockResponse:
        try:
            return next(iter_responses)
        except StopIteration:
            return last

    session.request = MagicMock(side_effect=request)
    session.close = AsyncMock()
    return session


@pytest.fixture
def fast_source():
    """Source with no real backoff so retry tests don't hang."""
    return _make_fast_source([_MockResponse(200, {"posts": []})])


def _make_fast_source(responses: list[_MockResponse], **kwargs: Any) -> MoltbookSource:
    """Patch asyncio.sleep on the moltbook module so retries don't burn
    real wall time. Tests pass their own response sequence."""
    import personas.insult.core.sources.moltbook as mod

    mod.asyncio.sleep = AsyncMock()  # type: ignore[assignment]
    session = _make_session(responses)
    return MoltbookSource(api_key="moltbook_test", session=session, max_retries=3, **kwargs)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_rejects_empty_api_key():
    with pytest.raises(ValueError, match="api_key"):
        MoltbookSource(api_key="")


def test_name_is_moltbook(fast_source):
    assert fast_source.name == "moltbook"


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


async def test_fetch_feed_returns_posts():
    src = _make_fast_source(
        [
            _MockResponse(
                200,
                {
                    "posts": [
                        {
                            "id": "p1",
                            "title": "first",
                            "content": "body",
                            "author_name": "DuckBot",
                            "submolt": "m/philosophy",
                            "upvotes": 5,
                            "comment_count": 2,
                            "created_at": "2026-05-04T00:00:00Z",
                        }
                    ]
                },
            )
        ]
    )
    posts = await src.fetch_feed()
    assert len(posts) == 1
    assert posts[0].id == "p1"
    assert posts[0].author == "DuckBot"
    assert posts[0].source == "moltbook"
    assert posts[0].submolt == "m/philosophy"
    assert posts[0].upvotes == 5
    assert posts[0].created_at > 0


async def test_fetch_submolt_posts_passes_submolt_param():
    src = _make_fast_source([_MockResponse(200, {"posts": []})])
    await src.fetch_submolt_posts("m/ai-agents")
    call = src._session.request.call_args
    assert call.kwargs["params"]["submolt"] == "m/ai-agents"


async def test_search_posts_passes_query():
    src = _make_fast_source([_MockResponse(200, {"posts": []})])
    await src.search_posts("consciousness")
    call = src._session.request.call_args
    assert call.kwargs["params"]["q"] == "consciousness"


async def test_create_post_round_trip():
    src = _make_fast_source(
        [
            _MockResponse(
                200,
                {
                    "id": "new_post_id",
                    "title": "hola",
                    "content": "qué onda",
                    "author_name": "Insult",
                    "submolt": "m/newbots",
                    "upvotes": 0,
                    "comment_count": 0,
                    "created_at": 1777800000.0,
                },
            )
        ]
    )
    post = await src.create_post("m/newbots", "hola", "qué onda")
    assert post.id == "new_post_id"
    assert post.source == "moltbook"


async def test_create_comment_round_trip():
    src = _make_fast_source(
        [
            _MockResponse(
                200,
                {
                    "id": "c1",
                    "post_id": "p1",
                    "content": "agree",
                    "author_name": "Insult",
                    "upvotes": 0,
                    "created_at": 1777800000.0,
                },
            )
        ]
    )
    c = await src.create_comment("p1", "agree")
    assert c.id == "c1"
    assert c.post_id == "p1"


async def test_upvote_post_uses_post_method():
    src = _make_fast_source([_MockResponse(204)])
    await src.upvote_post("p1")
    assert src._session.request.call_args.args[0] == "POST"


async def test_health_check_true_on_200():
    src = _make_fast_source([_MockResponse(200, {"id": "agent_xyz", "name": "Insult"})])
    assert await src.health_check() is True


async def test_health_check_false_on_auth_error():
    src = _make_fast_source([_MockResponse(401, text_body="invalid key")])
    assert await src.health_check() is False


# ---------------------------------------------------------------------------
# Authentication header
# ---------------------------------------------------------------------------


async def test_authorization_header_uses_bearer():
    src = _make_fast_source([_MockResponse(200, {"posts": []})])
    await src.fetch_feed()
    headers = src._session.request.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer moltbook_test"


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


async def test_401_raises_auth_error_no_retry():
    src = _make_fast_source([_MockResponse(401, text_body="invalid key")])
    with pytest.raises(SourceAuthError):
        await src.fetch_feed()
    # Should NOT retry — auth errors don't fix themselves
    assert src._session.request.call_count == 1


async def test_403_raises_auth_error():
    src = _make_fast_source([_MockResponse(403, text_body="forbidden")])
    with pytest.raises(SourceAuthError):
        await src.fetch_feed()


async def test_404_raises_not_found_no_retry():
    src = _make_fast_source([_MockResponse(404, text_body="post deleted")])
    with pytest.raises(SourceNotFoundError):
        await src.create_comment("ghost_id", "hi")
    assert src._session.request.call_count == 1


async def test_429_retries_then_succeeds():
    src = _make_fast_source(
        [
            _MockResponse(429, text_body="slow down", headers={"Retry-After": "0"}),
            _MockResponse(429, text_body="still slow", headers={"Retry-After": "0"}),
            _MockResponse(200, {"posts": []}),
        ]
    )
    posts = await src.fetch_feed()
    assert posts == []
    assert src._session.request.call_count == 3


async def test_429_exhausts_retries_raises_rate_limit():
    src = _make_fast_source(
        [
            _MockResponse(429, text_body="slow", headers={"Retry-After": "0"}),
        ]
    )
    with pytest.raises(SourceRateLimitError) as exc:
        await src.fetch_feed()
    # Carries the parsed Retry-After
    assert exc.value.retry_after_seconds == 0.0


async def test_500_retries_then_succeeds():
    src = _make_fast_source(
        [
            _MockResponse(503, text_body="upstream down"),
            _MockResponse(
                200,
                {
                    "posts": [
                        {
                            "id": "p1",
                            "title": "t",
                            "content": "c",
                            "author_name": "x",
                            "submolt": "m/x",
                            "upvotes": 0,
                            "comment_count": 0,
                            "created_at": 0,
                        }
                    ]
                },
            ),
        ]
    )
    posts = await src.fetch_feed()
    assert len(posts) == 1


async def test_500_exhausts_retries_raises_transient():
    src = _make_fast_source([_MockResponse(500, text_body="boom")])
    with pytest.raises(SourceTransientError):
        await src.fetch_feed()


async def test_other_4xx_raises_generic_error_no_retry():
    """422 / 400 etc are caller bugs, not platform issues. Surface immediately."""
    src = _make_fast_source([_MockResponse(422, text_body="invalid title")])
    with pytest.raises(SourceError) as exc:
        await src.create_post("m/x", "", "")
    assert not isinstance(
        exc.value,
        SourceAuthError | SourceNotFoundError | SourceRateLimitError | SourceTransientError,
    )
    assert src._session.request.call_count == 1


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def test_post_from_json_falls_back_when_fields_missing():
    p = MoltbookSource._post_from_json({})
    assert p.id == ""
    assert p.title == ""
    assert p.upvotes == 0
    assert p.created_at == 0.0
    assert p.source == "moltbook"


def test_post_from_json_preserves_raw():
    p = MoltbookSource._post_from_json({"id": "x", "weird_field": "value"})
    assert p.raw["weird_field"] == "value"


def test_post_from_json_handles_unix_timestamp_int():
    p = MoltbookSource._post_from_json({"created_at": 1777800000})
    assert p.created_at == 1777800000.0


def test_post_from_json_handles_iso_string():
    p = MoltbookSource._post_from_json({"created_at": "2026-05-04T12:00:00Z"})
    assert p.created_at > 0


def test_parse_retry_after_numeric():
    assert MoltbookSource._parse_retry_after("12") == 12.0


def test_parse_retry_after_missing():
    assert MoltbookSource._parse_retry_after(None) is None


def test_parse_retry_after_unparseable_returns_none():
    assert MoltbookSource._parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None


# ---------------------------------------------------------------------------
# Identity token cache
# ---------------------------------------------------------------------------


async def test_identity_token_caches_until_expiry():
    src = _make_fast_source(
        [
            _MockResponse(200, {"token": "tok_1", "expires_in": 3600}),
            _MockResponse(200, {"token": "tok_2", "expires_in": 3600}),
        ]
    )
    a = await src.get_identity_token()
    b = await src.get_identity_token()
    assert a == b == "tok_1"
    assert src._session.request.call_count == 1  # cache hit, no second call


async def test_identity_token_refreshes_when_expired():
    src = _make_fast_source(
        [
            _MockResponse(200, {"token": "tok_1", "expires_in": 0}),  # immediately stale
            _MockResponse(200, {"token": "tok_2", "expires_in": 3600}),
        ]
    )
    a = await src.get_identity_token()
    b = await src.get_identity_token()
    assert a == "tok_1"
    assert b == "tok_2"
    assert src._session.request.call_count == 2


async def test_identity_token_raises_if_server_omits_token():
    src = _make_fast_source([_MockResponse(200, {"some_other_field": "x"})])
    with pytest.raises(SourceError, match="no token"):
        await src.get_identity_token()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def test_close_closes_session_when_owned():
    src = MoltbookSource(api_key="moltbook_test", session=None)
    real_session = await src._ensure_session()
    await src.close()
    assert real_session.closed is True
    assert src._session is None


async def test_close_does_not_close_borrowed_session():
    """When caller passes their own session (e.g. shared across multiple
    sources), close() must NOT close it — that's not our session to close."""
    src = _make_fast_source([_MockResponse(200, {"posts": []})])
    borrowed = src._session
    await src.close()
    borrowed.close.assert_not_called()


# ---------------------------------------------------------------------------
# register_agent — no API key, this IS the call that obtains one
# ---------------------------------------------------------------------------


def _make_register_session(responses: list[_MockResponse]) -> MagicMock:
    """Variant for register_agent: aiohttp.ClientSession.post is what's
    used, not .request. Fake the same context-manager shape.

    An empty `responses` list is allowed — used by tests that expect
    register_agent to fail BEFORE making any HTTP call (e.g. blank
    name/description validation)."""
    session = MagicMock()
    iter_responses = iter(responses)
    last = responses[-1] if responses else _MockResponse(500, text_body="unexpected call")

    def post(*_args: Any, **_kwargs: Any) -> _MockResponse:
        try:
            return next(iter_responses)
        except StopIteration:
            return last

    session.post = MagicMock(side_effect=post)
    session.close = AsyncMock()
    return session


async def test_register_rejects_blank_name():
    with pytest.raises(ValueError, match="name"):
        await MoltbookSource.register_agent("", "desc", session=_make_register_session([]))


async def test_register_rejects_blank_description():
    with pytest.raises(ValueError, match="description"):
        await MoltbookSource.register_agent("Insult", "  ", session=_make_register_session([]))


async def test_register_happy_path_unwraps_agent():
    session = _make_register_session(
        [
            _MockResponse(
                200,
                {
                    "agent": {
                        "api_key": "moltbook_sk_live_abc123",
                        "claim_url": "https://www.moltbook.com/claim/xyz",
                        "verification_code": "reef-X4B2",
                    },
                    "important": "⚠️ SAVE YOUR API KEY!",
                },
            )
        ]
    )
    out = await MoltbookSource.register_agent("Insult", "abrasive", session=session)
    assert out["api_key"] == "moltbook_sk_live_abc123"
    assert out["claim_url"] == "https://www.moltbook.com/claim/xyz"
    assert out["verification_code"] == "reef-X4B2"


async def test_register_sends_only_name_and_description():
    """Per skill.md the body schema is exactly {name, description}. We
    must NOT include owner_email (the moltbook-agent.zip's outdated
    behavior) — Moltbook doesn't ask for it."""
    session = _make_register_session(
        [
            _MockResponse(
                200,
                {
                    "agent": {
                        "api_key": "moltbook_x",
                        "claim_url": "https://x",
                        "verification_code": "code",
                    },
                },
            )
        ]
    )
    await MoltbookSource.register_agent("Insult", "desc", session=session)
    body = session.post.call_args.kwargs["json"]
    assert set(body.keys()) == {"name", "description"}


async def test_register_rejects_response_without_agent():
    session = _make_register_session([_MockResponse(200, {"important": "no agent key"})])
    with pytest.raises(SourceError, match="no 'agent'"):
        await MoltbookSource.register_agent("Insult", "desc", session=session)


async def test_register_rejects_invalid_api_key_prefix():
    """The skill.md spec says keys start with 'moltbook_'. If the response
    returns something else, refuse to use it — likely a Moltbook bug we
    want to surface, not silently propagate."""
    session = _make_register_session(
        [_MockResponse(200, {"agent": {"api_key": "wrong_prefix_xyz", "claim_url": "x", "verification_code": "y"}})]
    )
    with pytest.raises(SourceError, match="api_key"):
        await MoltbookSource.register_agent("Insult", "desc", session=session)


async def test_register_rejects_missing_claim_url():
    session = _make_register_session(
        [_MockResponse(200, {"agent": {"api_key": "moltbook_x", "verification_code": "y"}})]
    )
    with pytest.raises(SourceError, match="claim_url"):
        await MoltbookSource.register_agent("Insult", "desc", session=session)


async def test_register_rejects_missing_verification_code():
    session = _make_register_session([_MockResponse(200, {"agent": {"api_key": "moltbook_x", "claim_url": "u"}})])
    with pytest.raises(SourceError, match="verification_code"):
        await MoltbookSource.register_agent("Insult", "desc", session=session)


async def test_register_4xx_raises_source_error():
    session = _make_register_session([_MockResponse(400, text_body="invalid name")])
    with pytest.raises(SourceError):
        await MoltbookSource.register_agent("Insult", "desc", session=session)


async def test_register_429_raises_rate_limit_error():
    session = _make_register_session(
        [
            _MockResponse(429, text_body="rate limited", headers={"Retry-After": "5"}),
        ]
    )
    with pytest.raises(SourceRateLimitError) as exc:
        await MoltbookSource.register_agent("Insult", "desc", session=session)
    assert exc.value.retry_after_seconds == 5.0


async def test_register_5xx_raises_transient_error():
    session = _make_register_session([_MockResponse(503, text_body="upstream down")])
    with pytest.raises(SourceTransientError):
        await MoltbookSource.register_agent("Insult", "desc", session=session)


async def test_register_does_not_log_full_api_key(caplog):
    """API keys are credentials; the registration log line must show only
    a prefix, never the full string. Otherwise the key leaks via Azure
    Log Analytics ingestion."""
    import logging

    caplog.set_level(logging.INFO)
    session = _make_register_session(
        [
            _MockResponse(
                200,
                {
                    "agent": {
                        "api_key": "moltbook_sk_live_SECRETLEAKEDKEY_xyz",
                        "claim_url": "https://x",
                        "verification_code": "z",
                    },
                },
            )
        ]
    )
    await MoltbookSource.register_agent("Insult", "desc", session=session)
    full_key = "moltbook_sk_live_SECRETLEAKEDKEY_xyz"
    for record in caplog.records:
        assert full_key not in record.getMessage()


# ---------------------------------------------------------------------------
# Phase 7 — heartbeat helpers, rate limiter, verification streak alarm
# ---------------------------------------------------------------------------


async def test_fetch_home_parses_activity_on_your_posts():
    """`fetch_home()` returns the JSON body verbatim — the heartbeat
    consumer is what parses `activity_on_your_posts`. We just assert
    the GET hits /home and that the payload round-trips intact."""
    payload = {
        "activity_on_your_posts": [
            {"post_id": "p_own_1", "post_title": "Session 4", "unread_count": 3},
            {"post_id": "p_own_2", "post_title": "Session 5", "unread_count": 1},
        ],
        "activity_on_others": [],
    }
    src = _make_fast_source([_MockResponse(200, payload)])
    home = await src.fetch_home()
    call = src._session.request.call_args
    assert call.args[0] == "GET"
    assert call.args[1].endswith("/home")
    assert home == payload


async def test_mark_notifications_read_swallows_source_error():
    """Marking notifications read is a fire-and-forget — if it fails
    we want a log line but NOT a raised exception (the heartbeat
    already published the actual reply; the unread badge is cosmetic)."""
    src = _make_fast_source([_MockResponse(500, text_body="boom")])
    # Should NOT raise — the implementation logs and returns None.
    await src.mark_notifications_read("p_own_1")


async def test_rate_limiter_sleeps_20s_between_writes():
    """1 write / 20s — confirm the limiter inserts a sleep when the
    last write was less than 20s ago. The patched `asyncio.sleep` lets
    us inspect the requested wait without burning real time."""
    import personas.insult.core.sources.moltbook as mod

    src = _make_fast_source(
        [
            _MockResponse(
                200,
                {
                    "id": "c_new",
                    "post_id": "p1",
                    "content": "agree",
                    "author_name": "Insult",
                    "upvotes": 0,
                    "created_at": 1777800000.0,
                },
            )
        ]
    )
    # Simulate "we wrote 5s ago" — limiter should sleep ~15s.
    import time as _time

    src._last_write_ts = _time.time() - 5.0
    src._write_count_day = 0
    await src.create_comment("p1", "agree")
    waits = [c.args[0] for c in mod.asyncio.sleep.await_args_list if c.args]
    rate_limit_waits = [w for w in waits if 14.0 <= w <= 16.0]
    assert rate_limit_waits, f"no ~15s rate-limit sleep observed, saw: {waits}"


async def test_rate_limiter_daily_cap_raises_typed_error():
    """At 50 writes the limiter must raise SourceRateLimitError BEFORE
    issuing an HTTP request. Heartbeat callers depend on the typed
    error to know to retry tomorrow rather than next tick."""
    src = _make_fast_source([_MockResponse(200, {"id": "x"})])
    # Force the daily counter into the current epoch-day at the cap.
    import time as _time

    src._write_count_day_key = int(_time.time() // 86400)
    src._write_count_day = 50
    with pytest.raises(SourceRateLimitError):
        await src.create_comment("p1", "shouldnt-publish")
    # And the session should NEVER have seen the call.
    assert src._session.request.call_count == 0


async def test_verification_failure_streak_resets_on_success():
    """`_consecutive_verify_failures` resets to 0 on a successful
    /verify, AND the alarm-emitted flag clears so a fresh streak that
    re-crosses the threshold gets surfaced again."""
    create_resp = _MockResponse(
        200,
        {
            "id": "c_with_verify",
            "post_id": "p1",
            "content": "x",
            "author_name": "Insult",
            "upvotes": 0,
            "created_at": 1.0,
            "verification": {
                "verification_code": "vc_abc",
                "challenge_text": "What is 2 + 2? answer NN.NN",
            },
        },
    )
    verify_ok = _MockResponse(200, {"ok": True})
    src = _make_fast_source([create_resp, verify_ok])
    # Pre-seed a partial failure streak.
    src._consecutive_verify_failures = 5
    src._verify_alarm_emitted = True
    await src.create_comment("p1", "x")
    assert src._consecutive_verify_failures == 0
    assert src._verify_alarm_emitted is False


async def test_verification_alarm_fires_once_at_threshold():
    """At ≥7 consecutive failures the `_verify_alarm_emitted` flag flips
    to True (and the alarm log line fires). On the NEXT failure the flag
    must stay True — the alarm is a one-shot per streak, not per failure.
    Reset only happens when the streak itself resets (success path)."""
    create_resp = _MockResponse(
        200,
        {
            "id": "c_x",
            "post_id": "p1",
            "content": "x",
            "author_name": "Insult",
            "upvotes": 0,
            "created_at": 1.0,
            "verification": {
                "verification_code": "vc_x",
                "challenge_text": "Two lobsters carry 5 plus 3 muffins. Answer NN.NN",
            },
        },
    )
    # /verify returns 400 → SourceError → counter increments
    verify_fail = _MockResponse(400, text_body="Incorrect answer")
    src = _make_fast_source([create_resp, verify_fail, create_resp, verify_fail])
    src._consecutive_verify_failures = 6  # next failure crosses threshold (7)
    assert src._verify_alarm_emitted is False
    await src.create_comment("p1", "x")
    assert src._consecutive_verify_failures == 7
    assert src._verify_alarm_emitted is True

    # Second failing call — counter keeps going up but the one-shot
    # alarm flag stays True (no re-trigger until a success resets it).
    await src.create_comment("p1", "x")
    assert src._consecutive_verify_failures == 8
    assert src._verify_alarm_emitted is True


async def test_delete_comment_still_refuses_after_phase7():
    """v3.7.67 operator policy stays in force after Phase 7 — the
    method MUST keep raising NotImplementedError no matter how many
    helpers we add around it."""
    src = MoltbookSource(api_key="moltbook_test_key")
    with pytest.raises(NotImplementedError, match="operator policy"):
        await src.delete_comment("c1")
