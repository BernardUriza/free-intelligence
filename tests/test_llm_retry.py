"""Retry-policy tests for LLMClient._send (PR 0 of turn_resilience).

Covers:
- ``_parse_retry_after`` header parsing edge cases.
- ``_full_jitter_backoff`` bounds.
- ``RateLimitError`` (429) honors ``retry-after`` when present, else Full Jitter.
- ``APIStatusError`` 500/502/503/529 are retried (regression: pre-PR0 we
  ``break``-ed at the first 500).
- ``APIStatusError`` 504 is treated as timeout family — capped at
  ``_MAX_TIMEOUT_RETRIES`` regardless of ``max_retries``.
- ``APITimeoutError`` / ``APIConnectionError`` retry with Full Jitter.
- ``BadRequestError`` and other ``APIStatusError`` codes still ``break``.

Mocks the streaming context manager so no real network or sleep happens.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest

from insult.core.llm import (
    _BACKOFF_CAP_5XX,
    _BACKOFF_CAP_429,
    _BACKOFF_CAP_TIMEOUT,
    LLMClient,
    _full_jitter_backoff,
    _parse_retry_after,
)

# ---------- Pure helpers ----------


class TestParseRetryAfter:
    def test_none_headers_returns_none(self):
        assert _parse_retry_after(None) is None

    def test_object_without_get_returns_none(self):
        assert _parse_retry_after("not-a-headers-object") is None

    def test_seconds_header_valid(self):
        h = httpx.Headers({"retry-after": "5"})
        assert _parse_retry_after(h) == 5.0

    def test_milliseconds_header_takes_precedence(self):
        # When both are present the millisecond version is more precise; honor it.
        h = httpx.Headers({"retry-after": "5", "retry-after-ms": "2500"})
        assert _parse_retry_after(h) == 2.5

    def test_milliseconds_header_alone(self):
        h = httpx.Headers({"retry-after-ms": "1500"})
        assert _parse_retry_after(h) == 1.5

    def test_value_above_cap_returns_none(self):
        # >60s falls through to our own jittered backoff.
        h = httpx.Headers({"retry-after": "120"})
        assert _parse_retry_after(h) is None

    def test_value_zero_returns_none(self):
        h = httpx.Headers({"retry-after": "0"})
        assert _parse_retry_after(h) is None

    def test_negative_value_returns_none(self):
        h = httpx.Headers({"retry-after": "-1"})
        assert _parse_retry_after(h) is None

    def test_malformed_header_returns_none(self):
        h = httpx.Headers({"retry-after": "soon"})
        assert _parse_retry_after(h) is None

    def test_malformed_ms_falls_back_to_seconds(self):
        h = httpx.Headers({"retry-after-ms": "garbage", "retry-after": "3"})
        assert _parse_retry_after(h) == 3.0

    def test_missing_returns_none(self):
        h = httpx.Headers({"x-other": "1"})
        assert _parse_retry_after(h) is None


class TestFullJitterBackoff:
    def test_attempt_one_within_bounds(self):
        for _ in range(50):
            v = _full_jitter_backoff(1, cap=10.0)
            assert 0 <= v <= 2.0  # 2 ** 1 = 2

    def test_attempt_three_within_bounds(self):
        for _ in range(50):
            v = _full_jitter_backoff(3, cap=30.0)
            assert 0 <= v <= 8.0  # 2 ** 3 = 8

    def test_cap_clamps_high_attempts(self):
        # 2 ** 10 = 1024, but cap pins it.
        for _ in range(50):
            v = _full_jitter_backoff(10, cap=5.0)
            assert 0 <= v <= 5.0

    def test_attempt_below_one_treated_as_one(self):
        for _ in range(50):
            v = _full_jitter_backoff(0, cap=10.0)
            assert 0 <= v <= 2.0


# ---------- Retry loop integration ----------


@pytest.fixture
def client():
    with patch("insult.core.llm.anthropic.AsyncAnthropic"):
        return LLMClient(api_key="fake", model="sonnet-default", max_tokens=512, timeout=1.0, max_retries=3)


def _mk_response_for_error(status: int, headers: dict[str, str] | None = None) -> httpx.Response:
    """Build an httpx.Response suitable for instantiating an SDK error."""
    return httpx.Response(status, headers=httpx.Headers(headers or {}), request=httpx.Request("POST", "https://x"))


def _mk_rate_limit(headers: dict[str, str] | None = None) -> anthropic.RateLimitError:
    return anthropic.RateLimitError("rate limited", response=_mk_response_for_error(429, headers), body=None)


def _mk_status(status: int, headers: dict[str, str] | None = None) -> anthropic.APIStatusError:
    return anthropic.APIStatusError(f"status {status}", response=_mk_response_for_error(status, headers), body=None)


def _mk_bad_request() -> anthropic.BadRequestError:
    return anthropic.BadRequestError("bad request", response=_mk_response_for_error(400), body=None)


def _patch_stream_to_raise_then_succeed(client: LLMClient, errors: list[Exception], success_text: str = "ok"):
    """Configure ``messages.stream(...)`` to raise each error in order, then
    yield a successful final message. Returns the mock for assertions."""
    from insult.core.llm import LLMResponse  # local to avoid circular import noise

    class _SuccessMsg:
        # Shape required by _send: .content (list with .text), .usage.*, .stop_reason
        class _Usage:
            input_tokens = 1
            output_tokens = 1
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 0

        usage = _Usage()
        stop_reason = "end_turn"

        @property
        def content(self):
            block = MagicMock()
            block.text = success_text
            block.type = "text"
            return [block]

    success_stream = MagicMock()
    success_stream.__aenter__ = AsyncMock(
        return_value=MagicMock(get_final_message=AsyncMock(return_value=_SuccessMsg()))
    )
    success_stream.__aexit__ = AsyncMock(return_value=None)

    def make_failing_stream(exc: Exception):
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=exc)
        cm.__aexit__ = AsyncMock(return_value=None)
        return cm

    sequence = [make_failing_stream(e) for e in errors] + [success_stream]
    mock_stream = MagicMock(side_effect=sequence)
    client.client.messages.stream = mock_stream
    return mock_stream, LLMResponse


@pytest.mark.asyncio
async def test_rate_limit_honors_retry_after_header(client, monkeypatch):
    """429 with retry-after=2: we sleep 2s exactly, no jitter math."""
    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    monkeypatch.setattr("insult.core.llm.asyncio.sleep", fake_sleep)
    err = _mk_rate_limit({"retry-after": "2"})
    mock_stream, _ = _patch_stream_to_raise_then_succeed(client, [err], success_text="recovered")

    result = await client._send("sys", [{"role": "user", "content": "hi"}])

    assert result.text == "recovered"
    assert sleep_calls == [2.0]
    assert mock_stream.call_count == 2


@pytest.mark.asyncio
async def test_rate_limit_falls_back_to_jitter_when_no_header(client, monkeypatch):
    """429 with no retry-after: Full Jitter sleep ≤ cap."""
    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    monkeypatch.setattr("insult.core.llm.asyncio.sleep", fake_sleep)
    err = _mk_rate_limit()  # no headers
    _patch_stream_to_raise_then_succeed(client, [err])

    await client._send("sys", [{"role": "user", "content": "hi"}])

    assert len(sleep_calls) == 1
    assert 0 <= sleep_calls[0] <= _BACKOFF_CAP_429


@pytest.mark.asyncio
async def test_rate_limit_ignores_oversized_retry_after(client, monkeypatch):
    """retry-after=120 (>60s cap) is ignored — we use our own jitter cap."""
    sleep_calls: list[float] = []
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock(side_effect=lambda s: sleep_calls.append(s)))

    err = _mk_rate_limit({"retry-after": "120"})
    _patch_stream_to_raise_then_succeed(client, [err])

    await client._send("sys", [{"role": "user", "content": "hi"}])

    assert len(sleep_calls) == 1
    assert sleep_calls[0] <= _BACKOFF_CAP_429


@pytest.mark.asyncio
async def test_status_500_now_retries(client, monkeypatch):
    """REGRESSION: pre-PR0 a 500 caused immediate ``break``. Now it retries
    with Full Jitter (5xx cap) and recovers."""
    sleep_calls: list[float] = []
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock(side_effect=lambda s: sleep_calls.append(s)))

    err = _mk_status(500)
    mock_stream, _ = _patch_stream_to_raise_then_succeed(client, [err], success_text="500 recovered")

    result = await client._send("sys", [{"role": "user", "content": "hi"}])

    assert result.text == "500 recovered"
    assert mock_stream.call_count == 2
    assert len(sleep_calls) == 1
    assert 0 <= sleep_calls[0] <= _BACKOFF_CAP_5XX


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [502, 503])
async def test_status_502_503_retries(client, monkeypatch, code):
    """502 and 503 are also in the transient 5xx family."""
    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    monkeypatch.setattr("insult.core.llm.asyncio.sleep", fake_sleep)
    _patch_stream_to_raise_then_succeed(client, [_mk_status(code)])
    await client._send("sys", [{"role": "user", "content": "hi"}])
    assert len(sleep_calls) == 1
    assert sleep_calls[0] <= _BACKOFF_CAP_5XX


@pytest.mark.asyncio
async def test_status_529_retries_with_overloaded_event(client, monkeypatch):
    """529 keeps the historical ``llm_overloaded`` event name (alerts depend on it)."""
    sleep_calls: list[float] = []
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock(side_effect=lambda s: sleep_calls.append(s)))

    err = _mk_status(529, {"retry-after": "3"})
    _patch_stream_to_raise_then_succeed(client, [err])

    await client._send("sys", [{"role": "user", "content": "hi"}])

    # retry-after honored
    assert sleep_calls == [3.0]


@pytest.mark.asyncio
async def test_status_504_treated_as_timeout(client, monkeypatch):
    """504 counts toward ``_MAX_TIMEOUT_RETRIES`` (=2), not ``max_retries``."""
    sleep_calls: list[float] = []
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock(side_effect=lambda s: sleep_calls.append(s)))

    # Three consecutive 504s; we should give up after 2 timeout-class attempts.
    errs = [_mk_status(504), _mk_status(504), _mk_status(504)]
    # All three failing means no success at the end.
    failing_streams = []
    for e in errs:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=e)
        cm.__aexit__ = AsyncMock(return_value=None)
        failing_streams.append(cm)
    client.client.messages.stream = MagicMock(side_effect=failing_streams)

    with pytest.raises(anthropic.APIStatusError):
        await client._send("sys", [{"role": "user", "content": "hi"}])

    # _MAX_TIMEOUT_RETRIES=2 → first attempt fails, second fails, then break
    # without sleeping after the second. So only 1 sleep between the two attempts.
    assert len(sleep_calls) == 1
    assert sleep_calls[0] <= _BACKOFF_CAP_TIMEOUT


@pytest.mark.asyncio
async def test_status_504_fires_on_timeout_callback(client, monkeypatch):
    """504, like APITimeoutError, fires the ``on_timeout`` callback once."""
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock())
    notice = AsyncMock()

    err = _mk_status(504)
    _patch_stream_to_raise_then_succeed(client, [err])

    await client._send("sys", [{"role": "user", "content": "hi"}], on_timeout=notice)
    assert notice.await_count == 1


@pytest.mark.asyncio
async def test_status_404_does_not_retry(client):
    """Non-transient APIStatusError codes still ``break`` immediately."""
    err = _mk_status(404)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=err)
    cm.__aexit__ = AsyncMock(return_value=None)
    client.client.messages.stream = MagicMock(return_value=cm)

    with pytest.raises(anthropic.APIStatusError):
        await client._send("sys", [{"role": "user", "content": "hi"}])

    assert client.client.messages.stream.call_count == 1


@pytest.mark.asyncio
async def test_bad_request_without_tools_does_not_retry(client):
    """BadRequestError unrelated to tools is fatal."""
    err = _mk_bad_request()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=err)
    cm.__aexit__ = AsyncMock(return_value=None)
    client.client.messages.stream = MagicMock(return_value=cm)

    with pytest.raises(anthropic.BadRequestError):
        await client._send("sys", [{"role": "user", "content": "hi"}])
    assert client.client.messages.stream.call_count == 1


@pytest.mark.asyncio
async def test_api_timeout_uses_full_jitter(client, monkeypatch):
    """APITimeoutError now sleeps with Full Jitter (was: fixed 1s)."""
    sleep_calls: list[float] = []
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock(side_effect=lambda s: sleep_calls.append(s)))

    err = anthropic.APITimeoutError(request=httpx.Request("POST", "https://x"))
    _patch_stream_to_raise_then_succeed(client, [err], success_text="recovered after timeout")

    result = await client._send("sys", [{"role": "user", "content": "hi"}])

    assert result.text == "recovered after timeout"
    assert len(sleep_calls) == 1
    assert 0 <= sleep_calls[0] <= _BACKOFF_CAP_TIMEOUT


@pytest.mark.asyncio
async def test_api_connection_error_uses_full_jitter(client, monkeypatch):
    sleep_calls: list[float] = []
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock(side_effect=lambda s: sleep_calls.append(s)))

    err = anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))
    _patch_stream_to_raise_then_succeed(client, [err])

    await client._send("sys", [{"role": "user", "content": "hi"}])

    assert len(sleep_calls) == 1
    assert 0 <= sleep_calls[0] <= _BACKOFF_CAP_TIMEOUT


@pytest.mark.asyncio
async def test_rate_limit_capped_by_max_retries(client, monkeypatch):
    """When every attempt is 429, we exhaust ``max_retries`` and raise."""
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock())

    failing_streams: list[Any] = []
    for _ in range(5):  # more than max_retries=3
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=_mk_rate_limit())
        cm.__aexit__ = AsyncMock(return_value=None)
        failing_streams.append(cm)
    client.client.messages.stream = MagicMock(side_effect=failing_streams)

    with pytest.raises(anthropic.RateLimitError):
        await client._send("sys", [{"role": "user", "content": "hi"}])

    # Exactly max_retries calls, no more.
    assert client.client.messages.stream.call_count == 3


@pytest.mark.asyncio
async def test_rate_limit_then_500_then_success(client, monkeypatch):
    """Mixed transient errors all retry through to a successful response."""
    sleep_calls: list[float] = []
    monkeypatch.setattr("insult.core.llm.asyncio.sleep", AsyncMock(side_effect=lambda s: sleep_calls.append(s)))

    errs = [_mk_rate_limit({"retry-after": "1"}), _mk_status(500)]
    _patch_stream_to_raise_then_succeed(client, errs, success_text="finally")

    result = await client._send("sys", [{"role": "user", "content": "hi"}])

    assert result.text == "finally"
    # One sleep per failed attempt.
    assert len(sleep_calls) == 2
    assert sleep_calls[0] == 1.0  # respected retry-after
    assert sleep_calls[1] <= _BACKOFF_CAP_5XX  # jittered 500 backoff
