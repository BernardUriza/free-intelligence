#!/usr/bin/env python3
"""Performance baseline — fi_runner's own per-turn overhead, in isolation.

The hardening on deck (input validation, error boundaries around
`guard.inspect()`, backend try/catch) touches the LOCAL path, not provider API
latency. So this measures fi_runner's overhead with a zero-latency fake backend,
which is exactly the surface the hardening changes:

  - Runner.run() orchestration only (no guards)        -> framework floor
  - Runner.run() with the two guards                    -> delta = guard cost/turn
  - guard.inspect() standalone (triage, antidrift)      -> per-guard cost
  - run_pipeline() with one stage                        -> post-processor cost

Run it before the hardening, commit the JSON, then `--compare` after. A double-
digit % jump in the with-guards path means a try/catch (or validation) added
real overhead per turn.

    python3 benchmarks/perf_baseline.py            # print + save baseline
    python3 benchmarks/perf_baseline.py --compare  # diff vs saved baseline
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Run as a plain script: put the package root on the path so `import fi_runner`
# resolves without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa: E402

import fi_runner  # noqa: E402
from fi_runner import Runner, TurnResult, antidrift_guard, triage_guard  # noqa: E402

_BASELINE = Path(__file__).parent / "baselines" / "perf_baseline.json"
_ITERS = 3000
_WARMUP = 200


@dataclass
class _FakeBackend:
    """Zero-latency backend: isolates fi_runner overhead from provider latency."""

    text: str = "Órale, claro que te ayudo con eso, aquí va la respuesta."

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text=self.text)


def _stats(samples_ms: list[float]) -> dict[str, float]:
    s = sorted(samples_ms)
    n = len(s)

    def pct(p: float) -> float:
        k = max(0, min(n - 1, round((p / 100) * (n - 1))))
        return s[k]

    return {
        "n": n,
        "mean_ms": round(sum(s) / n, 5),
        "p50_ms": round(pct(50), 5),
        "p95_ms": round(pct(95), 5),
        "p99_ms": round(pct(99), 5),
        "max_ms": round(s[-1], 5),
    }


def _bench_sync(fn, iters: int = _ITERS, warmup: int = _WARMUP) -> dict[str, float]:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return _stats(samples)


async def _bench_async(coro_fn, iters: int = _ITERS, warmup: int = _WARMUP) -> dict[str, float]:
    for _ in range(warmup):
        await coro_fn()
    samples = []
    for _ in range(iters):
        t0 = time.perf_counter()
        await coro_fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return _stats(samples)


def _make_guards() -> list:
    p = fi_runner.packs
    return [
        triage_guard("psychiatry"),
        antidrift_guard(
            break_patterns=list(p.ALL_AI_DISCLOSURE),
            soft_patterns=list(p.ALL_ASSISTANT_TONE),
            clarification_patterns=list(p.CLARIFICATION_DUMP_ES),
            reinforcement="STAY IN CHARACTER",
        ),
    ]


async def collect_async() -> dict:
    backend = _FakeBackend()
    runner_bare = Runner(backend=backend, persona="p")
    runner_guarded = Runner(backend=backend, persona="p", guards=_make_guards())

    bare = await _bench_async(lambda: runner_bare.run("hola doc"))
    guarded = await _bench_async(lambda: runner_guarded.run("hola doc, me siento muy mal"))

    triage, antidrift = _make_guards()
    text = "el paciente reporta ánimo estable y niega ideación suicida"
    triage_only = _bench_sync(lambda: triage.inspect(response_text=text))
    antidrift_only = _bench_sync(
        lambda: antidrift.inspect(response_text="As an AI, I cannot. Pero órale, va.")
    )

    from fi_runner import MutationStage, run_pipeline

    stage = MutationStage(name="strip", apply=lambda t, ctx: t.strip(), max_shrink_pct=None)
    pipe = await _bench_async(lambda: run_pipeline([stage], "  hola mundo  ", {}))

    guard_overhead = round(guarded["mean_ms"] - bare["mean_ms"], 5)
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "fi_runner_version": fi_runner.__version__,
        "git_sha": _git_sha(),
        "iters": _ITERS,
        "results": {
            "runner_bare": bare,
            "runner_guarded": guarded,
            "guard_overhead_mean_ms": guard_overhead,
            "triage_inspect": triage_only,
            "antidrift_inspect": antidrift_only,
            "pipeline_one_stage": pipe,
        },
    }


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent, text=True
        ).strip()
    except Exception:  # noqa: BLE001 - sha is best-effort metadata
        return "unknown"


def print_report(data: dict) -> None:
    r = data["results"]
    print("=" * 72)
    print(f"PERF BASELINE  ·  fi_runner {data['fi_runner_version']}  ·  {data['git_sha']}  ·  {data['iters']} iters")
    print("=" * 72)
    rows = [
        ("Runner.run() bare", r["runner_bare"]),
        ("Runner.run() + 2 guards", r["runner_guarded"]),
        ("triage.inspect()", r["triage_inspect"]),
        ("antidrift.inspect()", r["antidrift_inspect"]),
        ("run_pipeline() 1 stage", r["pipeline_one_stage"]),
    ]
    print(f"\n  {'op':28s} {'mean':>10s} {'p50':>10s} {'p95':>10s} {'p99':>10s}")
    for name, s in rows:
        print(f"  {name:28s} {s['mean_ms']:>9.4f}m {s['p50_ms']:>9.4f}m {s['p95_ms']:>9.4f}m {s['p99_ms']:>9.4f}m")
    print(f"\n  guard overhead per turn (mean): {r['guard_overhead_mean_ms']:+.4f} ms")
    print()


def save(data: dict) -> None:
    _BASELINE.parent.mkdir(parents=True, exist_ok=True)
    _BASELINE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"baseline saved -> {_BASELINE}")


def compare(current: dict) -> None:
    if not _BASELINE.exists():
        print("no saved baseline to compare against; run without --compare first.")
        return
    base = json.loads(_BASELINE.read_text())
    print(f"\nCOMPARE  (baseline {base['git_sha']} -> current {current['git_sha']})")
    for key in ("runner_bare", "runner_guarded", "triage_inspect", "antidrift_inspect", "pipeline_one_stage"):
        b = base["results"][key]["mean_ms"]
        c = current["results"][key]["mean_ms"]
        pct = ((c - b) / b * 100) if b else 0.0
        flag = "  <-- REGRESSION >10%" if pct > 10 else ""
        print(f"    {key:24s} {b:.4f}ms -> {c:.4f}ms  ({pct:+.1f}%){flag}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compare", action="store_true", help="diff against the saved baseline")
    ap.add_argument("--no-save", action="store_true", help="print only, don't write the baseline")
    args = ap.parse_args()

    data = asyncio.run(collect_async())
    print_report(data)
    if args.compare:
        compare(data)
    elif not args.no_save:
        save(data)


if __name__ == "__main__":
    main()
