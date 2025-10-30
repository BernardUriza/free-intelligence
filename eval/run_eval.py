#!/usr/bin/env python3
"""
Golden Set Evaluation Runner - Production Mode (NO MOCKS)

Executes real LLM router calls with tracing and cache measurement.

Philosophy (AURITY):
- No mocks: real router or nothing
- Measure on the wire (router), not client simulation
- Reproducible ≠ simulated: seed for order only, responses are real

File: eval/run_eval.py
Card: FI-OBS-RES-001
Updated: 2025-10-30
"""
import argparse
import csv
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("eval")


# Environment configuration
EVAL_MODE = os.getenv("EVAL_MODE", "prod")  # prod|dry-run (for backward compat)
FI_API_BASE = os.getenv("FI_API_BASE", "http://localhost:7001")
EVAL_LLM_ENDPOINT = os.getenv("EVAL_LLM_ENDPOINT", f"{FI_API_BASE}/llm/generate")
EVAL_PROVIDER = os.getenv("EVAL_PROVIDER", "ollama")
EVAL_MODEL = os.getenv("EVAL_MODEL", "qwen2:7b")
EVAL_MAX_TOKENS = int(os.getenv("EVAL_MAX_TOKENS", "512"))
EVAL_QPS = float(os.getenv("EVAL_QPS", "1"))
EVAL_CONCURRENCY = int(os.getenv("EVAL_CONCURRENCY", "2"))
EVAL_WARMUP = int(os.getenv("EVAL_WARMUP", "8"))
EVAL_CACHE_POLICY = os.getenv("EVAL_CACHE_POLICY", "measure-both")  # none|cold|warm|measure-both
EVAL_SEED = os.getenv("EVAL_SEED", "fi-obs-001")
EVAL_TIMEOUT = int(os.getenv("EVAL_TIMEOUT", "30"))


@dataclass
class PromptSpec:
    prompt_id: str
    category: str
    prompt: str
    expected_keywords: list[str]
    difficulty: str
    notes: str


@dataclass
class PromptMetrics:
    adequacy: float
    factuality: float
    latency_ms: int
    server_latency_ms: Optional[int]  # From router response
    cost_usd: float
    tokens_in: Optional[int]  # None if unknown
    tokens_out: Optional[int]  # None if unknown
    keywords_matched: list[str]
    cache_hit: bool


@dataclass
class PromptResult:
    prompt_id: str
    category: str
    metrics: dict
    trace_id: str
    cache_pass: str  # "cold" | "warm" | "combined"


class GoldenSetEvaluator:
    def __init__(
        self,
        prompts_path: str = "eval/prompts.csv",
        seed: str = EVAL_SEED,
        api_base: str = FI_API_BASE,
        llm_endpoint: str = EVAL_LLM_ENDPOINT,
        provider: str = EVAL_PROVIDER,
        model: str = EVAL_MODEL,
        max_tokens: int = EVAL_MAX_TOKENS,
        cache_policy: str = EVAL_CACHE_POLICY,
        qps: float = EVAL_QPS,
        warmup_count: int = EVAL_WARMUP,
    ):
        self.prompts_path = Path(prompts_path)
        self.seed = seed
        self.api_base = api_base
        self.llm_endpoint = llm_endpoint
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self.cache_policy = cache_policy
        self.qps = qps
        self.warmup_count = warmup_count
        self.prompts: list[PromptSpec] = []
        self.results: list[PromptResult] = []
        self.run_id = f"RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.rng = np.random.default_rng(self._seed_to_int(seed))

        logger.info(f"Evaluator initialized: mode=prod, seed={seed}")
        logger.info(f"  Endpoint: {llm_endpoint}")
        logger.info(f"  Provider: {provider}, Model: {model}")
        logger.info(f"  Cache policy: {cache_policy}")
        logger.info(f"  QPS: {qps}, Warmup: {warmup_count}")

    def _seed_to_int(self, seed: str) -> int:
        """Convert seed string to deterministic int for numpy RNG (order only)"""
        return int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)

    def load_prompts(self) -> list[PromptSpec]:
        """Load prompts from CSV"""
        if not self.prompts_path.exists():
            raise FileNotFoundError(f"Prompts file not found: {self.prompts_path}")

        prompts = []
        with open(self.prompts_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                keywords = [kw.strip() for kw in row["expected_keywords"].split(",")]
                prompts.append(
                    PromptSpec(
                        prompt_id=row["prompt_id"],
                        category=row["category"],
                        prompt=row["prompt"],
                        expected_keywords=keywords,
                        difficulty=row["difficulty"],
                        notes=row.get("notes", ""),
                    )
                )

        self.prompts = prompts
        logger.info(f"Loaded {len(prompts)} prompts from {self.prompts_path}")
        return prompts

    def _call_llm_router(
        self, prompt: PromptSpec, bypass_cache: bool = False
    ) -> tuple[str, int, Optional[int], Optional[int], Optional[int], bool]:
        """
        Call real LLM router (NO MOCKS).

        Args:
            prompt: Prompt specification
            bypass_cache: If True, add X-Bypass-Cache: 1 header

        Returns:
            (response, client_latency_ms, server_latency_ms, tokens_in, tokens_out, cache_hit)

        Raises:
            requests.RequestException: On network/API errors
        """
        trace_id = str(uuid.uuid4())

        headers = {
            "X-Run-Id": self.run_id,
            "X-Trace-Id": trace_id,
            "Content-Type": "application/json",
        }

        if bypass_cache:
            headers["X-Bypass-Cache"] = "1"

        payload = {
            "provider": self.provider,
            "model": self.model,
            "prompt": prompt.prompt,
            "system": "",
            "params": {
                "temperature": 0.2,
                "max_tokens": self.max_tokens,
            },
            "stream": False,
        }

        start_time = time.time()

        try:
            response = requests.post(
                self.llm_endpoint,
                json=payload,
                headers=headers,
                timeout=EVAL_TIMEOUT,
            )
            response.raise_for_status()

            client_latency_ms = int((time.time() - start_time) * 1000)

            data = response.json()

            # Extract response text
            text = data.get("text", "")

            # Extract server latency (if provided by router)
            server_latency_ms = data.get("latency_ms")

            # Extract tokens (None if not provided)
            usage = data.get("usage", {})
            tokens_in = usage.get("in") if usage.get("in") is not None else None
            tokens_out = usage.get("out") if usage.get("out") is not None else None

            # Extract cache hit status
            cache_hit = data.get("cache_hit", False)

            return text, client_latency_ms, server_latency_ms, tokens_in, tokens_out, cache_hit

        except requests.exceptions.Timeout:
            logger.error(f"  Timeout ({EVAL_TIMEOUT}s) for {prompt.prompt_id}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"  HTTP error {e.response.status_code} for {prompt.prompt_id}")
            raise
        except Exception as e:
            logger.error(f"  Request failed for {prompt.prompt_id}: {e}")
            raise

    def _compute_metrics(
        self,
        prompt: PromptSpec,
        response: str,
        client_latency_ms: int,
        server_latency_ms: Optional[int],
        tokens_in: Optional[int],
        tokens_out: Optional[int],
        cache_hit: bool,
    ) -> PromptMetrics:
        """Compute metrics (NO ESTIMATION - report unknowns as None)"""
        # Adequacy: keyword coverage
        keywords_matched = [
            kw for kw in prompt.expected_keywords if kw.lower() in response.lower()
        ]
        adequacy = (
            len(keywords_matched) / len(prompt.expected_keywords)
            if prompt.expected_keywords
            else 0.0
        )

        # Factuality: simple heuristic (response length / expected length)
        # TODO: Replace with actual LLM-based factuality scoring
        factuality = min(1.0, len(response.split()) / 50.0) if response else 0.0

        # Cost: Provider-specific pricing (Ollama = $0, Claude = real pricing)
        if self.provider == "ollama" or self.provider == "local":
            cost_usd = 0.0
        elif self.provider == "anthropic":
            # Claude Sonnet 3.5 pricing (as of 2025)
            cost_usd = (
                (tokens_in or 0) / 1_000_000
            ) * 3.0 + ((tokens_out or 0) / 1_000_000) * 15.0
        elif self.provider == "openai":
            # GPT-4o pricing
            cost_usd = (
                (tokens_in or 0) / 1_000_000
            ) * 5.0 + ((tokens_out or 0) / 1_000_000) * 15.0
        else:
            cost_usd = 0.0

        return PromptMetrics(
            adequacy=round(adequacy, 3),
            factuality=round(factuality, 3),
            latency_ms=client_latency_ms,
            server_latency_ms=server_latency_ms,
            cost_usd=round(cost_usd, 6),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            keywords_matched=keywords_matched,
            cache_hit=cache_hit,
        )

    def run_evaluation(self) -> list[PromptResult]:
        """
        Run evaluation with cache policy.

        Cache policies:
        - none: No special handling
        - cold: Force cache bypass on all requests
        - warm: Allow cache hits (after warmup)
        - measure-both: Run cold pass + warm pass
        """
        logger.info(f"Starting evaluation (run_id={self.run_id})...")
        logger.info(f"  Mode: PRODUCTION (NO MOCKS)")
        logger.info(f"  Cache policy: {self.cache_policy}")
        logger.info(f"  Total prompts: {len(self.prompts)}")

        if self.cache_policy == "measure-both":
            logger.info("Running COLD pass (bypass cache)...")
            self._run_pass(bypass_cache=True, cache_pass="cold")

            logger.info(f"Warmup: {self.warmup_count} requests...")
            self._warmup_cache()

            logger.info("Running WARM pass (allow cache)...")
            self._run_pass(bypass_cache=False, cache_pass="warm")

        elif self.cache_policy == "cold":
            self._run_pass(bypass_cache=True, cache_pass="cold")

        elif self.cache_policy == "warm":
            logger.info(f"Warmup: {self.warmup_count} requests...")
            self._warmup_cache()
            self._run_pass(bypass_cache=False, cache_pass="warm")

        else:  # none
            self._run_pass(bypass_cache=False, cache_pass="combined")

        return self.results

    def _warmup_cache(self):
        """Warm up cache with first N prompts"""
        for i, prompt in enumerate(self.prompts[: self.warmup_count], 1):
            logger.info(f"  Warmup [{i}/{self.warmup_count}] {prompt.prompt_id}")
            try:
                self._call_llm_router(prompt, bypass_cache=False)
                time.sleep(1.0 / self.qps)  # Rate limiting
            except Exception as e:
                logger.warning(f"  Warmup failed for {prompt.prompt_id}: {e}")

    def _run_pass(self, bypass_cache: bool, cache_pass: str):
        """Run single evaluation pass"""
        for i, prompt in enumerate(self.prompts, 1):
            logger.info(
                f"[{i}/{len(self.prompts)}] {prompt.prompt_id} ({prompt.category}) - {cache_pass}"
            )

            try:
                (
                    response,
                    client_latency_ms,
                    server_latency_ms,
                    tokens_in,
                    tokens_out,
                    cache_hit,
                ) = self._call_llm_router(prompt, bypass_cache=bypass_cache)

                metrics = self._compute_metrics(
                    prompt,
                    response,
                    client_latency_ms,
                    server_latency_ms,
                    tokens_in,
                    tokens_out,
                    cache_hit,
                )

                self.results.append(
                    PromptResult(
                        prompt_id=prompt.prompt_id,
                        category=prompt.category,
                        metrics={
                            "adequacy": metrics.adequacy,
                            "factuality": metrics.factuality,
                            "latency_ms": metrics.latency_ms,
                            "server_latency_ms": metrics.server_latency_ms,
                            "cost_usd": metrics.cost_usd,
                            "tokens_in": metrics.tokens_in,
                            "tokens_out": metrics.tokens_out,
                            "tokens_unknown": 1
                            if (metrics.tokens_in is None or metrics.tokens_out is None)
                            else 0,
                            "keywords_matched": metrics.keywords_matched,
                            "cache_hit": metrics.cache_hit,
                        },
                        trace_id=f"{self.run_id}_{prompt.prompt_id}_{cache_pass}",
                        cache_pass=cache_pass,
                    )
                )

                logger.info(
                    f"  ✓ adequacy={metrics.adequacy:.2f}, latency={metrics.latency_ms}ms"
                    + (f" (server={metrics.server_latency_ms}ms)" if metrics.server_latency_ms else "")
                    + (f", cache_hit" if metrics.cache_hit else "")
                )

                # Rate limiting
                time.sleep(1.0 / self.qps)

            except Exception as e:
                logger.error(f"  ✗ Failed: {e}")
                # Continue with next prompt instead of failing entire run

    def compute_aggregates(self, cache_pass: Optional[str] = None) -> dict:
        """Compute aggregate metrics for specified cache pass or all results"""
        if cache_pass:
            results = [r for r in self.results if r.cache_pass == cache_pass]
        else:
            results = self.results

        if not results:
            return {}

        adequacy_scores = [r.metrics["adequacy"] for r in results]
        factuality_scores = [r.metrics["factuality"] for r in results]
        latencies = [r.metrics["latency_ms"] for r in results]
        tokens_in = [
            r.metrics["tokens_in"] for r in results if r.metrics["tokens_in"] is not None
        ]
        tokens_out = [
            r.metrics["tokens_out"]
            for r in results
            if r.metrics["tokens_out"] is not None
        ]
        tokens_unknown_count = sum(r.metrics["tokens_unknown"] for r in results)
        costs = [r.metrics["cost_usd"] for r in results]
        cache_hits = sum(1 for r in results if r.metrics["cache_hit"])

        return {
            "avg_adequacy": round(np.mean(adequacy_scores), 3) if adequacy_scores else 0.0,
            "avg_factuality": round(np.mean(factuality_scores), 3)
            if factuality_scores
            else 0.0,
            "p50_latency_ms": int(np.percentile(latencies, 50)) if latencies else 0,
            "p95_latency_ms": int(np.percentile(latencies, 95)) if latencies else 0,
            "p99_latency_ms": int(np.percentile(latencies, 99)) if latencies else 0,
            "total_cost_usd": round(sum(costs), 6),
            "total_tokens_in": sum(tokens_in) if tokens_in else 0,
            "total_tokens_out": sum(tokens_out) if tokens_out else 0,
            "tokens_unknown_count": tokens_unknown_count,
            "cache_hit_count": cache_hits,
            "cache_hit_ratio": round(cache_hits / len(results), 3) if results else 0.0,
        }

    def save_results(self, output_path: Path) -> dict:
        """Save results in schema-compliant format"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).isoformat()

        # Compute aggregates for each cache pass
        aggregates_cold = self.compute_aggregates(cache_pass="cold")
        aggregates_warm = self.compute_aggregates(cache_pass="warm")
        aggregates_combined = self.compute_aggregates(cache_pass=None)

        output = {
            "run_id": self.run_id,
            "timestamp": timestamp,
            "mode": "production",
            "provider": self.provider,
            "model": self.model,
            "seed": self.seed,
            "cache_policy": self.cache_policy,
            "total_prompts": len(self.results),
            "results": [
                {
                    "prompt_id": r.prompt_id,
                    "category": r.category,
                    "metrics": r.metrics,
                    "trace_id": r.trace_id,
                    "cache_pass": r.cache_pass,
                }
                for r in self.results
            ],
            "aggregates": {
                "cold": aggregates_cold,
                "warm": aggregates_warm,
                "combined": aggregates_combined,
            },
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Results saved to {output_path}")
        return output

    def generate_manifest(self, output_path: Path, results_file: Path) -> dict:
        """Generate manifest.json with metadata and hashes"""
        # Compute dataset digest
        with open(self.prompts_path, "rb") as f:
            dataset_digest = hashlib.sha256(f.read()).hexdigest()

        # Git SHA (if available)
        try:
            import subprocess

            git_sha = (
                subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
                .strip()
            )
        except:
            git_sha = "unknown"

        aggregates_combined = self.compute_aggregates(cache_pass=None)

        manifest = {
            "version": "1.1",
            "run_id": self.run_id,
            "mode": "production",
            "git_sha": git_sha,
            "dataset_digest": dataset_digest,
            "runner": "run_eval.py@2.0-prod",
            "seed": self.seed,
            "provider": self.provider,
            "model": self.model,
            "cache_policy": self.cache_policy,
            "metrics": aggregates_combined,
            "files": [str(results_file.name), "report/QA_REPORT.md"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved to {output_path}")
        return manifest


def main():
    parser = argparse.ArgumentParser(description="Golden Set Evaluation Runner (Production)")
    parser.add_argument("--prompts", type=str, default="eval/prompts.csv")
    parser.add_argument("--seed", type=str, default=EVAL_SEED)
    parser.add_argument("--provider", type=str, default=EVAL_PROVIDER)
    parser.add_argument("--model", type=str, default=EVAL_MODEL)
    parser.add_argument("--cache-policy", type=str, default=EVAL_CACHE_POLICY)
    parser.add_argument("--qps", type=float, default=EVAL_QPS)
    parser.add_argument("--warmup", type=int, default=EVAL_WARMUP)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--manifest", type=str, default=None)
    args = parser.parse_args()

    # Default output paths
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output or f"eval/results/run_{timestamp}.json")
    manifest_path = Path(args.manifest or "eval/results/manifest.json")

    evaluator = GoldenSetEvaluator(
        prompts_path=args.prompts,
        seed=args.seed,
        provider=args.provider,
        model=args.model,
        cache_policy=args.cache_policy,
        qps=args.qps,
        warmup_count=args.warmup,
    )

    try:
        evaluator.load_prompts()
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Run evaluation
    evaluator.run_evaluation()
    results = evaluator.save_results(output_path)
    manifest = evaluator.generate_manifest(manifest_path, output_path)

    # Print summary
    print("\n" + "=" * 70)
    print("Golden Set Evaluation Summary (PRODUCTION)")
    print("=" * 70)
    print(f"Run ID:          {results['run_id']}")
    print(f"Mode:            {results['mode']}")
    print(f"Provider:        {results['provider']}")
    print(f"Model:           {results['model']}")
    print(f"Seed:            {args.seed}")
    print(f"Cache Policy:    {results['cache_policy']}")
    print(f"Total Prompts:   {results['total_prompts']}")
    print(f"Dataset Digest:  {manifest['dataset_digest'][:16]}...")
    print(f"Git SHA:         {manifest['git_sha']}")

    # Print aggregates for each cache pass
    for pass_name in ["cold", "warm", "combined"]:
        agg = results["aggregates"].get(pass_name)
        if agg and agg.get("avg_adequacy") is not None:
            print(f"\nAggregate Metrics ({pass_name.upper()}):")
            print(f"  Avg Adequacy:    {agg['avg_adequacy']:.3f}")
            print(f"  Avg Factuality:  {agg['avg_factuality']:.3f}")
            print(f"  p50 Latency:     {agg['p50_latency_ms']}ms")
            print(f"  p95 Latency:     {agg['p95_latency_ms']}ms")
            print(f"  p99 Latency:     {agg['p99_latency_ms']}ms")
            print(f"  Total Cost:      ${agg['total_cost_usd']:.4f}")
            print(f"  Tokens Unknown:  {agg['tokens_unknown_count']}")
            print(f"  Cache Hit Ratio: {agg['cache_hit_ratio']:.3f}")

    print("=" * 70)
    print(f"\nResults: {output_path}")
    print(f"Manifest: {manifest_path}")
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
