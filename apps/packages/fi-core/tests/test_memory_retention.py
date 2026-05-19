"""Tests for `fi_core.memory.retention`.

Three concrete policies + Protocol satisfaction.
"""

from __future__ import annotations

import pytest

from fi_core.memory import Default90d, RetentionPolicy
from fi_core.memory.retention import FixedWindow, NeverPurge


class TestProtocolSatisfaction:
    def test_default_90d_is_a_retention_policy(self):
        assert isinstance(Default90d(), RetentionPolicy)

    def test_fixed_window_is_a_retention_policy(self):
        assert isinstance(FixedWindow(seconds=86400), RetentionPolicy)

    def test_never_purge_is_a_retention_policy(self):
        assert isinstance(NeverPurge(), RetentionPolicy)


class TestDefault90d:
    def test_cutoff_is_now_minus_90_days(self):
        policy = Default90d()
        now = 1_000_000_000.0
        cutoff = policy.cutoff(now=now)
        assert cutoff == now - (90 * 86_400)

    def test_now_defaults_to_time_time(self, monkeypatch):
        import fi_core.memory.retention as retention_mod

        monkeypatch.setattr(retention_mod.time, "time", lambda: 500.0)
        policy = Default90d()
        cutoff = policy.cutoff()
        assert cutoff == 500.0 - (90 * 86_400)

    def test_principal_and_category_are_ignored(self):
        policy = Default90d()
        a = policy.cutoff(now=1.0, principal_id="u1", category="x")
        b = policy.cutoff(now=1.0, principal_id="u2", category="y")
        assert a == b


class TestFixedWindow:
    def test_custom_seconds(self):
        policy = FixedWindow(seconds=3600)
        cutoff = policy.cutoff(now=1000.0)
        assert cutoff == 1000.0 - 3600


class TestNeverPurge:
    def test_returns_negative_infinity(self):
        policy = NeverPurge()
        assert policy.cutoff() == float("-inf")
        # Any deleted_at < -inf is impossible, so no row purged
        assert policy.cutoff(now=999999.0) == float("-inf")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
