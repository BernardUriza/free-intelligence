"""Mutation pipeline — Intercepting Filter pattern with per-stage invariants.

Why this exists
---------------
The post-LLM path applies a chain of text-mutation stages
(``strip_metadata``, ``deduplicate_opener``, ``language_cure``, etc.). On
2026-05-06 ``deduplicate_opener`` silently deleted **51% of a substantive
empathic response to a vulnerable user** because its "is this a name
collision?" matcher fired on the common Spanish demonstrative *"Eso"*.
The mutation was logged via ``text_mutated`` but nothing blocked it —
telemetry without a guard is a surveillance camera that watches the
robbery. The user only noticed because the reply felt cortante.

The fix is structural, not a patch on that one regex. Each mutation
stage now declares ``(invariant, on_violation_policy)`` pairs and the
pipeline runner enforces them between stages, so a future stage with a
similarly catch-all matcher cannot silently nuke the body again — the
violation is logged AND the mutation is rejected.

This is the Validator + on_fail policy shape used by Guardrails AI and
NeMo Guardrails, structured as a Python dataclass + async runner that
fits the existing list-of-functions chain without re-architecting the
callsites. See research notes in `.claude/plans/` and the Phase 8
commit message for the pattern citations.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Invariant helpers — built-in must_preserve callables
# ---------------------------------------------------------------------------
#
# Each helper returns True when the invariant HOLDS, False when it's been
# violated (so a stage that breaks the invariant gets rejected). They
# accept (before, after) — never the stage context — so they're trivially
# composable across stages with different ``ctx`` shapes.
#
# Add new invariants here, not inline in stage definitions. Inlining
# breeds the "many lambdas" anti-pattern and obscures the intent at the
# call site.

_REACT_MARKER_RE = re.compile(r"\[REACT:[^\]]*\]")


def preserve_react_markers(before: str, after: str) -> bool:
    """The number of [REACT:emoji,emoji] markers must not decrease.

    deduplicate_opener — the stage that triggered this whole module —
    nuked the entire first line of the response, which contained the
    ``[REACT:🌊💙🪷🫂🌿✨]`` block intended for the user. Stages that are
    not strip_reactions (which deliberately removes them) must keep the
    count intact.
    """
    return len(_REACT_MARKER_RE.findall(after)) >= len(_REACT_MARKER_RE.findall(before))


def preserve_question_marks(before: str, after: str) -> bool:
    """If the original asked a question, the mutation must keep at least one.

    A mutation that strips every '?' from a response with explicit user
    questions is almost certainly recording a meaningful semantic loss —
    block it and let the next attempt try.
    """
    if "?" in before:
        return "?" in after
    return True


def preserve_min_length(min_chars: int) -> Callable[[str, str], bool]:
    """Floor: 'don't let a stage take a non-empty response below N chars.'

    Returns a callable so this can parameterize per stage.
    """

    def _check(before: str, after: str) -> bool:
        if len(before) >= min_chars:
            return len(after) >= min_chars
        return True

    _check.__name__ = f"preserve_min_length({min_chars})"
    return _check


# ---------------------------------------------------------------------------
# MutationStage + on_violation policies
# ---------------------------------------------------------------------------

OnViolation = Literal["skip_stage", "abort_pipeline", "raise", "log_only"]
"""Per-stage failure policy.

- ``skip_stage`` (default) — mutation is rejected, the stage is treated
  as a no-op, telemetry fires. The pipeline continues to the next stage.
  Right answer for stages that are *cosmetic* (deduplication, formatting):
  if they fail their invariant, the pre-mutation text was probably fine.
- ``abort_pipeline`` — the mutation is rejected AND no further stage
  runs. Use for stages where the violation suggests an upstream break
  that further processing would compound.
- ``raise`` — let the caller handle it. Reserved for tests / dev-only.
- ``log_only`` — accept the mutation, just log the violation. Use only
  when you have telemetry but cannot yet trust the invariant enough to
  block (rollout shadow mode).
"""


@dataclass
class MutationStage:
    """One step in the post-LLM mutation chain.

    The ``apply`` callable can be sync OR async — the runner detects and
    awaits if needed. Keep the signature ``(text, ctx) -> str`` so a
    stage can pull side data (recent_openers, user_profile) out of
    ``ctx`` without changing the runner.
    """

    name: str
    apply: Callable[[str, dict[str, Any]], str | Awaitable[str]]
    max_shrink_pct: float | None = 0.40
    """Reject the mutation if it shrinks the text by more than this fraction.

    ``None`` disables the length guard for stages where shrinkage is
    legitimate (e.g. ``strip_reactions`` may legitimately remove 100% of
    a reaction-only response).
    """
    must_preserve: list[Callable[[str, str], bool]] = field(default_factory=list)
    on_violation: OnViolation = "skip_stage"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class PipelineViolationError(Exception):
    """Raised by ``run_pipeline`` when a stage's policy is ``"raise"``."""

    def __init__(self, stage: str, failed: list[str], before_len: int, after_len: int) -> None:
        super().__init__(f"stage={stage} violations={failed} {before_len}->{after_len} chars")
        self.stage = stage
        self.failed = failed
        self.before_len = before_len
        self.after_len = after_len


def _shrink_pct(before: str, after: str) -> float:
    if not before:
        return 0.0
    return max(0.0, (len(before) - len(after)) / len(before))


def _check_invariants(stage: MutationStage, before: str, after: str) -> list[str]:
    """Return the names of invariants that the mutation broke. Empty list = OK."""
    failed: list[str] = []
    if stage.max_shrink_pct is not None and _shrink_pct(before, after) > stage.max_shrink_pct:
        failed.append(f"max_shrink_pct({stage.max_shrink_pct:.2f})")
    for check in stage.must_preserve:
        try:
            if not check(before, after):
                failed.append(check.__name__ or repr(check))
        except Exception:
            log.exception("pipeline_invariant_check_raised", stage=stage.name, check=getattr(check, "__name__", None))
            # A broken invariant check is itself a violation — bias toward
            # rejecting the mutation rather than silently accepting it.
            failed.append(f"{getattr(check, '__name__', 'check')}:raised")
    return failed


async def run_pipeline(
    stages: list[MutationStage],
    text: str,
    ctx: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> str:
    """Apply ``stages`` in order, enforcing each stage's invariants.

    Telemetry: emits one ``mutation_applied`` event per stage that
    actually changed the text, and one ``pipeline_violation`` event for
    every rejected mutation. Both include ``stage``, ``before_len``,
    ``after_len``, ``shrink_pct`` and (for violations) ``failed_invariants``
    + ``policy``.
    """
    ctx = ctx or {}
    for stage in stages:
        before = text
        try:
            result = stage.apply(text, ctx)
            if inspect.isawaitable(result):
                result = await result  # type: ignore[assignment]
            after = result if isinstance(result, str) else str(result)
        except Exception:
            log.exception("pipeline_stage_raised", stage=stage.name, request_id=request_id)
            # A raising stage does not get to mutate text — keep ``before``.
            continue
        if after == before:
            continue
        failed = _check_invariants(stage, before, after)
        if failed:
            log.warning(
                "pipeline_violation",
                stage=stage.name,
                policy=stage.on_violation,
                failed_invariants=failed,
                before_len=len(before),
                after_len=len(after),
                shrink_pct=round(_shrink_pct(before, after), 4),
                request_id=request_id,
            )
            if stage.on_violation == "raise":
                raise PipelineViolationError(stage.name, failed, len(before), len(after))
            if stage.on_violation == "abort_pipeline":
                return before
            if stage.on_violation == "skip_stage":
                # Reject this stage's mutation; keep going with the
                # pre-mutation text so the next stage operates on what
                # the user *would* have received without this stage.
                text = before
                continue
            # log_only — accept anyway. Shadow-mode rollout option.
            text = after
            continue
        log.info(
            "mutation_applied",
            stage=stage.name,
            before_len=len(before),
            after_len=len(after),
            shrink_pct=round(_shrink_pct(before, after), 4),
            request_id=request_id,
        )
        text = after
    return text


def run_pipeline_sync(
    stages: list[MutationStage],
    text: str,
    ctx: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> str:
    """Sync façade for callsites that don't have an event loop available.

    Uses ``asyncio.run`` so a test or a CLI helper can drive the pipeline
    without restructuring. Production callsites already inside an async
    handler should call ``run_pipeline`` directly.
    """
    return asyncio.run(run_pipeline(stages, text, ctx, request_id=request_id))
