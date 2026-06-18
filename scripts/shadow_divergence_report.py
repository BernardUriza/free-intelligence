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

Reuses the Log Analytics REST path from ``scripts/kql.sh`` (workspace
``a07bf4c8-...``, table ``ContainerAppConsoleLogs_CL``) — no new infra.

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
    _print_llm_section(fetch_llm_rows(args.hours), args.channel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
