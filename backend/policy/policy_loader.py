from __future__ import annotations

"""
Free Intelligence - Policy Loader

Loads and validates fi.policy.yaml configuration file.
Provides unified interface for accessing LLM policies, export policies, audit policies, etc.

Philosophy: Policy-driven configuration for provider-agnostic LLM routing.
"""

import threading
from pathlib import Path
from typing import Any, Optional

import yaml

from backend.logger import get_logger

logger = get_logger(__name__)


class PolicyValidationError(Exception):
    """Raised when policy validation fails"""

    pass


class PolicyLoader:
    """Loads and validates fi.policy.yaml"""

    def __init__(self, policy_path: Optional[str] = None):
        """
        Initialize policy loader.

        Args:
            policy_path: Path to fi.policy.yaml (defaults to config/fi.policy.yaml)
        """
        if policy_path is None:
            # Default: config/fi.policy.yaml relative to project root
            project_root = Path(__file__).parent.parent
            policy_path = project_root / "config" / "fi.policy.yaml"

        self.policy_path = Path(policy_path)
        self.policy: Optional[dict[str, Any]] = None
        self.logger = get_logger(self.__class__.__name__)

    def load(self) -> dict[str, Any]:
        """
        Load policy from YAML file.

        Returns:
            Dict with policy configuration

        Raises:
            FileNotFoundError: If policy file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid
            PolicyValidationError: If policy validation fails
        """
        if not self.policy_path.exists():
            self.logger.error("POLICY_FILE_NOT_FOUND", file_path=str(self.policy_path))
            raise FileNotFoundError(f"Policy file not found: {self.policy_path}")

        self.logger.info("POLICY_LOADING_STARTED", file_path=str(self.policy_path))

        try:
            with open(self.policy_path, encoding="utf-8") as f:
                policy = yaml.safe_load(f)

            if policy is None:
                raise PolicyValidationError("Policy file is empty")

            # Validate schema
            self._validate_policy(policy)

            self.policy = policy
            self.logger.info(
                "POLICY_LOADED_SUCCESSFULLY",
                file_path=str(self.policy_path),
                primary_provider=policy.get("llm", {}).get("primary_provider"),
            )

            return policy

        except yaml.YAMLError as e:
            self.logger.error("POLICY_YAML_PARSE_ERROR", error=str(e))
            raise
        except PolicyValidationError as e:
            self.logger.error("POLICY_VALIDATION_FAILED", error=str(e))
            raise

    def _validate_policy(self, policy: dict[str, Any]) -> None:
        """
        Validate policy schema and required fields.

        Args:
            policy: Policy dict to validate

        Raises:
            PolicyValidationError: If validation fails
        """
        # Check top-level sections
        required_sections = ["llm", "export", "audit", "metadata"]
        for section in required_sections:
            if section not in policy:
                raise PolicyValidationError(f"Missing required section: {section}")

        # Validate LLM section
        self._validate_llm_section(policy["llm"])

        # Validate export section
        self._validate_export_section(policy["export"])

        # Validate audit section
        self._validate_audit_section(policy["audit"])

        # Validate metadata section
        self._validate_metadata_section(policy["metadata"])

        self.logger.info("POLICY_VALIDATION_PASSED")

    def _validate_llm_section(self, llm: dict[str, Any]) -> None:
        """Validate LLM policy section"""
        required_fields = ["primary_provider", "fallback_provider", "providers"]
        for field in required_fields:
            if field not in llm:
                raise PolicyValidationError(f"Missing required LLM field: {field}")

        # Validate primary_provider is in providers
        primary = llm["primary_provider"]
        if primary not in llm["providers"]:
            raise PolicyValidationError(
                f"primary_provider '{primary}' not found in providers configuration"
            )

        # Validate fallback_provider is in providers
        fallback = llm["fallback_provider"]
        if fallback not in llm["providers"]:
            raise PolicyValidationError(
                f"fallback_provider '{fallback}' not found in providers configuration"
            )

        # Validate budgets
        if "budgets" in llm:
            budgets = llm["budgets"]
            if "max_cost_per_day" not in budgets:
                raise PolicyValidationError("Missing budgets.max_cost_per_day")
            if "max_requests_per_hour" not in budgets:
                raise PolicyValidationError("Missing budgets.max_requests_per_hour")

        # Validate fallback_rules
        if "fallback_rules" in llm:
            for rule in llm["fallback_rules"]:
                if "condition" not in rule or "action" not in rule:
                    raise PolicyValidationError(
                        "Each fallback_rule must have 'condition' and 'action'"
                    )

    def _validate_export_section(self, export: dict[str, Any]) -> None:
        """Validate export policy section"""
        required_fields = ["require_manifest", "compute_sha256", "allowed_formats"]
        for field in required_fields:
            if field not in export:
                raise PolicyValidationError(f"Missing required export field: {field}")

        # Validate allowed_formats is a list
        if not isinstance(export["allowed_formats"], list):
            raise PolicyValidationError("export.allowed_formats must be a list")

    def _validate_audit_section(self, audit: dict[str, Any]) -> None:
        """Validate audit policy section"""
        required_fields = ["log_all_operations", "retention_days", "hash_payloads", "hash_results"]
        for field in required_fields:
            if field not in audit:
                raise PolicyValidationError(f"Missing required audit field: {field}")

    def _validate_metadata_section(self, metadata: dict[str, Any]) -> None:
        """Validate metadata section"""
        required_fields = ["version", "last_updated", "owner"]
        for field in required_fields:
            if field not in metadata:
                raise PolicyValidationError(f"Missing required metadata field: {field}")

    def get_llm_config(self) -> dict[str, Any]:
        """
        Get LLM configuration section.

        Returns:
            Dict with LLM configuration

        Raises:
            RuntimeError: If policy not loaded
        """
        if self.policy is None:
            raise RuntimeError("Policy not loaded. Call load() first.")
        return self.policy["llm"]

    def get_primary_provider(self) -> str:
        """Get primary LLM provider name"""
        return self.get_llm_config()["primary_provider"]

    def get_fallback_provider(self) -> str:
        """Get fallback LLM provider name"""
        return self.get_llm_config()["fallback_provider"]

    def get_provider_config(self, provider_name: str) -> dict[str, Any]:
        """
        Get configuration for specific provider.

        Args:
            provider_name: Provider name (e.g., "claude", "ollama")

        Returns:
            Dict with provider configuration

        Raises:
            KeyError: If provider not found
        """
        llm_config = self.get_llm_config()
        providers = llm_config["providers"]

        if provider_name not in providers:
            raise KeyError(f"Provider '{provider_name}' not found in policy")

        return providers[provider_name]

    def get_budgets(self) -> dict[str, Any]:
        """Get budget configuration"""
        return self.get_llm_config().get("budgets", {})

    def get_fallback_rules(self) -> list[dict[str, str]]:
        """Get fallback rules"""
        return self.get_llm_config().get("fallback_rules", [])

    def get_export_config(self) -> dict[str, Any]:
        """Get export policy configuration"""
        if self.policy is None:
            raise RuntimeError("Policy not loaded. Call load() first.")
        return self.policy["export"]

    def get_audit_config(self) -> dict[str, Any]:
        """Get audit policy configuration"""
        if self.policy is None:
            raise RuntimeError("Policy not loaded. Call load() first.")
        return self.policy["audit"]

    def is_offline_enabled(self) -> bool:
        """Check if offline-first mode is enabled"""
        return self.get_llm_config().get("enable_offline", False)


# Singleton instance with thread-safe double-checked locking
_policy_loader: Optional[PolicyLoader] = None
_policy_loader_lock = threading.Lock()


def get_policy_loader(policy_path: Optional[str] = None) -> PolicyLoader:
    """
    Get singleton PolicyLoader instance (thread-safe).

    Uses double-checked locking pattern to ensure thread safety
    without performance penalty after initialization.

    Args:
        policy_path: Optional path to policy file (only used on first call)

    Returns:
        PolicyLoader instance

    Thread Safety:
        - Multiple threads can safely call this function concurrently
        - Only one instance will be created even under high concurrency
        - Lock is only acquired on first call (fast path for subsequent calls)
    """
    global _policy_loader

    # Fast path: check without lock (99.9% of calls)
    if _policy_loader is not None:
        return _policy_loader

    # Slow path: acquire lock and check again
    with _policy_loader_lock:
        # Double-check: another thread might have initialized while we waited
        if _policy_loader is None:
            logger.info("POLICY_LOADER_INITIALIZING", thread_id=threading.current_thread().name)
            _policy_loader = PolicyLoader(policy_path)
            _policy_loader.load()
            logger.info("POLICY_LOADER_INITIALIZED", thread_id=threading.current_thread().name)

    return _policy_loader


def reload_policy(policy_path: Optional[str] = None) -> PolicyLoader:
    """
    Force reload of policy (useful for testing or configuration changes).

    Thread-safe: Uses same lock as get_policy_loader().

    Args:
        policy_path: Optional path to policy file

    Returns:
        New PolicyLoader instance
    """
    global _policy_loader

    with _policy_loader_lock:
        logger.info("POLICY_RELOADING", thread_id=threading.current_thread().name)
        _policy_loader = PolicyLoader(policy_path)
        _policy_loader.load()
        logger.info("POLICY_RELOADED", thread_id=threading.current_thread().name)

    return _policy_loader


if __name__ == "__main__":
    """Demo script"""
    print("🔐 Free Intelligence - Policy Loader Demo")
    print("=" * 50)

    try:
        # Load policy
        print("\n1️⃣  Loading policy...")
        loader = get_policy_loader()
        print("   ✅ Policy loaded successfully")

        # Show primary provider
        print(f"\n2️⃣  Primary provider: {loader.get_primary_provider()}")
        print(f"   Fallback provider: {loader.get_fallback_provider()}")

        # Show Claude config
        print("\n3️⃣  Claude configuration:")
        claude_config = loader.get_provider_config("claude")
        print(f"   Model: {claude_config['model']}")
        print(f"   Timeout: {claude_config['timeout_seconds']}s")
        print(f"   Max tokens: {claude_config['max_tokens']}")

        # Show budgets
        print("\n4️⃣  Budget configuration:")
        budgets = loader.get_budgets()
        print(f"   Max cost per day: ${budgets['max_cost_per_day']}")
        print(f"   Max requests per hour: {budgets['max_requests_per_hour']}")

        # Show fallback rules
        print("\n5️⃣  Fallback rules:")
        rules = loader.get_fallback_rules()
        for i, rule in enumerate(rules, 1):
            print(f"   {i}. {rule['condition']} → {rule['action']}")

        # Show offline mode
        print(
            f"\n6️⃣  Offline mode: {'✅ Enabled' if loader.is_offline_enabled() else '❌ Disabled'}"
        )

        print("\n" + "=" * 50)
        print("Demo complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
