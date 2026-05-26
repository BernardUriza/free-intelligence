"""Configuration dataclasses for :class:`Runner` — retry policy + narrator.

Both are frozen immutable configs, completely independent of Runner state.
They live in their own module so a consumer can compose them without
touching the Runner class itself, and to keep ``runner.py`` focused on the
turn pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """How the runner retries a turn when a guard requests it.

    The guard decides WHETHER a turn is retry-worthy (``GuardOutcome.retry``);
    this policy decides HOW MANY times and on WHICH model. ``max_attempts=1``
    (the default) disables retry entirely — backward-compatible.
    """

    # Total turn attempts (1 = no retry). The final attempt runs guards with
    # ``final=True`` so transformational guards clean up instead of retrying.
    max_attempts: int = 1
    # Model to switch to on retry (e.g. a stronger tier). None = keep the model.
    fallback_model: str | None = None


@dataclass(frozen=True)
class FlowNarrator:
    """How the runner narrates each turn's flow diagram (the INSIDE view).

    After a turn settles, the runner hands the mechanical diagram + the turn's
    request/response back to its OWN backend and asks it to refine the Mermaid
    into a dev-facing narrative: what its cognitive process reasoned about, with
    new notes/edges/blocks and colors. This is a SECOND backend call, so it runs
    in the BACKGROUND (never delays the turn) and supersedes the mechanical
    diagram when it lands. A refinement is rejected (mechanical kept) if it isn't
    a Mermaid flowchart or drops the ``request_id`` anchor.

    Observability is core to Free Intelligence, so a Runner narrates by DEFAULT.
    Pass ``flow_narrator=None`` to disable it (e.g. a metered backend where a
    second call per turn isn't wanted). Pending narrations are drained by
    :meth:`Runner.aclose` — or use the runner as an async context manager.
    """

    # Override the turn's model for the narration call (e.g. a cheaper tier).
    model: str | None = None
    # Extra guidance appended to the narration system prompt.
    instructions: str | None = None


__all__ = ["RetryPolicy", "FlowNarrator"]
