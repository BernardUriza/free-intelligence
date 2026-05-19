"""High-level Mem0-style consolidator orchestrator.

Wraps the three primitives that already exist:

1. :class:`fi_core.memory.MemoryStore` — provides the live facts and
   applies the resulting plan.
2. ``fi_core.persona.mcp_server.build_consolidation_prompt`` — produces
   the judge prompt + user_text + suggested model.
3. ``fi_core.persona.mcp_server.parse_consolidation_result`` — parses +
   validates the raw LLM response into a plan.

fi-core does NOT execute the LLM call itself. The consumer
(discord-bot's consolidator runner, AURITY's curator, anyone else)
supplies a ``llm_call`` callable that takes ``(system_prompt, user_text,
max_tokens)`` and returns the raw LLM text. The consolidator owns the
glue: facts → prompt → caller's LLM → parse → store.apply.

This is Shape B per ``memory:[[mcp-shape-b-canonical]]``: server builds
prompt + parser, caller executes LLM. Same pattern discord-bot already
uses post-v3.9.82.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import TYPE_CHECKING

from fi_core.memory.types import ConsolidationOp, ConsolidationReport, Fact

if TYPE_CHECKING:
    from fi_core.memory.protocols import MemoryStore


# Type alias for the caller-supplied LLM call.
# Returns the raw response text (or empty string on failure — the
# consolidator treats empty-after-parse as judge_failed).
LLMCall = Callable[[str, str, int], Awaitable[str]]


# Minimum number of live facts before a consolidation pass is worth
# the LLM round-trip. Matches discord-bot's threshold (below this,
# the judge has too little to merge / dedupe).
DEFAULT_MIN_FACTS = 3


# Default max output tokens for the judge call. Matches discord-bot's
# JUDGE_MAX_OUTPUT_TOKENS — empirically validated as enough headroom
# for ~300 facts/principal before truncation.
DEFAULT_JUDGE_MAX_TOKENS = 8192


class FactConsolidator:
    """Orchestrate one Mem0-style consolidation pass over a principal's facts.

    Usage::

        consolidator = FactConsolidator(store=my_pg_store, llm_call=my_judge)
        report = await consolidator.consolidate_principal("user-42")
        print(report.counts_by_op())

    The consolidator is stateless — instantiate once, reuse across runs
    and principals.
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        llm_call: LLMCall,
        min_facts: int = DEFAULT_MIN_FACTS,
        max_tokens: int = DEFAULT_JUDGE_MAX_TOKENS,
    ) -> None:
        self._store = store
        self._llm_call = llm_call
        self._min_facts = min_facts
        self._max_tokens = max_tokens

    async def consolidate_principal(
        self,
        principal_id: str,
        *,
        dry_run: bool = False,
    ) -> ConsolidationReport:
        """Run one consolidation pass for ``principal_id``.

        Steps:
            1. Load live facts. Skip if below ``min_facts``.
            2. Build the judge prompt via ``build_consolidation_prompt``.
            3. Call the consumer-supplied ``llm_call``.
            4. Parse the response via ``parse_consolidation_result``.
            5. If ``dry_run``: synthesize ops from the plan WITHOUT
               touching the store. Else: ``apply_consolidation_plan``.
            6. Return a :class:`ConsolidationReport` rollup.

        Errors at any stage are captured in ``report.error``; the
        report is always returned (never raises) so the caller can
        log / retry / move on.
        """
        # Imported lazily — fi_core.persona.mcp_server requires the [mcp]
        # extra. The consolidator can still be imported by consumers who
        # do not have it (Protocol satisfaction only, no use).
        from fi_core.persona.mcp_server import (
            build_consolidation_prompt,
            parse_consolidation_result,
        )

        started = time.monotonic()
        run_ts = time.time()
        live_facts = await self._store.get_facts(principal_id)

        report = ConsolidationReport(
            principal_id=principal_id,
            facts_in=len(live_facts),
            facts_out=len(live_facts),
        )

        if len(live_facts) < self._min_facts:
            report.duration_ms = int((time.monotonic() - started) * 1000)
            return report

        # Step 2: build the prompt. mcp_server.build_consolidation_prompt
        # expects facts as list of dicts with keys id / fact / category /
        # updated_at — we serialize Fact dataclasses to that shape.
        fact_dicts = [
            {
                "id": f.id,
                "fact": f.fact,
                "category": f.category,
                "updated_at": f.updated_at,
            }
            for f in live_facts
            if f.id is not None
        ]
        prompt_spec = await build_consolidation_prompt(
            facts=fact_dicts,
            max_tokens_hint=self._max_tokens,
        )

        # Step 3: caller executes the LLM call.
        try:
            raw_response = await self._llm_call(
                prompt_spec["system_prompt"],
                prompt_spec["user_text"],
                prompt_spec["max_tokens"],
            )
        except Exception as e:  # noqa: BLE001 - protocol-level isolation
            report.error = f"llm_call_failed: {e}"
            report.duration_ms = int((time.monotonic() - started) * 1000)
            return report

        # Step 4: parse + validate.
        parsed = await parse_consolidation_result(
            raw_response=raw_response,
            facts=fact_dicts,
        )
        if not parsed["ok"]:
            report.error = f"parse_failed: {parsed.get('error', 'unknown')}"
            report.duration_ms = int((time.monotonic() - started) * 1000)
            return report

        plan = parsed["ops"]

        # Step 5: apply or dry-run.
        if dry_run:
            report.ops = _synthesize_dry_run_ops(plan, live_facts, run_ts)
        else:
            report.ops = await self._store.apply_consolidation_plan(
                principal_id,
                plan,
                run_ts=run_ts,
            )

        # Recompute facts_out: NOOPs preserve facts; UPDATEs merge N→1;
        # DELETEs drop. Easy way is to ask the store again post-apply
        # (skipped in dry_run since DB wasn't touched).
        if not dry_run:
            report.facts_out = await self._store.count_live(principal_id)
        else:
            # Compute counterfactual: dry-run output = NOOPs + 1 row per UPDATE
            report.facts_out = sum(
                1 for op in plan if op["op"] == "NOOP"
            ) + sum(1 for op in plan if op["op"] == "UPDATE")

        report.duration_ms = int((time.monotonic() - started) * 1000)
        return report


def _synthesize_dry_run_ops(
    plan: list[dict],
    live_facts: list[Fact],
    run_ts: float,
) -> list[ConsolidationOp]:
    """Build :class:`ConsolidationOp` audit rows from a plan WITHOUT touching DB.

    Used by ``dry_run=True`` consolidation passes — useful for offline
    eval ("what would this judge do?") and for surfacing a plan diff
    in CLI dashboards before committing.
    """
    by_id = {f.id: f for f in live_facts if f.id is not None}
    ops: list[ConsolidationOp] = []
    for op in plan:
        kind = op["op"]
        reason = (op.get("reason") or "")[:500]
        if kind == "NOOP":
            fid = op["id"]
            ops.append(
                ConsolidationOp(
                    op="NOOP",
                    fact_id_before=fid,
                    fact_id_after=fid,
                    fact_text_before=by_id[fid].fact if fid in by_id else None,
                    fact_text_after=by_id[fid].fact if fid in by_id else None,
                    reason=reason,
                    run_ts=run_ts,
                )
            )
        elif kind == "DELETE":
            fid = op["id"]
            ops.append(
                ConsolidationOp(
                    op="DELETE",
                    fact_id_before=fid,
                    fact_id_after=None,
                    fact_text_before=by_id[fid].fact if fid in by_id else None,
                    fact_text_after=None,
                    reason=reason,
                    run_ts=run_ts,
                )
            )
        elif kind == "UPDATE":
            for fid in op["merge_ids"]:
                ops.append(
                    ConsolidationOp(
                        op="UPDATE",
                        fact_id_before=fid,
                        fact_id_after=None,  # No real id in dry-run
                        fact_text_before=by_id[fid].fact if fid in by_id else None,
                        fact_text_after=op["new_fact"],
                        reason=reason,
                        run_ts=run_ts,
                    )
                )
    return ops


# Re-export so consumers can import everything from one place.
__all__ = [
    "ConsolidationOp",
    "ConsolidationReport",
    "FactConsolidator",
    "LLMCall",
]


# Silence unused-import warnings for re-exports
_ = (asdict,)
