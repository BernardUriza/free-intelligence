#!/usr/bin/env python3
"""Shadow-router divergence report — the measurement gate before HOST 5/6 slice B.

HOST 5/6 slice A wired a DETERMINISTIC shadow router that logs
``shadow_router_decision {current_target, shadow_target, shadow_reason, diverged}``
on every turn without changing routing. The coagent's gate for slice B is
"collect real shadow traffic, then classify divergences" — this script is that
classifier.

HONEST SCOPE (Art. 2/3 — no fake-green): the slice-A shadow is deterministic and
MIRRORS the live ``@vultur``/``~vultur`` rule by construction, so it agrees with
production almost always. What this report CAN prove from shadow data alone:

- volume of shadow decisions (is the shadow actually emitting?),
- the agree/diverge split — a ``diverged=true`` row means the LIVE routing
  disagreed with the deterministic rule, i.e. a REAL routing-gap / bug to review,
- the reason distribution (default_insult vs vultur_prefix).

What it CANNOT produce yet: the rich intent taxonomy the coagent named
(missing-vultur / false-vultur / ambiguous). Those require a SECOND opinion —
the gpt-4.1 intent classifier running in shadow (slice 4, spend-gated) or human
labeling. This report flags that gap instead of faking those buckets.

On top of the divergence taxonomy, the report renders the HOST 5/6 slice-B
CUTOVER READINESS verdict (the coagent's flip gate, 2026-06-21): token avg/p95
vs the direct-transport target, weekly spend vs the $5 cap, the router failure
modes (router_error / timeout / unparseable), and a GREEN_PENDING_MANUAL / WAIT /
RED verdict. The two criteria a report cannot exercise (kill switch, deterministic
fallback) stay MANUAL — the verdict never reads green on a thing it never ran.

Reuses the Log Analytics REST path from ``scripts/kql.sh`` (workspace
``a07bf4c8-...``, table ``ContainerAppConsoleLogs_CL``) and the live price model
from ``demux_ai.router_budget`` — no new infra, no parallel price table.

Usage:
    python scripts/shadow_divergence_report.py [--hours 48]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from collections import Counter
from pathlib import Path

# Run-from-anywhere: a `python scripts/shadow_divergence_report.py` invocation puts
# scripts/ (not the repo root) on sys.path[0], so `demux_ai` — the live price model
# reused by estimate_window_spend_usd — would not import. pytest adds the root via
# rootdir, hiding this; the live run is what surfaced it. Make the script self-locating.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

WORKSPACE = "a07bf4c8-22ff-455a-b7bd-91055da53b28"
_LOGANALYTICS = f"https://api.loganalytics.io/v1/workspaces/{WORKSPACE}/query"

# #general — the record-grade verification surface (see .claude/rules/testing.md).
# slice A.1 splits shadow traffic by channel because a DM turn is a WEAK sanity
# check, NOT #general evidence: counting DM rows as #general would fake the gate.
GENERAL_CHANNEL_ID = "1489180895264116736"

# Buckets derivable from the DETERMINISTIC shadow alone. The LLM-intent taxonomy
# is intentionally absent — see module docstring.
BUCKET_DIVERGED = "diverged_review"
BUCKET_AGREE_VULTUR = "agree_vultur_explicit"
BUCKET_AGREE_INSULT = "agree_default_insult"
BUCKET_AGREE_OTHER = "agree_other"


def _as_bool(value: object) -> bool:
    """Coerce a logged ``diverged`` field (bool, or "true"/"false" string) to bool."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def classify_decision(*, shadow_reason: str, diverged: object) -> str:
    """Bucket one ``shadow_router_decision`` row — pure, no I/O.

    ``diverged`` already encodes ``shadow_target != current_target`` (computed at
    the emit site), so the targets themselves are not needed here. A divergence
    (live routing != deterministic rule) always wins the classification: it is
    the only row that needs human review, so it must never be hidden behind an
    "agree" bucket even if the reason looks benign.
    """
    if _as_bool(diverged):
        return BUCKET_DIVERGED
    if shadow_reason == "vultur_prefix":
        return BUCKET_AGREE_VULTUR
    if shadow_reason == "default_insult":
        return BUCKET_AGREE_INSULT
    return BUCKET_AGREE_OTHER


# slice A.2 — the GENUINE-divergence taxonomy. The gpt-4.1 host brain decides a
# target INDEPENDENTLY of the live prefix rule, so (unlike the deterministic
# shadow) its decision CAN disagree with where the turn went — and that
# disagreement finally yields the intent buckets the coagent named.
LLM_BUCKET_AGREE = "llm_agree"
LLM_BUCKET_MISSING_VULTUR = "llm_missing_vultur"  # live=insult, brain=vultur
LLM_BUCKET_FALSE_VULTUR = "llm_false_vultur"  # live=vultur, brain=insult
LLM_BUCKET_OTHER_DIVERGENCE = "llm_other_divergence"


def classify_llm_decision(*, current_target: str, llm_shadow_target: str, llm_diverged: object) -> str:
    """Bucket one ``llm_shadow_router_decision`` row — pure, no I/O.

    Agreement (the brain matched the live route) is benign. A genuine divergence
    is split by direction into the intent taxonomy the deterministic shadow could
    never produce: ``missing_vultur`` (live kept it on Insult, the brain would
    have handed it to the film specialist) and ``false_vultur`` (the explicit
    ``~vultur`` prefix forced Vultur, the brain judged Insult enough). Any other
    diverged pair is surfaced rather than hidden."""
    if not _as_bool(llm_diverged):
        return LLM_BUCKET_AGREE
    if current_target == "insult" and llm_shadow_target == "vultur":
        return LLM_BUCKET_MISSING_VULTUR
    if current_target == "vultur" and llm_shadow_target == "insult":
        return LLM_BUCKET_FALSE_VULTUR
    return LLM_BUCKET_OTHER_DIVERGENCE


# --- HOST 5/6 readiness gate: parse quality, tokens, spend, failure modes -------
# The coagent's slice-B flip criteria (2026-06-21) need more than the divergence
# taxonomy above: avg/p95 tokens, weekly spend vs the $5 cap, and the router's
# failure modes (router_error / timeout / unparseable). This section aggregates
# those and renders an explicit readiness VERDICT — auto-checkable criteria only.
# The two the report CANNOT exercise (kill switch, deterministic fallback) stay
# MANUAL so the verdict never reads GREEN on a thing it never ran (Art. 2).

MIN_GENERAL_SAMPLES = 50  # coagent: ">=50 direct decisions OR several days of traffic"

PARSE_CLEAN = "parse_clean"
PARSE_LOOSE = "parse_loose"
PARSE_UNPARSEABLE = "parse_unparseable"


def classify_parse_quality(llm_shadow_reason: str) -> str:
    """Bucket a gpt-4.1 decision by PARSE quality from its reason token — pure.

    ``llm_unparseable`` (model gave nothing recognizable → defaulted to Insult) is
    the failure mode that matters for the gate; ``llm_<t>_loose`` (target dug out
    of prose) is a soft signal of a chatty model; a clean ``llm_<t>`` is healthy."""
    if llm_shadow_reason == "llm_unparseable":
        return PARSE_UNPARSEABLE
    if llm_shadow_reason.endswith("_loose"):
        return PARSE_LOOSE
    return PARSE_CLEAN


def _int(value: object) -> int:
    """Coerce a KQL-stringified integer field to int (0 on junk/empty)."""
    try:
        return int(str(value).strip() or 0)
    except (ValueError, TypeError):
        return 0


def percentile(values: list[int], p: float) -> float:
    """Linear-interpolated p-th percentile of ``values`` (0.0 for empty) — pure.

    The p95-input-tokens figure the direct-transport fix (115 vs 9.5k) is measured
    against, so a token-bloat regression shows up as a moved p95, not a hidden tail."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def estimate_window_spend_usd(llm_rows: list[dict]) -> float:
    """USD cost of the LLM-shadow calls in the window, priced with the SAME model
    the live ``RouterBudget`` uses (Art. 6 — no parallel price table). A cross-check
    against the bot's own cumulative ``week_spent_usd`` counter, not a replacement
    for it (the counter is ground truth; this catches a counter that drifted)."""
    from demux_ai.router_budget import RouterBudget

    budget = RouterBudget()
    return sum(budget.cost_usd(_int(r.get("llm_input_tokens")), _int(r.get("llm_output_tokens"))) for r in llm_rows)


def count_router_errors(ops_rows: list[dict]) -> int:
    """Hard ``llm_shadow_router_failed`` events — the router-error rate the gate
    requires at 0 (a recurrent failure means the host brain can't be trusted to
    route)."""
    return sum(1 for r in ops_rows if r.get("event") == "llm_shadow_router_failed")


def count_timeouts(ops_rows: list[dict]) -> int:
    """Subset of router failures whose rendered exception names a timeout. Honest
    floor: if structlog did not carry the exception text, a timeout cannot be told
    from any other failure and is counted only under ``router_error``."""
    return sum(
        1
        for r in ops_rows
        if r.get("event") == "llm_shadow_router_failed" and "timeout" in str(r.get("exc") or "").lower()
    )


def observed_week_spend(ops_rows: list[dict], cap_default: float) -> tuple[float, float]:
    """Ground-truth weekly spend from the bot's own ``llm_router_spend`` counter:
    the MAX ``week_spent_usd`` seen in the window (the counter is cumulative per
    ISO week, resets on restart). Returns ``(spend, cap)`` — cap from the logged
    ``cap_usd`` when present, else ``cap_default``."""
    spends = [
        float(r["week_spent_usd"]) for r in ops_rows if r.get("event") == "llm_router_spend" and r.get("week_spent_usd")
    ]
    caps = [float(r["cap_usd"]) for r in ops_rows if r.get("cap_usd")]
    return (max(spends) if spends else 0.0, max(caps) if caps else cap_default)


def readiness_verdict(
    *,
    general_llm_count: int,
    false_vultur: int,
    missing_vultur: int,
    router_error: int,
    timeout: int,
    parse_unparseable: int,
    observed_week_spend_usd: float,
    cap_usd: float,
    min_samples: int = MIN_GENERAL_SAMPLES,
) -> dict:
    """Score the slice-B flip criteria the coagent named (2026-06-21) — pure.

    Auto-checkable criteria become PASS/WAIT/FAIL/REVIEW; the two the report cannot
    exercise (kill switch, deterministic fallback) stay MANUAL so the verdict can
    never read fully green without a human proving them. ``overall`` is
    ``GREEN_PENDING_MANUAL`` only when no criterion FAILs and the sample is large
    enough — never an unqualified GREEN, because the manual proofs are real gates."""
    criteria = [
        {
            "name": "sample_size",
            "status": "PASS" if general_llm_count >= min_samples else "WAIT",
            "detail": f"{general_llm_count}/{min_samples} #general LLM-shadow decisions",
        },
        {
            "name": "false_vultur",
            "status": "PASS" if false_vultur == 0 else "REVIEW",
            "detail": f"{false_vultur} turn(s) the brain would have kept on Insult — prod-breaking if cut over",
        },
        {
            "name": "missing_vultur",
            "status": "REVIEW",
            "detail": f"{missing_vultur} 'should-be-Vultur' candidate(s) — correctness needs a human label",
        },
        {
            "name": "router_error",
            "status": "PASS" if router_error == 0 else "FAIL",
            "detail": f"{router_error} llm_shadow_router_failed event(s)",
        },
        {
            "name": "timeout",
            "status": "PASS" if timeout == 0 else "FAIL",
            "detail": f"{timeout} timeout-classed failure(s)",
        },
        {
            "name": "parse_unparseable",
            "status": "PASS" if parse_unparseable == 0 else "REVIEW",
            "detail": f"{parse_unparseable} unparseable model reply/replies (defaulted to Insult)",
        },
        {
            "name": "spend_within_budget",
            "status": "PASS" if observed_week_spend_usd < cap_usd else "FAIL",
            "detail": f"observed ${observed_week_spend_usd:.4f} / ${cap_usd:.2f} weekly cap",
        },
        {
            "name": "kill_switch_tested",
            "status": "MANUAL",
            "detail": "flip llm_shadow_router_enabled OFF → zero new decisions (verify out of band)",
        },
        {
            "name": "deterministic_fallback_tested",
            "status": "MANUAL",
            "detail": "router_error/parse/timeout must fall to the deterministic rule, never silence or fake-ALICE",
        },
    ]
    statuses = {c["status"] for c in criteria}
    if "FAIL" in statuses:
        overall = "RED"
    elif any(c["name"] == "sample_size" and c["status"] == "WAIT" for c in criteria):
        overall = "WAIT_MORE_SAMPLES"
    else:
        overall = "GREEN_PENDING_MANUAL"
    return {"overall": overall, "criteria": criteria}


def build_query(hours: int) -> str:
    """KQL for the shadow_router_decision events over the last ``hours``.

    Projects the slice-A.1 telemetry (channel/guild/explicit_vultur_trigger/
    route_input_len) on top of the slice-A routing fields so the report can
    filter #general for real and distinguish "no trigger" from "can't tell".
    ``channel_id``/``user_id`` arrive via structlog contextvars on every line.
    """
    return f"""ContainerAppConsoleLogs_CL
| where TimeGenerated > ago({int(hours)}h)
| extend p = parse_json(Log_s)
| where tostring(p.event) == "shadow_router_decision"
| project TimeGenerated,
          current=tostring(p.current_target),
          shadow=tostring(p.shadow_target),
          reason=tostring(p.shadow_reason),
          diverged=tostring(p.diverged),
          channel=tostring(p.channel_id),
          guild=tostring(p.guild_id),
          explicit_vultur_trigger=tostring(p.explicit_vultur_trigger),
          route_input_len=tostring(p.route_input_len)
| order by TimeGenerated asc"""


def build_llm_query(hours: int) -> str:
    """KQL for the gpt-4.1 ``llm_shadow_router_decision`` events (slice A.2) over the
    last ``hours``. Projects the host brain's independent target + divergence flag
    next to where the turn actually went, plus the channel partition and token
    counts for spend accounting."""
    return f"""ContainerAppConsoleLogs_CL
| where TimeGenerated > ago({int(hours)}h)
| extend p = parse_json(Log_s)
| where tostring(p.event) == "llm_shadow_router_decision"
| project TimeGenerated,
          current=tostring(p.current_target),
          llm_shadow_target=tostring(p.llm_shadow_target),
          llm_shadow_reason=tostring(p.llm_shadow_reason),
          llm_diverged=tostring(p.llm_diverged),
          channel=tostring(p.channel_id),
          guild=tostring(p.guild_id),
          route_input_len=tostring(p.route_input_len),
          llm_input_tokens=tostring(p.llm_input_tokens),
          llm_output_tokens=tostring(p.llm_output_tokens)
| order by TimeGenerated asc"""


def build_llm_ops_query(hours: int) -> str:
    """KQL for the LLM router's NON-decision ops events over the last ``hours``:
    hard failures (``llm_shadow_router_failed``), the per-call spend log
    (``llm_router_spend`` → the bot's own cumulative ``week_spent_usd``), budget
    cutoffs, and empty-input skips. Projects the rendered ``exception`` so timeout
    failures can be told apart from other router errors."""
    return f"""ContainerAppConsoleLogs_CL
| where TimeGenerated > ago({int(hours)}h)
| extend p = parse_json(Log_s)
| where tostring(p.event) in ("llm_shadow_router_failed", "llm_router_spend", "llm_router_budget_exceeded", "llm_shadow_router_skipped")
| project TimeGenerated,
          event=tostring(p.event),
          exc=tostring(p.exception),
          week_spent_usd=tostring(p.week_spent_usd),
          cap_usd=tostring(p.cap_usd),
          reason=tostring(p.reason),
          channel=tostring(p.channel_id)
| order by TimeGenerated asc"""


def partition_by_channel(rows: list[dict], channel_id: str) -> tuple[list[dict], list[dict]]:
    """Split rows into ``(in_channel, off_channel)`` by the ``channel`` field.

    The whole point of slice A.1: shadow traffic from the Insult DM is a WEAK
    sanity check, not #general evidence. Partitioning lets the report say
    "N in #general, M off-channel" instead of silently mixing a DM turn into
    the record-grade count.
    """
    in_channel = [r for r in rows if r.get("channel") == channel_id]
    off_channel = [r for r in rows if r.get("channel") != channel_id]
    return in_channel, off_channel


def _access_token() -> str:
    out = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://api.loganalytics.io",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _fetch(query: str) -> list[dict]:
    """Run a KQL query and return rows as dicts. Raises on auth/query failure."""
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        _LOGANALYTICS,
        data=body,
        headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    tables = data.get("tables") or []
    if not tables:
        return []
    cols = [c["name"] for c in tables[0]["columns"]]
    return [dict(zip(cols, row, strict=False)) for row in tables[0]["rows"]]


def fetch_rows(hours: int) -> list[dict]:
    """Deterministic ``shadow_router_decision`` rows over the last ``hours``."""
    return _fetch(build_query(hours))


def fetch_llm_rows(hours: int) -> list[dict]:
    """gpt-4.1 ``llm_shadow_router_decision`` rows over the last ``hours`` (slice A.2)."""
    return _fetch(build_llm_query(hours))


def fetch_llm_ops_rows(hours: int) -> list[dict]:
    """LLM-router ops events (failures/spend/budget/skip) over the last ``hours``."""
    return _fetch(build_llm_ops_query(hours))


def summarize(rows: list[dict]) -> Counter:
    counts: Counter = Counter()
    for r in rows:
        counts[
            classify_decision(
                shadow_reason=r.get("reason", ""),
                diverged=r.get("diverged", "false"),
            )
        ] += 1
    return counts


def summarize_llm(rows: list[dict]) -> Counter:
    counts: Counter = Counter()
    for r in rows:
        counts[
            classify_llm_decision(
                current_target=r.get("current", ""),
                llm_shadow_target=r.get("llm_shadow_target", ""),
                llm_diverged=r.get("llm_diverged", "false"),
            )
        ] += 1
    return counts


def _print_llm_section(rows: list[dict], channel_id: str) -> None:
    """Report the gpt-4.1 shadow (slice A.2) — the genuine-divergence taxonomy.

    Only #general rows are record-grade (same discipline as the deterministic
    section). Silent when there is no LLM-shadow traffic — the flag may be OFF
    (no spend) or simply no turns yet."""
    if not rows:
        print(
            "\n  gpt-4.1 LLM shadow (slice A.2): no llm_shadow_router_decision events "
            "(flag off = no spend, or no traffic yet)."
        )
        return
    in_channel, _off = partition_by_channel(rows, channel_id)
    print(f"\n  gpt-4.1 LLM shadow (slice A.2): {len(rows)} events, {len(in_channel)} in #general")
    if not in_channel:
        print("    NO #general LLM-shadow traffic yet — genuine-divergence taxonomy not yet measurable.")
        return
    total = len(in_channel)
    counts = summarize_llm(in_channel)
    for bucket in (
        LLM_BUCKET_MISSING_VULTUR,
        LLM_BUCKET_FALSE_VULTUR,
        LLM_BUCKET_OTHER_DIVERGENCE,
        LLM_BUCKET_AGREE,
    ):
        n = counts.get(bucket, 0)
        if n:
            print(f"    {bucket:24s} {n:5d}  ({100 * n / total:.1f}%)")
    diverged = [r for r in in_channel if _as_bool(r.get("llm_diverged", "false"))]
    if diverged:
        print(f"\n  ⚠️  {len(diverged)} GENUINE divergence(s) — host brain disagreed with live routing (review):")
        for r in diverged:
            print(
                f"    {r.get('TimeGenerated', '')}  live={r.get('current')}  brain={r.get('llm_shadow_target')}  reason={r.get('llm_shadow_reason')}"
            )
    else:
        print("    0 genuine divergences yet — the host brain agreed with live routing on every #general turn.")


def _print_readiness(llm_in_general: list[dict], ops_rows: list[dict], cap_default: float) -> None:
    """HOST 5/6 slice-B readiness verdict — the coagent's flip gate (2026-06-21).

    Aggregates parse quality + token p95 + spend + failure modes from the LLM
    shadow data and renders an explicit GREEN_PENDING_MANUAL / WAIT / RED verdict.
    #general rows drive the intent taxonomy (record-grade); ops events (failures,
    spend) are counted globally — a router failure or overspend anywhere is a
    router-health signal, not a per-channel one."""
    counts = summarize_llm(llm_in_general)
    false_vultur = counts.get(LLM_BUCKET_FALSE_VULTUR, 0)
    missing_vultur = counts.get(LLM_BUCKET_MISSING_VULTUR, 0)
    parse_counts = Counter(classify_parse_quality(r.get("llm_shadow_reason", "")) for r in llm_in_general)
    parse_unparseable = parse_counts.get(PARSE_UNPARSEABLE, 0)
    in_tokens = [_int(r.get("llm_input_tokens")) for r in llm_in_general if r.get("llm_input_tokens")]
    router_error = count_router_errors(ops_rows)
    timeout = count_timeouts(ops_rows)
    week_spend, cap = observed_week_spend(ops_rows, cap_default)
    window_spend = estimate_window_spend_usd(llm_in_general)

    print("\n" + "=" * 64)
    print("HOST 5/6 — implicit-router CUTOVER readiness (coagent gate 2026-06-21)")
    print("=" * 64)
    if in_tokens:
        print(
            f"  tokens/call (input): avg {sum(in_tokens) / len(in_tokens):.0f}  "
            f"p95 {percentile(in_tokens, 95):.0f}  max {max(in_tokens)}  "
            f"(direct transport target ~115; ~9.5k = agentic-bloat regression)"
        )
    print(f"  spend: bot counter max ${week_spend:.4f}/wk  |  window estimate ${window_spend:.4f}  |  cap ${cap:.2f}")
    print(
        f"  parse quality: clean {parse_counts.get(PARSE_CLEAN, 0)}  "
        f"loose {parse_counts.get(PARSE_LOOSE, 0)}  unparseable {parse_unparseable}"
    )

    verdict = readiness_verdict(
        general_llm_count=len(llm_in_general),
        false_vultur=false_vultur,
        missing_vultur=missing_vultur,
        router_error=router_error,
        timeout=timeout,
        parse_unparseable=parse_unparseable,
        observed_week_spend_usd=week_spend,
        cap_usd=cap,
    )
    print(f"\n  VERDICT: {verdict['overall']}")
    for c in verdict["criteria"]:
        print(f"    [{c['status']:6s}] {c['name']:30s} {c['detail']}")
    if verdict["overall"] == "WAIT_MORE_SAMPLES":
        print(
            "\n  → Let #general traffic accumulate (the gpt-4.1 shadow is spend-gated by "
            "llm_shadow_router_enabled). Re-run this report; the flip is Bernard's call once GREEN_PENDING_MANUAL."
        )
    elif verdict["overall"] == "GREEN_PENDING_MANUAL":
        print(
            "\n  → Auto-criteria green. Remaining = the two MANUAL proofs (kill switch + deterministic "
            "fallback) + a human label on the missing/false-Vultur samples. Then the flip is Bernard's call."
        )
    else:
        print("\n  → RED: a hard criterion failed (router_error/timeout/spend). Fix before measuring again.")


def _print_buckets(rows: list[dict]) -> None:
    total = len(rows)
    counts = summarize(rows)
    for bucket in (BUCKET_DIVERGED, BUCKET_AGREE_VULTUR, BUCKET_AGREE_INSULT, BUCKET_AGREE_OTHER):
        n = counts.get(bucket, 0)
        if n:
            print(f"    {bucket:24s} {n:5d}  ({100 * n / total:.1f}%)")
    triggers = sum(1 for r in rows if _as_bool(r.get("explicit_vultur_trigger", "false")))
    print(
        f"    explicit_vultur_trigger  {triggers:5d}  ({100 * triggers / total:.1f}% had a real @vultur/~vultur token)"
    )
    diverged = [r for r in rows if _as_bool(r.get("diverged", "false"))]
    if diverged:
        print(f"\n  ⚠️  {len(diverged)} DIVERGED row(s) — live routing disagreed with the deterministic rule (review):")
        for r in diverged:
            print(
                f"    {r.get('TimeGenerated', '')}  current={r.get('current')}  shadow={r.get('shadow')}  reason={r.get('reason')}"
            )
    else:
        print("\n  0 divergences — live routing matches the deterministic rule (expected for slice A).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Shadow-router divergence report")
    ap.add_argument("--hours", type=int, default=48, help="lookback window (default 48h)")
    ap.add_argument(
        "--channel",
        default=GENERAL_CHANNEL_ID,
        help="record-grade channel_id to filter (default: #general)",
    )
    args = ap.parse_args(argv)

    rows = fetch_rows(args.hours)
    total = len(rows)
    in_channel, off_channel = partition_by_channel(rows, args.channel)

    print(f"shadow_router_decision events (last {args.hours}h): {total} total")
    print(f"  in #general ({args.channel}): {len(in_channel)}")
    print(f"  off-channel (DM/other — WEAK sanity only): {len(off_channel)}")

    if total == 0:
        print("\n  (no deterministic shadow traffic at all yet — let real turns accumulate)")
    elif not in_channel:
        # The honest distinction the coagent asked for: traffic EXISTS but none
        # is record-grade. NOT the same as "no traffic" — do not fake the gate.
        print(
            "\n  NO #general shadow traffic yet — the gate is NOT satisfiable from "
            "off-channel rows. Need real #general turns (ideally some @vultur) before slice B."
        )
        off_channels = sorted({r.get("channel", "?") for r in off_channel})
        print(f"  off-channel ids seen: {', '.join(off_channels)}")
    else:
        print(f"\n  #general breakdown ({len(in_channel)} rows):")
        _print_buckets(in_channel)
        print(
            "\nNOTE: the deterministic shadow mirrors the live @vultur rule by construction, so "
            "~all rows agree — a diverged row here is a live-routing bug, not an intent gap. The "
            "intent taxonomy (missing-vultur / false-vultur) comes from the gpt-4.1 LLM shadow below."
        )

    # slice A.2 — the gpt-4.1 LLM shadow section (the genuine-divergence taxonomy).
    llm_rows = fetch_llm_rows(args.hours)
    _print_llm_section(llm_rows, args.channel)

    # HOST 5/6 slice-B readiness verdict — the coagent's flip gate.
    llm_in_general, _ = partition_by_channel(llm_rows, args.channel)
    _print_readiness(llm_in_general, fetch_llm_ops_rows(args.hours), cap_default=5.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
