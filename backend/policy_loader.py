"""
Free Intelligence - Policy Loader

Loads and validates fi.policy.yaml configuration file.
Provides unified interface for accessing LLM policies, export policies, audit policies, etc.

Philosophy: Policy-driven configuration for provider-agnostic LLM routing.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
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
        self.policy: Optional[Dict[str, Any]] = None
        self.logger = get_logger(self.__class__.__name__)

    def load(self) -> Dict[str, Any]:
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
            self.logger.error("POLICY_FILE_NOT_FOUND", path=str(self.policy_path))
            raise FileNotFoundError(f"Policy file not found: {self.policy_path}")

        self.logger.info("POLICY_LOADING_STARTED", path=str(self.policy_path))

        try:
            with open(self.policy_path, 'r', encoding='utf-8') as f:
                policy = yaml.safe_load(f)

            if policy is None:
                raise PolicyValidationError("Policy file is empty")

            # Validate schema
            self._validate_policy(policy)

            self.policy = policy
            self.logger.info("POLICY_LOADED_SUCCESSFULLY",
                           path=str(self.policy_path),
                           primary_provider=policy.get('llm', {}).get('primary_provider'))

            return policy

        except yaml.YAMLError as e:
            self.logger.error("POLICY_YAML_PARSE_ERROR", error=str(e), path=str(self.policy_path))
            raise
        except PolicyValidationError as e:
            self.logger.error("POLICY_VALIDATION_FAILED", error=str(e))
            raise

    def _validate_policy(self, policy: Dict[str, Any]) -> None:
        """
        Validate policy schema and required fields.

        Args:
            policy: Policy dict to validate

        Raises:
            PolicyValidationError: If validation fails
        """
        # Check top-level sections
        required_sections = ['llm', 'export', 'audit', 'metadata']
        for section in required_sections:
            if section not in policy:
                raise PolicyValidationError(f"Missing required section: {section}")

        # Validate LLM section
        self._validate_llm_section(policy['llm'])

        # Validate export section
        self._validate_export_section(policy['export'])

        # Validate audit section
        self._validate_audit_section(policy['audit'])

        # Validate metadata section
        self._validate_metadata_section(policy['metadata'])

        self.logger.info("POLICY_VALIDATION_PASSED")

    def _validate_llm_section(self, llm: Dict[str, Any]) -> None:
        """Validate LLM policy section"""
        required_fields = ['primary_provider', 'fallback_provider', 'providers']
        for field in required_fields:
            if field not in llm:
                raise PolicyValidationError(f"Missing required LLM field: {field}")

        # Validate primary_provider is in providers
        primary = llm['primary_provider']
        if primary not in llm['providers']:
            raise PolicyValidationError(
                f"primary_provider '{primary}' not found in providers configuration"
            )

        # Validate fallback_provider is in providers
        fallback = llm['fallback_provider']
        if fallback not in llm['providers']:
            raise PolicyValidationError(
                f"fallback_provider '{fallback}' not found in providers configuration"
            )

        # Validate budgets
        if 'budgets' in llm:
            budgets = llm['budgets']
            if 'max_cost_per_day' not in budgets:
                raise PolicyValidationError("Missing budgets.max_cost_per_day")
            if 'max_requests_per_hour' not in budgets:
                raise PolicyValidationError("Missing budgets.max_requests_per_hour")

        # Validate fallback_rules
        if 'fallback_rules' in llm:
            for rule in llm['fallback_rules']:
                if 'condition' not in rule or 'action' not in rule:
                    raise PolicyValidationError(
                        "Each fallback_rule must have 'condition' and 'action'"
                    )

    def _validate_export_section(self, export: Dict[str, Any]) -> None:
        """Validate export policy section"""
        required_fields = ['require_manifest', 'compute_sha256', 'allowed_formats']
        for field in required_fields:
            if field not in export:
                raise PolicyValidationError(f"Missing required export field: {field}")

        # Validate allowed_formats is a list
        if not isinstance(export['allowed_formats'], list):
            raise PolicyValidationError("export.allowed_formats must be a list")

    def _validate_audit_section(self, audit: Dict[str, Any]) -> None:
        """Validate audit policy section"""
        required_fields = ['log_all_operations', 'retention_days', 'hash_payloads', 'hash_results']
        for field in required_fields:
            if field not in audit:
                raise PolicyValidationError(f"Missing required audit field: {field}")

    def _validate_metadata_section(self, metadata: Dict[str, Any]) -> None:
        """Validate metadata section"""
        required_fields = ['version', 'last_updated', 'owner']
        for field in required_fields:
            if field not in metadata:
                raise PolicyValidationError(f"Missing required metadata field: {field}")

    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration section.

        Returns:
            Dict with LLM configuration

        Raises:
            RuntimeError: If policy not loaded
        """
        if self.policy is None:
            raise RuntimeError("Policy not loaded. Call load() first.")
        return self.policy['llm']

    def get_primary_provider(self) -> str:
        """Get primary LLM provider name"""
        return self.get_llm_config()['primary_provider']

    def get_fallback_provider(self) -> str:
        """Get fallback LLM provider name"""
        return self.get_llm_config()['fallback_provider']

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
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
        providers = llm_config['providers']

        if provider_name not in providers:
            raise KeyError(f"Provider '{provider_name}' not found in policy")

        return providers[provider_name]

    def get_budgets(self) -> Dict[str, Any]:
        """Get budget configuration"""
        return self.get_llm_config().get('budgets', {})

    def get_fallback_rules(self) -> List[Dict[str, str]]:
        """Get fallback rules"""
        return self.get_llm_config().get('fallback_rules', [])

    def get_export_config(self) -> Dict[str, Any]:
        """Get export policy configuration"""
        if self.policy is None:
            raise RuntimeError("Policy not loaded. Call load() first.")
        return self.policy['export']

    def get_audit_config(self) -> Dict[str, Any]:
        """Get audit policy configuration"""
        if self.policy is None:
            raise RuntimeError("Policy not loaded. Call load() first.")
        return self.policy['audit']

    def is_offline_enabled(self) -> bool:
        """Check if offline-first mode is enabled"""
        return self.get_llm_config().get('enable_offline', False)


# Singleton instance
_policy_loader: Optional[PolicyLoader] = None


def get_policy_loader(policy_path: Optional[str] = None) -> PolicyLoader:
    """
    Get singleton PolicyLoader instance.

    Args:
        policy_path: Optional path to policy file (only used on first call)

    Returns:
        PolicyLoader instance
    """
    global _policy_loader

    if _policy_loader is None:
        _policy_loader = PolicyLoader(policy_path)
        _policy_loader.load()

    return _policy_loader


def reload_policy(policy_path: Optional[str] = None) -> PolicyLoader:
    """
    Force reload of policy (useful for testing or configuration changes).

    Args:
        policy_path: Optional path to policy file

    Returns:
        New PolicyLoader instance
    """
    global _policy_loader
    _policy_loader = PolicyLoader(policy_path)
    _policy_loader.load()
    return _policy_loader


if __name__ == "__main__":
    """Demo script"""
    print("🔐 Free Intelligence - Policy Loader Demo")
    print("=" * 50)

    try:
        # Load policy
        print("\n1️⃣  Loading policy...")
        loader = get_policy_loader()
        print(f"   ✅ Policy loaded successfully")

        # Show primary provider
        print(f"\n2️⃣  Primary provider: {loader.get_primary_provider()}")
        print(f"   Fallback provider: {loader.get_fallback_provider()}")

        # Show Claude config
        print(f"\n3️⃣  Claude configuration:")
        claude_config = loader.get_provider_config('claude')
        print(f"   Model: {claude_config['model']}")
        print(f"   Timeout: {claude_config['timeout_seconds']}s")
        print(f"   Max tokens: {claude_config['max_tokens']}")

        # Show budgets
        print(f"\n4️⃣  Budget configuration:")
        budgets = loader.get_budgets()
        print(f"   Max cost per day: ${budgets['max_cost_per_day']}")
        print(f"   Max requests per hour: {budgets['max_requests_per_hour']}")

        # Show fallback rules
        print(f"\n5️⃣  Fallback rules:")
        rules = loader.get_fallback_rules()
        for i, rule in enumerate(rules, 1):
            print(f"   {i}. {rule['condition']} → {rule['action']}")

        # Show offline mode
        print(f"\n6️⃣  Offline mode: {'✅ Enabled' if loader.is_offline_enabled() else '❌ Disabled'}")

        print("\n" + "=" * 50)
        print("Demo complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
