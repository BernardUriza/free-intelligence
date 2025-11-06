from __future__ import annotations

"""
Policy Enforcer — Runtime Policy Guards
Card: FI-POLICY-STR-001

Loads and enforces policies from config/fi.policy.yaml
Provides guard functions for sovereignty, privacy, cost, and feature flags
"""

import hashlib
import re
from pathlib import Path
from typing import Any, Optional

import yaml

from backend.logger import get_logger

logger = get_logger(__name__)


class PolicyViolation(Exception):
    """Raised when a policy rule is violated"""

    def __init__(self, rule: str, message: str, metadata: dict[str, Optional[Any]] = None):
        self.rule = rule
        self.message = message
        self.metadata = metadata or {}
        super().__init__(f"Policy violation [{rule}]: {message}")


class PolicyEnforcer:
    """
    Runtime policy enforcement engine

    Loads policy from config/fi.policy.yaml and provides guard functions:
    - check_egress(url): Blocks external egress if sovereignty.egress.default = deny
    - check_cost(cents): Blocks if exceeds monthly budget
    - check_phi(text): Returns true if PHI patterns detected
    - redact(text): Masks PII/PHI according to redaction_style.yaml
    - check_timeline_auto(): Returns true if timeline.auto.enabled
    - check_agents_enabled(): Returns true if agents.enabled
    """

    def __init__(
        self,
        policy_path: str = "config/fi.policy.yaml",
        redaction_path: str = "config/redaction_style.yaml",
    ):
        self.policy_path = Path(policy_path)
        self.redaction_path = Path(redaction_path)

        # Load policies on init
        self.policy = self._load_yaml(self.policy_path)
        self.redaction_config = self._load_yaml(self.redaction_path)

        # Compile regex patterns for performance
        self._compiled_patterns = {}
        if self.redaction_config:
            for name, pattern_config in self.redaction_config.get("patterns", {}).items():
                if pattern_config.get("enabled", True):
                    self._compiled_patterns[name] = {
                        "regex": re.compile(pattern_config["regex"]),
                        "replacement": pattern_config["replacement"],
                    }

            # PHI patterns
            for name, pattern_config in self.redaction_config.get("phi", {}).items():
                if pattern_config.get("enabled", True):
                    self._compiled_patterns[f"phi_{name}"] = {
                        "regex": re.compile(pattern_config["regex"]),
                        "replacement": pattern_config["replacement"],
                    }

        logger.info(
            f"PolicyEnforcer loaded: {self.policy.get('version', 'unknown')} "
            + f"({len(self._compiled_patterns)} redaction patterns)"
        )

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load YAML file with error handling"""
        if not path.exists():
            logger.warning(f"Policy file not found: {path}")
            return {}

        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return {}

    def get_policy_digest(self) -> str:
        """
        Compute SHA256 hash of policy file for manifest/audit trail
        """
        if not self.policy_path.exists():
            return "no-policy-file"

        with open(self.policy_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    # === Sovereignty Guards ===

    def check_egress(self, url: str, run_id: Optional[str] = None) -> None:
        """
        Check if external egress is allowed

        Supports allowlist when default=deny.
        Allowlist entries can be:
        - Domain: "api.anthropic.com"
        - Host:port: "127.0.0.1:11434", "localhost:11434"
        - URL prefix: "https://api.anthropic.com"

        Args:
            url: Target URL for egress
            run_id: Optional run ID for logging

        Raises:
            PolicyViolation: If egress is denied by policy
        """
        from urllib.parse import urlparse

        egress_policy = self.policy.get("sovereignty", {}).get("egress", {})
        default_action = egress_policy.get("default", "allow")
        allowlist = egress_policy.get("allowlist", [])

        if default_action == "deny":
            # Parse URL to extract domain/host
            parsed = urlparse(url)
            host = parsed.netloc.lower() if parsed.netloc else ""
            domain = parsed.hostname.lower() if parsed.hostname else ""

            # Check if URL/host is in allowlist (strict matching)
            allowed = False
            for entry in allowlist:
                entry_lower = entry.lower().lstrip(".")

                # Wildcard match: .example.com matches *.example.com
                if entry.startswith("."):
                    if domain == entry_lower or domain.endswith("." + entry_lower):
                        allowed = True
                        logger.debug(f"Egress allowed by wildcard: {url} (matched: {entry})")
                        break
                else:
                    # Exact match: host or domain must match exactly
                    if host == entry_lower or domain == entry_lower:
                        allowed = True
                        logger.debug(f"Egress allowed by exact match: {url} (matched: {entry})")
                        break

            if not allowed:
                metadata = {"url": url, "host": host, "run_id": run_id, "allowlist": allowlist}
                logger.warning(f"Egress blocked by policy: {url} (run_id={run_id})")
                raise PolicyViolation(
                    rule="sovereignty.egress",
                    message=f"External egress denied by policy: {url}",
                    metadata=metadata,
                )
        else:
            logger.debug(f"Egress allowed (default=allow): {url}")

    # === Privacy Guards ===

    def check_phi(self, text: str) -> bool:
        """
        Check if text contains PHI patterns

        Returns:
            True if PHI detected, False otherwise
        """
        phi_enabled = self.policy.get("privacy", {}).get("phi", {}).get("enabled", False)

        if not phi_enabled:
            return False

        # Check PHI-specific patterns
        for name, pattern in self._compiled_patterns.items():
            if name.startswith("phi_") and pattern["regex"].search(text):
                logger.debug(f"PHI detected: {name}")
                return True

        return False

    def redact(self, text: str) -> str:
        """
        Redact PII/PHI from text according to redaction_style.yaml

        Applies patterns in order: email, phone, CURP, RFC, SSN, credit card, PHI

        Args:
            text: Input text to redact

        Returns:
            Redacted text with [REDACTED_X] placeholders
        """
        if not text:
            return text

        redacted = text

        # Apply all enabled patterns
        for name, pattern in self._compiled_patterns.items():
            redacted = pattern["regex"].sub(pattern["replacement"], redacted)

        # Apply stop terms
        stop_terms = self.redaction_config.get("stop_terms", [])
        for term in stop_terms:
            # Case-insensitive whole-word replacement
            redacted = re.sub(
                rf"\b{re.escape(term)}\b",
                self.redaction_config.get("replacement", "[REDACTED]"),
                redacted,
                flags=re.IGNORECASE,
            )

        return redacted

    # === Cost Guards ===

    def check_cost(self, cents: int, run_id: Optional[str] = None) -> None:
        """
        Check if cost exceeds monthly budget

        Args:
            cents: Cost in cents (1 USD = 100 cents)
            run_id: Optional run ID for logging

        Raises:
            PolicyViolation: If cost exceeds llm.budgets.monthly_usd
        """
        budget_usd = self.policy.get("llm", {}).get("budgets", {}).get("monthly_usd", 0)
        budget_cents = budget_usd * 100

        if cents > budget_cents:
            metadata = {"cents": cents, "budget_cents": budget_cents, "run_id": run_id}
            logger.warning(f"Cost exceeds budget: {cents} > {budget_cents} (run_id={run_id})")
            raise PolicyViolation(
                rule="llm.budgets",
                message=f"Cost {cents}¢ exceeds monthly budget {budget_cents}¢",
                metadata=metadata,
            )

        logger.debug(f"Cost within budget: {cents}¢ <= {budget_cents}¢")

    # === Feature Flags ===

    def check_timeline_auto(self) -> bool:
        """
        Check if timeline.auto is enabled

        Returns:
            True if timeline.auto.enabled = true
        """
        return self.policy.get("timeline", {}).get("auto", {}).get("enabled", False)

    def check_agents_enabled(self) -> bool:
        """
        Check if agents are enabled

        Returns:
            True if agents.enabled = true
        """
        return self.policy.get("agents", {}).get("enabled", False)

    # === Utility ===

    def get_policy(self, key_path: str, default: Any = None) -> Any:
        """
        Get policy value by dot-separated key path

        Example:
            get_policy("llm.budgets.monthly_usd") → 200

        Args:
            key_path: Dot-separated path (e.g., "sovereignty.egress.default")
            default: Default value if not found

        Returns:
            Policy value or default
        """
        keys = key_path.split(".")
        value = self.policy

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default

        return value if value is not None else default

    def log_violation(self, rule: str, metadata: dict[str, Optional[Any]] = None):
        """
        Log policy violation for audit trail

        Args:
            rule: Policy rule violated (e.g., "sovereignty.egress")
            metadata: Additional metadata for logging
        """
        log_data = {"event": "policy_violation", "rule": rule, **(metadata or {})}
        logger.warning(f"Policy violation logged: {log_data}")


# Global singleton instance
_policy_enforcer: Optional[PolicyEnforcer] = None


def get_policy_enforcer() -> PolicyEnforcer:
    """
    Get or create global PolicyEnforcer singleton

    Returns:
        PolicyEnforcer instance
    """
    global _policy_enforcer

    if _policy_enforcer is None:
        _policy_enforcer = PolicyEnforcer()

    return _policy_enforcer


# Convenience functions for direct import


def check_egress(url: str, run_id: Optional[str] = None):
    """Check if external egress is allowed (raises PolicyViolation if denied)"""
    return get_policy_enforcer().check_egress(url, run_id)


def check_cost(cents: int, run_id: Optional[str] = None):
    """Check if cost exceeds budget (raises PolicyViolation if exceeded)"""
    return get_policy_enforcer().check_cost(cents, run_id)


def check_phi(text: str) -> bool:
    """Check if text contains PHI patterns"""
    return get_policy_enforcer().check_phi(text)


def redact(text: str) -> str:
    """Redact PII/PHI from text"""
    return get_policy_enforcer().redact(text)


def check_timeline_auto() -> bool:
    """Check if timeline.auto is enabled"""
    return get_policy_enforcer().check_timeline_auto()


def check_agents_enabled() -> bool:
    """Check if agents are enabled"""
    return get_policy_enforcer().check_agents_enabled()
