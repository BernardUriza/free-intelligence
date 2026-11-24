"""Retrieval evaluation of a persona's corpus, through the code the turn runs.

    python scripts/corpus_eval.py --persona frugivoro                 # both splits, report
    python scripts/corpus_eval.py --persona frugivoro --check         # exit 1 if worse than the baseline
    python scripts/corpus_eval.py --persona frugivoro --save          # write the baseline
    python scripts/corpus_eval.py --persona frugivoro --rules x.yml   # try another policy

Needs POSTGRES_URL (read-only use). Cases and baselines live in `data/eval/corpus/`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
import zlib
from pathlib import Path

import structlog
import yaml
from fi_core.rag import EvalCase, Retrieved, gate, run_cases, summarize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_core.corpus import references  # noqa: E402
from persona_core.corpus.rules import load_rules  # noqa: E402
from shared.personas.registry import PERSONAS  # noqa: E402

EVAL_DIR = ROOT / "data" / "eval" / "corpus"


def load_cases(persona: str) -> list[EvalCase]:
    """The labelled cases of `persona`; the split comes from a hash of the id."""
    raw = yaml.safe_load((EVAL_DIR / f"{persona}.yml").read_text(encoding="utf-8"))
    cases = []
    for case in raw["answerable"] + raw["off_topic"]:
        gold = tuple(f"{persona}:{pattern}" for pattern in case.get("gold", ()))
        split = "holdout" if zlib.crc32(case["id"].encode()) % 2 else "dev"
        cases.append(EvalCase(case["id"], case["q"], gold, split, case.get("must_pass", False)))
    return cases


async def evaluate(persona: str, cases: list[EvalCase]):
    namespace = PERSONAS[persona].corpus_namespace
    seconds: list[float] = []

    async def retrieve(query: str) -> Retrieved:
        started = time.perf_counter()
        ranked = await references.rank_references(query, namespace=namespace)
        seconds.append(time.perf_counter() - started)
        if ranked is None:
            raise SystemExit("retrieval could not run: check POSTGRES_URL and the models")
        kept = references.above_floor(ranked)
        return Retrieved(
            shortlist=[h["source_ref"] for h in ranked],
            accepted=[h["source_ref"] for h in kept],
            top_score=round(ranked[0]["relevance"], 3) if ranked else None,
        )

    return await run_cases(cases, retrieve), seconds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--persona", required=True)
    parser.add_argument("--split", choices=("dev", "holdout", "all"), default="all")
    parser.add_argument("--rules", type=Path, help="a rules.yml to evaluate instead of the shipped one")
    parser.add_argument("--save", action="store_true", help="write this run as the baseline")
    parser.add_argument("--check", action="store_true", help="exit 1 if this run is worse than the baseline")
    parser.add_argument("--failures", action="store_true", help="list every failing case")
    args = parser.parse_args()
    if args.save and args.split != "all":
        parser.error("--save needs the whole set")
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))
    if args.rules:
        references.load_rules = lambda: load_rules(args.rules)

    cases = [c for c in load_cases(args.persona) if args.split in ("all", c.split)]
    results, seconds = asyncio.run(evaluate(args.persona, cases))
    by_split = {c.id: c.split for c in cases}
    for split in ("dev", "holdout"):
        subset = [r for r in results if by_split[r.id] == split]
        if subset:
            print(f"{split:8}", summarize(subset))
    print(f"{'all':8}", summarize(results))
    ordered = sorted(seconds[1:] or seconds)
    print(f"seconds  p50 {ordered[len(ordered) // 2]:.2f}  p95 {ordered[int(len(ordered) * 0.95)]:.2f}")
    if args.failures:
        for r in results:
            if not r.passed:
                where = f"rank {r.gold_rank}" if r.in_shortlist else "not in shortlist"
                print(f"  FAIL {r.id}: top {r.top_score}, {where if r.answerable else 'off-topic accepted'}")
    baseline_path = EVAL_DIR / f"{args.persona}.baseline.json"
    if args.save:
        saved = {r.id: r.to_dict() for r in results}
        baseline_path.write_text(json.dumps(saved, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"saved {len(saved)} cases to {baseline_path.relative_to(ROOT)}")
    if args.check:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline = {k: v for k, v in baseline.items() if k in by_split} if args.split != "all" else baseline
        reasons = gate(baseline, results)
        for reason in reasons:
            print(f"WORSE  {reason}")
        print("gate: red" if reasons else "gate: green")
        return 1 if reasons else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
