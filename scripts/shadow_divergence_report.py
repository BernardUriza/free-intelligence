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


def build_query(hours: int) -> str:
    """KQL for the shadow_router_decision events over the last ``hours``."""
    return f"""ContainerAppConsoleLogs_CL
| where TimeGenerated > ago({int(hours)}h)
| extend p = parse_json(Log_s)
| where tostring(p.event) == "shadow_router_decision"
| project TimeGenerated,
          current=tostring(p.current_target),
          shadow=tostring(p.shadow_target),
          reason=tostring(p.shadow_reason),
          diverged=tostring(p.diverged)
| order by TimeGenerated asc"""


def _access_token() -> str:
    out = subprocess.run(
        ["az", "account", "get-access-token", "--resource",
         "https://api.loganalytics.io", "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def fetch_rows(hours: int) -> list[dict]:
    """Run the KQL and return rows as dicts. Raises on auth/query failure."""
    body = json.dumps({"query": build_query(hours)}).encode()
    req = urllib.request.Request(
        _LOGANALYTICS,
        data=body,
        headers={"Authorization": f"Bearer {_access_token()}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    tables = data.get("tables") or []
    if not tables:
        return []
    cols = [c["name"] for c in tables[0]["columns"]]
    return [dict(zip(cols, row, strict=False)) for row in tables[0]["rows"]]


def summarize(rows: list[dict]) -> Counter:
    counts: Counter = Counter()
    for r in rows:
        counts[classify_decision(
            shadow_reason=r.get("reason", ""),
            diverged=r.get("diverged", "false"),
        )] += 1
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Shadow-router divergence report")
    ap.add_argument("--hours", type=int, default=48, help="lookback window (default 48h)")
    args = ap.parse_args(argv)

    rows = fetch_rows(args.hours)
    total = len(rows)
    counts = summarize(rows)

    print(f"shadow_router_decision events (last {args.hours}h): {total}")
    if total == 0:
        print("  (no shadow traffic yet — let real #general turns accumulate)")
        return 0

    for bucket in (BUCKET_DIVERGED, BUCKET_AGREE_VULTUR, BUCKET_AGREE_INSULT, BUCKET_AGREE_OTHER):
        n = counts.get(bucket, 0)
        if n:
            print(f"  {bucket:24s} {n:5d}  ({100 * n / total:.1f}%)")

    diverged = [r for r in rows if _as_bool(r.get("diverged", "false"))]
    if diverged:
        print(f"\n⚠️  {len(diverged)} DIVERGED row(s) — live routing disagreed with the deterministic rule (review):")
        for r in diverged:
            print(f"  {r.get('TimeGenerated','')}  current={r.get('current')}  shadow={r.get('shadow')}  reason={r.get('reason')}")
    else:
        print("\n  0 divergences — live routing matches the deterministic rule (expected for slice A).")

    print(
        "\nNOTE: the deterministic shadow mirrors the live @vultur rule, so ~all rows agree. "
        "The intent taxonomy (missing-vultur / false-vultur / ambiguous) needs the gpt-4.1 "
        "shadow classifier (slice 4, spend-gated) — not derivable from this data alone."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
