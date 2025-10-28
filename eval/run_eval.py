#!/usr/bin/env python3
"""
Free Intelligence - Evaluation Runner

Evaluates LLM performance on 50 test prompts:
- 30 green (should pass easily)
- 10 yellow (moderate difficulty)
- 10 edge (challenging cases)

Metrics:
- Latency (p50, p95, p99)
- Quality score (heuristic: length, keywords, urgency match)
- Success rate by category

Output: Markdown report saved to eval/results/

File: eval/run_eval.py
Created: 2025-10-28
"""

import sys
import csv
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import statistics

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.llm_router import llm_generate
from backend.preset_loader import get_preset_loader
from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvalCase:
    """Single evaluation test case"""
    id: int
    category: str
    difficulty: str
    prompt: str
    expected_keywords: List[str]
    min_length: int
    max_length: int
    urgency_expected: str
    notes: str


@dataclass
class EvalResult:
    """Result of evaluating single case"""
    case_id: int
    category: str
    difficulty: str
    prompt: str
    response: str
    latency_ms: float
    tokens: int
    cost_usd: float

    # Quality scores
    length_score: float  # 0-100
    keyword_score: float  # 0-100
    urgency_score: float  # 0-100
    total_score: float  # 0-100

    passed: bool
    error: str = None


class EvalRunner:
    """
    Evaluation runner for IntakeCoach preset.

    Runs all test cases and generates quality metrics.
    """

    def __init__(
        self,
        prompts_csv: str = "eval/prompts.csv",
        provider: str = "ollama",
        pass_threshold: float = 70.0
    ):
        """
        Initialize eval runner.

        Args:
            prompts_csv: Path to prompts CSV
            provider: LLM provider (ollama or claude)
            pass_threshold: Minimum score to pass (0-100)
        """
        self.prompts_csv = Path(prompts_csv)
        self.provider = provider
        self.pass_threshold = pass_threshold
        self.logger = get_logger(__name__)

        # Load preset
        self.preset_loader = get_preset_loader()
        self.preset = self.preset_loader.load_preset("intake_coach")

        self.logger.info("EVAL_RUNNER_INITIALIZED",
                        prompts_csv=str(self.prompts_csv),
                        provider=provider,
                        pass_threshold=pass_threshold)

    def load_cases(self) -> List[EvalCase]:
        """Load test cases from CSV"""
        cases = []

        with open(self.prompts_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                case = EvalCase(
                    id=int(row['id']),
                    category=row['category'],
                    difficulty=row['difficulty'],
                    prompt=row['prompt'],
                    expected_keywords=row['expected_keywords'].split(','),
                    min_length=int(row['min_length']),
                    max_length=int(row['max_length']),
                    urgency_expected=row['urgency_expected'],
                    notes=row['notes']
                )
                cases.append(case)

        self.logger.info("EVAL_CASES_LOADED", count=len(cases))
        return cases

    def evaluate_case(self, case: EvalCase) -> EvalResult:
        """
        Evaluate single test case.

        Args:
            case: EvalCase to evaluate

        Returns:
            EvalResult with scores
        """
        self.logger.info("EVAL_CASE_STARTED",
                        case_id=case.id,
                        category=case.category,
                        difficulty=case.difficulty)

        try:
            # Generate with LLM
            full_prompt = f"{self.preset.system_prompt}\n\nPatient Input:\n{case.prompt}\n\nJSON Output:"

            start_time = time.time()
            response = llm_generate(
                prompt=full_prompt,
                provider=self.provider,
                temperature=self.preset.temperature,
                max_tokens=self.preset.max_tokens
            )
            latency_ms = (time.time() - start_time) * 1000

            # Parse response
            try:
                output = json.loads(response.content)
            except json.JSONDecodeError:
                # JSON parse failed
                return EvalResult(
                    case_id=case.id,
                    category=case.category,
                    difficulty=case.difficulty,
                    prompt=case.prompt,
                    response=response.content[:200],
                    latency_ms=latency_ms,
                    tokens=response.tokens_used,
                    cost_usd=response.cost_usd,
                    length_score=0,
                    keyword_score=0,
                    urgency_score=0,
                    total_score=0,
                    passed=False,
                    error="JSON_PARSE_ERROR"
                )

            # Score response
            length_score = self._score_length(response.content, case)
            keyword_score = self._score_keywords(response.content, case)
            urgency_score = self._score_urgency(output, case)

            total_score = (length_score + keyword_score + urgency_score) / 3.0
            passed = total_score >= self.pass_threshold

            result = EvalResult(
                case_id=case.id,
                category=case.category,
                difficulty=case.difficulty,
                prompt=case.prompt,
                response=response.content,
                latency_ms=latency_ms,
                tokens=response.tokens_used,
                cost_usd=response.cost_usd,
                length_score=length_score,
                keyword_score=keyword_score,
                urgency_score=urgency_score,
                total_score=total_score,
                passed=passed
            )

            self.logger.info("EVAL_CASE_COMPLETED",
                           case_id=case.id,
                           score=total_score,
                           passed=passed,
                           latency_ms=latency_ms)

            return result

        except Exception as e:
            self.logger.error("EVAL_CASE_FAILED",
                            case_id=case.id,
                            error=str(e))

            return EvalResult(
                case_id=case.id,
                category=case.category,
                difficulty=case.difficulty,
                prompt=case.prompt,
                response="",
                latency_ms=0,
                tokens=0,
                cost_usd=0,
                length_score=0,
                keyword_score=0,
                urgency_score=0,
                total_score=0,
                passed=False,
                error=str(e)
            )

    def _score_length(self, response: str, case: EvalCase) -> float:
        """Score response length (0-100)"""
        length = len(response)

        if length < case.min_length:
            return max(0, (length / case.min_length) * 100)
        elif length > case.max_length:
            return max(0, 100 - ((length - case.max_length) / case.max_length * 50))
        else:
            return 100.0

    def _score_keywords(self, response: str, case: EvalCase) -> float:
        """Score keyword presence (0-100)"""
        response_lower = response.lower()
        matches = sum(1 for kw in case.expected_keywords if kw.lower() in response_lower)

        if not case.expected_keywords:
            return 100.0

        return (matches / len(case.expected_keywords)) * 100

    def _score_urgency(self, output: Dict, case: EvalCase) -> float:
        """Score urgency match (0-100)"""
        actual_urgency = output.get('urgency', 'UNKNOWN')

        if actual_urgency == case.urgency_expected:
            return 100.0
        elif actual_urgency in ['HIGH', 'CRITICAL'] and case.urgency_expected in ['HIGH', 'CRITICAL']:
            return 75.0  # Partial credit for high-urgency cases
        else:
            return 0.0

    def run_all(self) -> List[EvalResult]:
        """Run all evaluation cases"""
        cases = self.load_cases()
        results = []

        print(f"\n{'='*70}")
        print(f"🎯 Running Evaluation: {len(cases)} cases")
        print(f"{'='*70}")

        for i, case in enumerate(cases, 1):
            print(f"\n[{i}/{len(cases)}] Case {case.id}: {case.category}/{case.difficulty}")
            print(f"  Prompt: {case.prompt[:60]}...")

            result = self.evaluate_case(case)
            results.append(result)

            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  Result: {status} (score: {result.total_score:.1f}, latency: {result.latency_ms:.0f}ms)")

            if result.error:
                print(f"  Error: {result.error}")

        print(f"\n{'='*70}")
        print(f"✅ Evaluation Complete: {len(results)} results")
        print(f"{'='*70}\n")

        return results

    def generate_report(self, results: List[EvalResult]) -> str:
        """
        Generate markdown report.

        Args:
            results: List of EvalResult

        Returns:
            Markdown report string
        """
        # Calculate statistics
        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        scores = [r.total_score for r in results]
        passed_count = sum(1 for r in results if r.passed)

        # By category
        by_category = {}
        for r in results:
            if r.category not in by_category:
                by_category[r.category] = []
            by_category[r.category].append(r)

        # Generate report
        report = []
        report.append("# Free Intelligence - Evaluation Report")
        report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Provider**: {self.provider}")
        report.append(f"**Model**: {self.preset.model}")
        report.append(f"**Pass Threshold**: {self.pass_threshold}")
        report.append(f"**Total Cases**: {len(results)}")

        # Summary
        report.append("\n## 📊 Summary")
        report.append(f"\n- **Pass Rate**: {passed_count}/{len(results)} ({passed_count/len(results)*100:.1f}%)")
        report.append(f"- **Mean Score**: {statistics.mean(scores):.1f}")
        report.append(f"- **Median Score**: {statistics.median(scores):.1f}")

        # Latency
        if latencies:
            report.append("\n## ⏱️  Latency")
            report.append(f"\n- **p50**: {self._percentile(sorted(latencies), 50):.0f}ms")
            report.append(f"- **p95**: {self._percentile(sorted(latencies), 95):.0f}ms")
            report.append(f"- **p99**: {self._percentile(sorted(latencies), 99):.0f}ms")
            report.append(f"- **Mean**: {statistics.mean(latencies):.0f}ms")
            report.append(f"- **Min**: {min(latencies):.0f}ms")
            report.append(f"- **Max**: {max(latencies):.0f}ms")

        # By category
        report.append("\n## 📂 Results by Category")
        for category in ['green', 'yellow', 'edge']:
            if category in by_category:
                cat_results = by_category[category]
                cat_passed = sum(1 for r in cat_results if r.passed)
                cat_scores = [r.total_score for r in cat_results]

                report.append(f"\n### {category.upper()} ({len(cat_results)} cases)")
                report.append(f"- Pass Rate: {cat_passed}/{len(cat_results)} ({cat_passed/len(cat_results)*100:.1f}%)")
                report.append(f"- Mean Score: {statistics.mean(cat_scores):.1f}")

        # Failures
        failures = [r for r in results if not r.passed]
        if failures:
            report.append("\n## ❌ Failures")
            report.append(f"\n{len(failures)} cases failed:\n")
            for r in failures:
                report.append(f"- **Case {r.case_id}** ({r.category}/{r.difficulty}): score={r.total_score:.1f}")
                if r.error:
                    report.append(f"  - Error: {r.error}")

        # Cost
        total_cost = sum(r.cost_usd for r in results)
        total_tokens = sum(r.tokens for r in results)
        report.append("\n## 💰 Cost")
        report.append(f"\n- **Total Cost**: ${total_cost:.6f}")
        report.append(f"- **Total Tokens**: {total_tokens:,}")

        return "\n".join(report)

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Free Intelligence Evaluation Runner"
    )

    parser.add_argument('--provider', default='ollama',
                       choices=['ollama', 'claude'],
                       help='LLM provider')
    parser.add_argument('--threshold', type=float, default=70.0,
                       help='Pass threshold (0-100)')
    parser.add_argument('--output', default='eval/results',
                       help='Output directory for reports')

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluation
    runner = EvalRunner(
        provider=args.provider,
        pass_threshold=args.threshold
    )

    results = runner.run_all()

    # Generate report
    report = runner.generate_report(results)

    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f"eval_report_{args.provider}_{timestamp}.md"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 Report saved: {report_path}")

    # Also save results as JSON
    json_path = output_dir / f"eval_results_{args.provider}_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in results], f, indent=2)

    print(f"📄 JSON saved: {json_path}")

    # Print report
    print("\n" + report)


if __name__ == '__main__':
    main()
