"""What AIRE lends an invited key, and what that turn costs it (backlog #32).

The gateway door spends AIRE's own money for an invited caller, so two things
must be exactly right and neither is observable from a green deploy: the
credential swap (an OAuth token is worthless on /v1/messages without its beta
header) and the price of a turn (Anthropic reports tokens, never dollars, so a
mispriced turn is a ceiling that does not bite).
"""

import pytest

from aire import lending, pricing

CALLER = [("anthropic-version", "2023-06-01"),
          ("anthropic-beta", "context-1m-2025-08-07"),
          ("authorization", "Bearer sk-ant-the-callers-own"),
          ("x-api-key", "sk-the-callers-own")]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    lending._inflight.clear()


def _dict(headers):
    return {k.lower(): v for k, v in headers}


def test_nothing_to_lend_is_none_not_a_naked_request():
    assert lending.lend(CALLER) is None


def test_oauth_is_lent_with_its_beta_appended_not_replacing(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oat-aire-own")
    sent = _dict(lending.lend(CALLER))
    assert sent["authorization"] == "Bearer oat-aire-own"
    assert "x-api-key" not in sent, "the caller's own key must not ride along"
    assert sent["anthropic-beta"] == f"context-1m-2025-08-07,{lending.OAUTH_BETA}"
    assert sent["anthropic-version"] == "2023-06-01", "unrelated headers survive"


def test_oauth_beta_added_when_the_caller_sent_none(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oat-aire-own")
    sent = _dict(lending.lend([("anthropic-version", "2023-06-01")]))
    assert sent["anthropic-beta"] == lending.OAUTH_BETA


def test_a_metered_key_wins_and_needs_no_beta(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oat-aire-own")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-metered")
    sent = _dict(lending.lend(CALLER))
    assert sent["x-api-key"] == "sk-ant-metered"
    assert "authorization" not in sent
    assert sent["anthropic-beta"] == "context-1m-2025-08-07"


def test_slots_bound_the_grace_window():
    assert [lending.enter("nick") for _ in range(lending.MAX_INFLIGHT)] == [True] * lending.MAX_INFLIGHT
    assert lending.enter("nick") is False
    lending.leave("nick")
    assert lending.enter("nick") is True
    assert lending.enter("someone else") is True, "slots are per key, not global"


def test_price_of_a_plain_turn():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert pricing.usd(usage, "claude-opus-5") == pytest.approx(30.0)


def test_cache_is_priced_by_ttl_and_reads_are_cheap():
    usage = {"input_tokens": 0, "output_tokens": 0,
             "cache_read_input_tokens": 1_000_000,
             "cache_creation": {"ephemeral_1h_input_tokens": 1_000_000,
                                "ephemeral_5m_input_tokens": 1_000_000}}
    # opus-5 input is $5/M: read 0.1x + 1h write 2x + 5m write 1.25x = 3.35x
    assert pricing.usd(usage, "claude-opus-5") == pytest.approx(5.0 * 3.35)


def test_a_bare_cache_total_is_billed_at_the_dearer_ttl():
    usage = {"cache_creation_input_tokens": 1_000_000}
    assert pricing.usd(usage, "claude-opus-5") == pytest.approx(10.0)


def test_an_unknown_model_is_never_free():
    usage = {"input_tokens": 1_000_000}
    dearest = max(r["input"] for r in pricing._table().values())
    assert pricing.usd(usage, "claude-something-unreleased") == pytest.approx(dearest)


def test_fast_mode_costs_double():
    usage = {"input_tokens": 1_000_000, "speed": "fast"}
    assert pricing.usd(usage, "claude-opus-5") == pytest.approx(10.0)


def test_no_usage_is_zero_and_the_caller_decides_what_that_means():
    assert pricing.usd(None, "claude-opus-5") == 0.0
