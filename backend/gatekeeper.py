from __future__ import annotations

"""
Free Intelligence - Gatekeeper (Intelligent A/B Routing)

Provides quality-based routing between providers:
- Ollama (local, free, private) for simple queries
- Claude (cloud, paid, high-quality) for complex queries or low-quality fallback

Philosophy: Start conservative (10% Ollama), increase progressively based on quality metrics.

File: backend/gatekeeper.py
Created: 2025-10-28 (Sprint 4)
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from backend.logger import get_logger
from backend.policy_loader import get_policy_loader

logger = get_logger(__name__)


class RoutingDecision(Enum):
    """Routing decision for LLM provider selection"""

    USE_PRIMARY = "use_primary"  # Use primary provider (Ollama)
    USE_FALLBACK = "use_fallback"  # Use fallback provider (Claude)
    USE_CACHE = "use_cache"  # Use cached response


@dataclass
class QualityScore:
    """
    Quality score for LLM response evaluation.

    Score ranges:
    - 90-100: Excellent (safe for 100% Ollama)
    - 75-89:  Good (safe for 50% Ollama)
    - 70-74:  Acceptable (safe for 10% Ollama)
    - <70:    Poor (fallback to Claude)
    """

    total_score: int  # 0-100
    length_score: int  # 0-30 points
    keyword_score: int  # 0-30 points
    coherence_score: int  # 0-20 points
    completeness_score: int  # 0-20 points
    checks_passed: dict[str, bool]
    explanation: str


class QualityScorer:
    """
    Heuristic-based quality scorer for LLM responses.

    Evaluates responses based on:
    1. Length (not too short, not too long)
    2. Keyword presence (domain-specific terms)
    3. Coherence (proper sentences, punctuation)
    4. Completeness (no truncation indicators)
    """

    # Length thresholds (characters)
    MIN_LENGTH = 50
    OPTIMAL_MIN_LENGTH = 100
    OPTIMAL_MAX_LENGTH = 2000
    MAX_LENGTH = 4000

    # Keywords that indicate quality domain responses
    # (Will be domain-specific in production)
    QUALITY_KEYWORDS = [
        # General quality indicators
        "because",
        "therefore",
        "however",
        "although",
        "specifically",
        "example",
        "such as",
        "including",
        "particularly",
        # Technical/medical (placeholder for actual domain)
        "patient",
        "treatment",
        "diagnosis",
        "symptom",
        "condition",
        "data",
        "analysis",
        "result",
        "research",
        "study",
    ]

    # Indicators of truncation or incompleteness
    TRUNCATION_INDICATORS = [
        "...",
        "[truncated]",
        "[continued]",
        "to be continued",
        "part 1 of",
        "see next",
        "more details in",
    ]

    # Negative sentiment keywords (for health queries, should be neutral/positive)
    NEGATIVE_KEYWORDS = [
        "unfortunately",
        "sadly",
        "regrettably",
        "cannot help",
        "unable to",
        "sorry",
        "don't know",
        "uncertain",
    ]

    def __init__(self):
        self.logger = get_logger(__name__)

    def score_response(self, prompt: str, response: str, provider: str = "ollama") -> QualityScore:
        """
        Score a response using heuristics.

        Args:
            prompt: Original prompt
            response: LLM response to score
            provider: Provider that generated the response

        Returns:
            QualityScore with breakdown
        """
        checks = {}

        # 1. Length score (0-30 points)
        length_score, length_checks = self._score_length(response)
        checks.update(length_checks)

        # 2. Keyword score (0-30 points)
        keyword_score, keyword_checks = self._score_keywords(response)
        checks.update(keyword_checks)

        # 3. Coherence score (0-20 points)
        coherence_score, coherence_checks = self._score_coherence(response)
        checks.update(coherence_checks)

        # 4. Completeness score (0-20 points)
        completeness_score, completeness_checks = self._score_completeness(response)
        checks.update(completeness_checks)

        # Total score
        total_score = length_score + keyword_score + coherence_score + completeness_score

        # Generate explanation
        explanation = self._generate_explanation(
            total_score, length_score, keyword_score, coherence_score, completeness_score
        )

        quality_score = QualityScore(
            total_score=total_score,
            length_score=length_score,
            keyword_score=keyword_score,
            coherence_score=coherence_score,
            completeness_score=completeness_score,
            checks_passed=checks,
            explanation=explanation,
        )

        self.logger.info(
            "QUALITY_SCORE_CALCULATED",
            provider=provider,
            total_score=total_score,
            length_score=length_score,
            keyword_score=keyword_score,
            coherence_score=coherence_score,
            completeness_score=completeness_score,
            response_length=len(response),
        )

        return quality_score

    def _score_length(self, response: str) -> tuple[int, dict[str, bool]]:
        """Score response length (0-30 points)"""
        length = len(response)
        checks = {}

        checks["length_not_empty"] = length > 0
        checks["length_above_minimum"] = length >= self.MIN_LENGTH
        checks["length_in_optimal_range"] = (
            self.OPTIMAL_MIN_LENGTH <= length <= self.OPTIMAL_MAX_LENGTH
        )
        checks["length_not_excessive"] = length <= self.MAX_LENGTH

        if length == 0:
            return 0, checks
        elif length < self.MIN_LENGTH:
            return 5, checks  # Too short
        elif length < self.OPTIMAL_MIN_LENGTH:
            return 15, checks  # Short but acceptable
        elif length <= self.OPTIMAL_MAX_LENGTH:
            return 30, checks  # Optimal length
        elif length <= self.MAX_LENGTH:
            return 20, checks  # A bit long but OK
        else:
            return 10, checks  # Too long

    def _score_keywords(self, response: str) -> tuple[int, dict[str, bool]]:
        """Score keyword presence (0-30 points)"""
        response_lower = response.lower()
        checks = {}

        # Count quality keywords
        quality_keyword_count = sum(
            1 for keyword in self.QUALITY_KEYWORDS if keyword in response_lower
        )

        # Count negative keywords
        negative_keyword_count = sum(
            1 for keyword in self.NEGATIVE_KEYWORDS if keyword in response_lower
        )

        checks["has_quality_keywords"] = quality_keyword_count > 0
        checks["has_multiple_quality_keywords"] = quality_keyword_count >= 3
        checks["no_negative_keywords"] = negative_keyword_count == 0
        checks["low_negative_keywords"] = negative_keyword_count <= 1

        # Score calculation
        score = 0

        # Add points for quality keywords (up to 20 points)
        if quality_keyword_count >= 5:
            score += 20
        elif quality_keyword_count >= 3:
            score += 15
        elif quality_keyword_count >= 1:
            score += 10

        # Deduct points for negative keywords (up to -10 points)
        if negative_keyword_count == 0:
            score += 10  # Bonus for no negatives
        elif negative_keyword_count <= 1:
            score += 5  # Minor negative presence
        else:
            score -= 5  # Too many negatives

        return max(0, min(30, score)), checks

    def _score_coherence(self, response: str) -> tuple[int, dict[str, bool]]:
        """Score response coherence (0-20 points)"""
        checks = {}

        # Check for proper sentences (capital letter + period)
        has_sentences = bool(re.search(r"[A-Z][^.!?]*[.!?]", response))

        # Check for paragraphs/structure
        has_structure = "\n" in response or len(response) > 200

        # Check for proper punctuation
        has_punctuation = any(p in response for p in ".!?,;:")

        # Check for complete sentences (not just fragments)
        sentence_count = len(re.findall(r"[.!?]", response))
        has_multiple_sentences = sentence_count >= 2

        checks["has_sentences"] = has_sentences
        checks["has_structure"] = has_structure
        checks["has_punctuation"] = has_punctuation
        checks["has_multiple_sentences"] = has_multiple_sentences

        score = 0
        if has_sentences:
            score += 8
        if has_structure:
            score += 4
        if has_punctuation:
            score += 4
        if has_multiple_sentences:
            score += 4

        return score, checks

    def _score_completeness(self, response: str) -> tuple[int, dict[str, bool]]:
        """Score response completeness (0-20 points)"""
        response_lower = response.lower()
        checks = {}

        # Check for truncation indicators
        has_truncation = any(
            indicator in response_lower for indicator in self.TRUNCATION_INDICATORS
        )

        # Check for complete ending (ends with punctuation)
        ends_properly = response.strip()[-1] in ".!?"

        # Check for balanced quotes/parentheses
        quote_count = response.count('"')
        paren_open = response.count("(")
        paren_close = response.count(")")
        balanced_quotes = (quote_count % 2) == 0
        balanced_parens = paren_open == paren_close

        checks["no_truncation_indicators"] = not has_truncation
        checks["ends_with_punctuation"] = ends_properly
        checks["balanced_quotes"] = balanced_quotes
        checks["balanced_parentheses"] = balanced_parens

        score = 20  # Start with full points

        if has_truncation:
            score -= 10  # Major penalty
        if not ends_properly:
            score -= 5
        if not balanced_quotes:
            score -= 3
        if not balanced_parens:
            score -= 2

        return max(0, score), checks

    def _generate_explanation(
        self, total: int, length: int, keywords: int, coherence: int, completeness: int
    ) -> str:
        """Generate human-readable explanation of score"""
        if total >= 90:
            quality = "Excellent"
        elif total >= 75:
            quality = "Good"
        elif total >= 70:
            quality = "Acceptable"
        else:
            quality = "Poor"

        return (
            f"{quality} quality (score: {total}/100). "
            f"Length: {length}/30, Keywords: {keywords}/30, "
            f"Coherence: {coherence}/20, Completeness: {completeness}/20"
        )


class Gatekeeper:
    """
    Intelligent routing between LLM providers based on quality scoring.

    Progressive rollout strategy:
    - Phase 1 (10% Ollama): Conservative, fallback on score < 70
    - Phase 2 (50% Ollama): If avg score > 75 for 7 days
    - Phase 3 (100% Ollama): If avg score > 85 for 7 days

    Automatic rollback if quality degrades.
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.scorer = QualityScorer()
        self.policy_loader = get_policy_loader()

    def should_use_primary(
        self, prompt: str, force_provider: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Decide whether to use primary provider (Ollama) or fallback (Claude).

        Args:
            prompt: User prompt
            force_provider: Force specific provider (for testing)

        Returns:
            (use_primary: bool, reason: str)
        """
        llm_config = self.policy_loader.get_llm_config()
        primary_provider = llm_config.get("primary_provider", "claude")
        enable_offline = llm_config.get("enable_offline", False)

        # If forced provider specified
        if force_provider:
            use_primary = force_provider == primary_provider
            reason = f"forced_provider={force_provider}"
            self.logger.info(
                "GATEKEEPER_DECISION",
                decision="use_primary" if use_primary else "use_fallback",
                reason=reason,
                primary_provider=primary_provider,
            )
            return use_primary, reason

        # If offline mode disabled, always use configured primary
        if not enable_offline:
            reason = "offline_mode_disabled"
            self.logger.info(
                "GATEKEEPER_DECISION",
                decision="use_configured_primary",
                reason=reason,
                primary_provider=primary_provider,
            )
            return True, reason

        # Default: use primary provider
        # (In future sprints, add progressive rollout logic here)
        reason = "default_primary_provider"
        self.logger.info(
            "GATEKEEPER_DECISION",
            decision="use_primary",
            reason=reason,
            primary_provider=primary_provider,
        )
        return True, reason

    def evaluate_response_quality(
        self, prompt: str, response: str, provider: str, should_fallback_on_low_score: bool = True
    ) -> tuple[QualityScore, Optional[str]]:
        """
        Evaluate response quality and decide if fallback is needed.

        Args:
            prompt: Original prompt
            response: LLM response
            provider: Provider that generated response
            should_fallback_on_low_score: Whether to recommend fallback on low score

        Returns:
            (quality_score, fallback_reason or None)
        """
        quality_score = self.scorer.score_response(prompt, response, provider)

        # Check if fallback is needed
        fallback_reason = None

        if should_fallback_on_low_score:
            llm_config = self.policy_loader.get_llm_config()
            gatekeeper_config = llm_config.get("gatekeeper", {})
            quality_threshold = gatekeeper_config.get("quality_threshold", 70)

            if quality_score.total_score < quality_threshold:
                fallback_reason = (
                    f"quality_score_below_threshold "
                    f"(score={quality_score.total_score}, "
                    f"threshold={quality_threshold})"
                )

                self.logger.warning(
                    "GATEKEEPER_QUALITY_FALLBACK_RECOMMENDED",
                    provider=provider,
                    score=quality_score.total_score,
                    threshold=quality_threshold,
                    reason=fallback_reason,
                )

        return quality_score, fallback_reason


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """CLI interface for testing Gatekeeper"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Free Intelligence Gatekeeper - Quality Scoring CLI"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Score command
    score_parser = subparsers.add_parser("score", help="Score a response")
    score_parser.add_argument("prompt", help="Original prompt")
    score_parser.add_argument("response", help="LLM response")
    score_parser.add_argument("--provider", default="ollama", help="Provider name")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test with sample responses")

    args = parser.parse_args()

    scorer = QualityScorer()

    if args.command == "score":
        quality_score = scorer.score_response(args.prompt, args.response, args.provider)

        print(f"\n{'='*70}")
        print(f"Quality Score: {quality_score.total_score}/100")
        print(f"{'='*70}")
        print("\nBreakdown:")
        print(f"  Length:       {quality_score.length_score}/30")
        print(f"  Keywords:     {quality_score.keyword_score}/30")
        print(f"  Coherence:    {quality_score.coherence_score}/20")
        print(f"  Completeness: {quality_score.completeness_score}/20")
        print(f"\n{quality_score.explanation}")
        print(
            f"\nChecks passed: {sum(quality_score.checks_passed.values())}/{len(quality_score.checks_passed)}"
        )

    elif args.command == "test":
        # Test with sample responses
        test_cases = [
            ("Who is Alice?", "Alice is the protagonist.", "ollama"),
            (
                "Who is Alice?",
                "Alice is the protagonist of Alice in Wonderland, written by Lewis Carroll. She is a curious young girl who falls down a rabbit hole into a fantastical world. Throughout her adventures, she meets various eccentric characters and experiences many bizarre situations.",
                "ollama",
            ),
            ("What is 2+2?", "4", "ollama"),
        ]

        print(f"\n{'='*70}")
        print("Gatekeeper Quality Scorer - Test Cases")
        print(f"{'='*70}\n")

        for prompt, response, provider in test_cases:
            quality_score = scorer.score_response(prompt, response, provider)
            print(f"Prompt: {prompt}")
            print(f"Response: {response[:50]}...")
            print(f"Score: {quality_score.total_score}/100 - {quality_score.explanation}")
            print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
