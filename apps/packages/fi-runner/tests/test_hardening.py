"""Tests for fi_runner hardening — input validation + error boundaries.

The defensive layer added before the hackathon, where consumers we don't control
feed the runner: it must fail fast on bad config/input, wrap any backend failure
in a typed :class:`BackendError` (root cause chained), and treat a raising guard
as a DEGRADED safety net (log + skip) rather than a turn killer.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fi_runner import BackendError, GuardOutcome, Runner, TurnResult


@dataclass
class _FakeBackend:
    text: str = "ok"

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text=self.text)


@dataclass
class _BoomBackend:
    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        raise RuntimeError("codex CLI not found")


@dataclass
class _BoomGuard:
    name: str = "boom"

    def inspect(self, **kwargs) -> GuardOutcome:  # noqa: ANN003
        raise ValueError("malformed regex")


# --- input validation ---------------------------------------------------------


def test_empty_persona_raises():
    with pytest.raises(ValueError, match="persona"):
        Runner(backend=_FakeBackend(), persona="   ")


@pytest.mark.asyncio
async def test_empty_user_message_raises():
    runner = Runner(backend=_FakeBackend(), persona="p")
    with pytest.raises(ValueError, match="user_message"):
        await runner.run("   ")


# --- backend error boundary ---------------------------------------------------


@pytest.mark.asyncio
async def test_backend_failure_wrapped_in_backend_error():
    runner = Runner(backend=_BoomBackend(), persona="p")
    with pytest.raises(BackendError) as ei:
        await runner.run("hola")
    assert isinstance(ei.value.__cause__, RuntimeError)  # root cause preserved
    assert "codex CLI not found" in str(ei.value)
    assert "_BoomBackend" in str(ei.value)  # which backend failed


@pytest.mark.asyncio
async def test_backend_error_emits_telemetry():
    events: list[tuple[str, dict]] = []
    runner = Runner(
        backend=_BoomBackend(), persona="p", on_event=lambda e, f: events.append((e, f))
    )
    with pytest.raises(BackendError):
        await runner.run("hola")
    assert any(e == "backend_error" for e, _ in events)


# --- guard error boundary -----------------------------------------------------


@pytest.mark.asyncio
async def test_raising_guard_does_not_kill_turn():
    events: list[tuple[str, dict]] = []
    runner = Runner(
        backend=_FakeBackend("respuesta válida del modelo"),
        persona="p",
        guards=[_BoomGuard()],
        on_event=lambda e, f: events.append((e, f)),
    )
    result = await runner.run("hola")
    assert result.text == "respuesta válida del modelo"  # backend text survives
    assert result.guard_outcomes["boom"].metadata["guard_failed"] is True
    assert "malformed regex" in result.guard_outcomes["boom"].metadata["error"]
    assert any(e == "guard_error" for e, _ in events)
