"""Tests for insult.core.errors — in-character error responses."""

from personas.insult.core.errors import classify_error, get_error_response


class TestGetErrorResponse:
    def test_returns_string(self):
        assert isinstance(get_error_response("generic"), str)

    def test_timeout_response(self):
        resp = get_error_response("timeout")
        assert len(resp) > 10

    def test_rate_limit_response(self):
        resp = get_error_response("rate_limit")
        assert len(resp) > 10

    def test_auth_response(self):
        resp = get_error_response("auth")
        assert len(resp) > 10

    def test_too_long_response(self):
        resp = get_error_response("too_long")
        assert len(resp) > 10

    def test_context_failed_response(self):
        resp = get_error_response("context_failed")
        assert len(resp) > 10

    def test_unknown_type_falls_back_to_generic(self):
        resp = get_error_response("nonexistent_type")
        assert isinstance(resp, str)
        assert len(resp) > 10

    def test_billing_response(self):
        resp = get_error_response("billing")
        assert len(resp) > 10

    def test_no_response_mentions_claude(self):
        """Insult NEVER reveals the underlying model in errors."""
        for error_type in [
            "timeout",
            "rate_limit",
            "auth",
            "generic",
            "too_long",
            "context_failed",
            "retry_notice",
            "billing",
        ]:
            for _ in range(10):  # sample random responses
                resp = get_error_response(error_type)
                assert "Claude" not in resp
                assert "claude" not in resp
                assert "Anthropic" not in resp
                assert "API" not in resp


class TestClassifyError:
    def test_timeout_error(self):
        class FakeTimeoutError(Exception):
            pass

        FakeTimeoutError.__name__ = "APITimeoutError"
        assert classify_error(FakeTimeoutError()) == "timeout"

    def test_rate_limit_error(self):
        class FakeRateLimitError(Exception):
            pass

        FakeRateLimitError.__name__ = "RateLimitError"
        assert classify_error(FakeRateLimitError()) == "rate_limit"

    def test_auth_error(self):
        class FakeAuthError(Exception):
            pass

        FakeAuthError.__name__ = "AuthenticationError"
        assert classify_error(FakeAuthError()) == "auth"

    def test_generic_error(self):
        assert classify_error(ValueError("something")) == "generic"

    def test_unknown_error(self):
        assert classify_error(RuntimeError("boom")) == "generic"

    def test_billing_error_by_credit_balance_message(self):
        """Real 2026-04-24 incident: Anthropic returns a 400 BadRequestError
        whose message contains 'credit balance is too low' when the workspace
        wallet runs out. The classifier MUST route this to 'billing' so the
        operator sees a clear "pay the API" prompt instead of the vague
        'generic tropiezo' message that hid the real problem for an hour."""

        class FakeBadRequestError(Exception):
            pass

        FakeBadRequestError.__name__ = "BadRequestError"
        exc = FakeBadRequestError(
            "Error code: 400 - {'message': 'Your credit balance is too low to access the Anthropic API.'}"
        )
        assert classify_error(exc) == "billing"

    def test_billing_error_detected_even_with_timeout_name(self):
        """Message-content check runs BEFORE the name-based matchers, so even
        if some hypothetical subclass is named with 'Timeout' but carries a
        credit-balance message, we route to billing. Prevents a stuck user
        from getting routed to 'timeout' when the real cause is money."""

        class WeirdTimeoutError(Exception):
            pass

        WeirdTimeoutError.__name__ = "APITimeoutError"
        exc = WeirdTimeoutError("credit balance too low, cannot proceed")
        assert classify_error(exc) == "billing"

    def test_insufficient_quota_also_classifies_as_billing(self):
        """Some API gateways return the phrase 'insufficient_quota' instead
        of 'credit balance'. Both must route to billing."""
        assert classify_error(Exception("insufficient_quota for this request")) == "billing"

    def test_billing_does_not_false_positive_on_plain_balance_talk(self):
        """Make sure the matcher doesn't grab 'balance' in unrelated contexts.
        An error mentioning 'balance' without 'credit' should stay generic."""
        assert classify_error(ValueError("work-life balance issue")) == "generic"
