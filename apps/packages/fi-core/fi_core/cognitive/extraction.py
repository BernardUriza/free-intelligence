"""Extraction iteration workflow — the data-gathering sub-machine.

Ported faithfully from FLOW.md §2 ("Extraction Iteration Workflow") and §8
decision point #1 ("Continue Extraction?") of the Redux-Claude medical flow.
Pure, zero-dep, and **explainable**: given the completeness of the structured
data extracted so far and the current iteration, it decides whether another
extraction pass is warranted and, if so, what to focus on next.

This is the control loop that drives the ``EXTRACTING ⇄ WIP_UPDATE`` cycle of
the consultation state machine (see :mod:`fi_core.cognitive.state_machine`):
iterate until completeness clears the threshold or the iteration cap is hit.

This is decision SUPPORT, not diagnosis — it governs *how much information to
gather*, never the clinical interpretation of that information.

    loop = ExtractionLoop()
    decision = loop.advance(completeness=35, missing_critical_fields=["age"])
    while decision.should_continue:
        print(loop.iteration, decision.focus_areas, decision.reason)
        # ... run the extractor for decision.focus_areas, recompute completeness
        decision = loop.advance(completeness=..., missing_critical_fields=[...])
    print("done:", decision.reason)
"""

from __future__ import annotations

from dataclasses import dataclass

#: Completeness percentage (0-100) at or above which extraction stops
#: (FLOW.md §2 / §8 decision point #1: ``completeness >= 80``).
COMPLETENESS_THRESHOLD = 80

#: Hard cap on extraction passes; reaching it forces a stop regardless of
#: completeness (FLOW.md §2 / §8: ``iteration >= 5``).
MAX_ITERATIONS = 5

#: Per-iteration focus strategy (FLOW.md §2 "Iteration Focus Strategy" table).
#: Maps a 1-based iteration number to the field(s) that pass should target.
FOCUS_STRATEGY: dict[int, list[str]] = {
    1: ["age", "gender", "weight", "height"],              # Demographics
    2: ["primary_symptoms", "duration", "severity"],       # Chief Complaint
    3: ["past_medical_history", "medications", "allergies"],  # Medical History
    4: ["associated_symptoms", "red_flags"],               # Systems Review
    5: ["occupation", "lifestyle", "psychosocial_factors"],  # Contextual Data
}

#: Human-readable label for each iteration's focus area (FLOW.md §2 table).
FOCUS_LABELS: dict[int, str] = {
    1: "Demographics",
    2: "Chief Complaint",
    3: "Medical History",
    4: "Systems Review",
    5: "Contextual Data",
}


def focus_for_iteration(n: int) -> str | list[str]:
    """The focus field(s) the ``n``-th extraction pass should target.

    Returns the list of target fields for iteration ``n`` (1-based) per the
    FLOW.md §2 strategy table. Iterations beyond the table (or below 1) have
    no prescribed focus, so an explanatory string is returned instead.
    """
    fields = FOCUS_STRATEGY.get(n)
    if fields is None:
        return f"no prescribed focus for iteration {n}"
    return list(fields)


@dataclass(frozen=True)
class IterationDecision:
    """The outcome of a single ``decideNextIteration`` evaluation (FLOW.md §2).

    :attr:`focus_areas` is what to extract next when continuing (the missing
    critical fields); it is empty when stopping.
    """

    should_continue: bool
    reason: str
    focus_areas: tuple[str, ...] = ()


def decide_next_iteration(
    completeness: float,
    iteration: int,
    missing_critical_fields: tuple[str, ...] | list[str] = (),
) -> IterationDecision:
    """Decide whether to run another extraction pass (FLOW.md §2 + §8 #1).

    Faithful to the ``decideNextIteration`` pseudocode:

    * stop if ``completeness >= COMPLETENESS_THRESHOLD`` (sufficient data),
    * else stop if ``iteration >= MAX_ITERATIONS`` (cap reached),
    * else continue, focusing on ``missing_critical_fields``.

    ``completeness`` is a 0-100 percentage; ``iteration`` is the number of
    passes already completed.
    """
    if completeness >= COMPLETENESS_THRESHOLD:
        return IterationDecision(
            should_continue=False,
            reason="Sufficient completeness achieved",
            focus_areas=(),
        )

    if iteration >= MAX_ITERATIONS:
        return IterationDecision(
            should_continue=False,
            reason="Max iterations reached",
            focus_areas=(),
        )

    missing = tuple(missing_critical_fields)
    return IterationDecision(
        should_continue=True,
        reason=f"Completeness {completeness}%, missing critical fields",
        focus_areas=missing,
    )


@dataclass
class ExtractionLoop:
    """A live extraction loop tracking iteration count and completeness.

    Drives the ``EXTRACTING ⇄ WIP_UPDATE`` cycle: each :meth:`advance` records
    one completed pass and returns the :class:`IterationDecision` for whether
    to keep going. Starts at iteration 0 with 0% completeness.
    """

    iteration: int = 0
    completeness: float = 0.0

    def advance(
        self,
        completeness: float,
        missing_critical_fields: tuple[str, ...] | list[str] = (),
    ) -> IterationDecision:
        """Record a completed extraction pass and decide what comes next.

        Increments :attr:`iteration`, stores the latest ``completeness``, then
        returns :func:`decide_next_iteration` for the new state.
        """
        self.iteration += 1
        self.completeness = completeness
        return decide_next_iteration(
            completeness=completeness,
            iteration=self.iteration,
            missing_critical_fields=missing_critical_fields,
        )

    def is_complete(self) -> bool:
        """Whether extraction should stop (threshold met or cap reached)."""
        return (
            self.completeness >= COMPLETENESS_THRESHOLD
            or self.iteration >= MAX_ITERATIONS
        )

    def reset(self) -> None:
        """Return to the initial state (iteration 0, 0% completeness)."""
        self.iteration = 0
        self.completeness = 0.0
