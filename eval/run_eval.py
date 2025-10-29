#!/usr/bin/env python3
"""
Golden Set Evaluation Runner - Card: FI-OBS-RES-001
"""
import argparse, csv, json, logging, sys, time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("eval")

@dataclass
class EvalPrompt:
    prompt_id: str
    category: str
    prompt: str
    expected_keywords: list[str]
    difficulty: str
    notes: str

@dataclass
class EvalResult:
    prompt_id: str
    prompt: str
    response: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    timestamp: str
    adecuacion_score: Optional[int] = None

class GoldenSetEvaluator:
    def __init__(self, prompts_path: str = "eval/prompts.csv", dry_run: bool = False):
        self.prompts_path = Path(prompts_path)
        self.dry_run = dry_run
        self.prompts: list[EvalPrompt] = []
        self.results: list[EvalResult] = []

    def load_prompts(self) -> list[EvalPrompt]:
        if not self.prompts_path.exists():
            raise FileNotFoundError(f"Prompts file not found: {self.prompts_path}")
        prompts = []
        with open(self.prompts_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompts.append(EvalPrompt(prompt_id=row["prompt_id"], category=row["category"], prompt=row["prompt"], expected_keywords=row["expected_keywords"].split(","), difficulty=row["difficulty"], notes=row["notes"]))
        self.prompts = prompts
        logger.info(f"Loaded {len(prompts)} prompts")
        return prompts

    def send_prompt(self, prompt: EvalPrompt) -> EvalResult:
        if self.dry_run:
            return EvalResult(prompt_id=prompt.prompt_id, prompt=prompt.prompt, response=f"[DRY RUN] Mock response for {prompt.prompt_id}", latency_ms=1000.0, input_tokens=len(prompt.prompt.split()), output_tokens=50, timestamp=datetime.now().isoformat())
        logger.warning("Real LLM execution not implemented yet")
        return EvalResult(prompt_id=prompt.prompt_id, prompt=prompt.prompt, response="[NOT IMPLEMENTED]", latency_ms=0, input_tokens=0, output_tokens=0, timestamp=datetime.now().isoformat())

    def score_adecuacion(self, prompt: EvalPrompt, response: str) -> int:
        keywords = [kw.strip() for kw in prompt.expected_keywords]
        matches = sum(1 for kw in keywords if kw.lower() in response.lower())
        coverage = matches / len(keywords) if keywords else 0
        if coverage >= 1.0: return 5
        elif coverage >= 0.75: return 4
        elif coverage >= 0.5: return 3
        elif coverage >= 0.25: return 2
        else: return 1

    def run_evaluation(self) -> list[EvalResult]:
        logger.info(f"Starting evaluation ({len(self.prompts)} prompts)...")
        for i, prompt in enumerate(self.prompts, 1):
            logger.info(f"[{i}/{len(self.prompts)}] {prompt.prompt_id}")
            try:
                result = self.send_prompt(prompt)
                result.adecuacion_score = self.score_adecuacion(prompt, result.response)
                self.results.append(result)
                logger.info(f"  ✓ adecuacion: {result.adecuacion_score}/5")
            except Exception as e:
                logger.error(f"  ✗ Failed: {e}")
        return self.results

    def generate_report(self) -> dict[str, Any]:
        if not self.results:
            return {"error": "No results"}
        total = len(self.results)
        avg_latency = sum(r.latency_ms for r in self.results) / total
        adec_scores = [r.adecuacion_score for r in self.results if r.adecuacion_score]
        avg_adec = sum(adec_scores) / len(adec_scores) if adec_scores else 0
        total_input = sum(r.input_tokens for r in self.results)
        total_output = sum(r.output_tokens for r in self.results)
        cost = (total_input / 1000) * 0.003 + (total_output / 1000) * 0.015
        return {"timestamp": datetime.now().isoformat(), "summary": {"total_prompts": total, "avg_latency_ms": avg_latency, "avg_adecuacion": avg_adec, "total_input_tokens": total_input, "total_output_tokens": total_output, "estimated_cost_usd": cost}}

    def save_results(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for r in self.results:
                f.write(json.dumps({"prompt_id": r.prompt_id, "prompt": r.prompt, "response": r.response, "latency_ms": r.latency_ms, "input_tokens": r.input_tokens, "output_tokens": r.output_tokens, "timestamp": r.timestamp, "adecuacion_score": r.adecuacion_score}) + "\n")
        logger.info(f"Results saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Golden Set Evaluation Runner")
    parser.add_argument("--prompts", type=str, default="eval/prompts.csv")
    parser.add_argument("--output", type=str)
    parser.add_argument("--report", type=str)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    evaluator = GoldenSetEvaluator(prompts_path=args.prompts, dry_run=args.dry_run)
    try:
        evaluator.load_prompts()
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    evaluator.run_evaluation()
    report = evaluator.generate_report()
    print("\n" + "=" * 60)
    print("Evaluation Report")
    print("=" * 60)
    print(f"Total Prompts: {report['summary']['total_prompts']}")
    print(f"Avg Latency: {report['summary']['avg_latency_ms']:.0f}ms")
    print(f"Avg Adecuación: {report['summary']['avg_adecuacion']:.1f}/5")
    print(f"Estimated Cost: ${report['summary']['estimated_cost_usd']:.2f}")
    print("=" * 60)
    if args.output:
        evaluator.save_results(Path(args.output))
    if args.report:
        with open(Path(args.report), "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {args.report}")
    sys.exit(0)

if __name__ == "__main__":
    main()
