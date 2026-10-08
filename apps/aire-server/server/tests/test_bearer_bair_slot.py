"""BAIR has its own door slot, revocable alone (one slot per consumer)."""

from __future__ import annotations

import importlib

import aire.bearer


def test_the_bair_token_opens_the_door_and_only_when_set(monkeypatch):
    for k in ("AIRE_AUTH_TOKEN", "AIRE_CANARY_TOKEN", "AIRE_RUNNER_TOKEN", "AIRE_PULSE_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("AIRE_BAIR_TOKEN", "bair-slot-value")
    assert importlib.reload(aire.bearer).ACCEPTED_TOKENS == ("bair-slot-value",)

    monkeypatch.delenv("AIRE_BAIR_TOKEN")
    assert importlib.reload(aire.bearer).ACCEPTED_TOKENS == ()
    importlib.reload(aire.bearer)
