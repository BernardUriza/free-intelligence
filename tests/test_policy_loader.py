"""
Free Intelligence - Policy Loader Tests

Tests for backend/policy_loader.py
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from backend.policy_loader import PolicyLoader, PolicyValidationError


class TestPolicyLoader(unittest.TestCase):
    """Test policy loader"""

    def setUp(self):
        """Create temporary policy file for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.policy_path = Path(self.temp_dir) / "test_policy.yaml"

        # Valid policy for testing
        self.valid_policy = {
            "llm": {
                "primary_provider": "claude",
                "fallback_provider": "claude",
                "enable_offline": False,
                "providers": {
                    "claude": {
                        "model": "claude-3-5-sonnet-20241022",
                        "api_key_env": "CLAUDE_API_KEY",
                        "timeout_seconds": 30,
                        "max_tokens": 4096,
                        "temperature": 0.7,
                    },
                    "ollama": {
                        "base_url": "http://localhost:11434",
                        "model": "qwen2:7b-instruct-q4_0",
                        "timeout_seconds": 12,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                    },
                },
                "budgets": {
                    "max_cost_per_day": 10.0,
                    "max_requests_per_hour": 100,
                    "alert_threshold": 0.8,
                },
                "fallback_rules": [
                    {"condition": "timeout", "action": "use_fallback"},
                    {"condition": "rate_limit", "action": "exponential_backoff"},
                ],
            },
            "export": {
                "require_manifest": True,
                "compute_sha256": True,
                "allowed_formats": ["markdown", "json", "hdf5"],
            },
            "audit": {
                "log_all_operations": True,
                "retention_days": 90,
                "hash_payloads": True,
                "hash_results": True,
            },
            "metadata": {"version": "1.0.0", "last_updated": "2025-10-28", "owner": "Test User"},
        }

        # Write valid policy
        with open(self.policy_path, "w") as f:
            yaml.dump(self.valid_policy, f)

    def tearDown(self):
        """Clean up temp files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_valid_policy(self):
        """Test loading valid policy"""
        loader = PolicyLoader(self.policy_path)
        policy = loader.load()

        self.assertIsNotNone(policy)
        self.assertEqual(policy["llm"]["primary_provider"], "claude")

    def test_get_primary_provider(self):
        """Test getting primary provider"""
        loader = PolicyLoader(self.policy_path)
        loader.load()

        self.assertEqual(loader.get_primary_provider(), "claude")

    def test_get_fallback_provider(self):
        """Test getting fallback provider"""
        loader = PolicyLoader(self.policy_path)
        loader.load()

        self.assertEqual(loader.get_fallback_provider(), "claude")

    def test_get_provider_config(self):
        """Test getting provider configuration"""
        loader = PolicyLoader(self.policy_path)
        loader.load()

        claude_config = loader.get_provider_config("claude")
        self.assertEqual(claude_config["model"], "claude-3-5-sonnet-20241022")
        self.assertEqual(claude_config["timeout_seconds"], 30)

    def test_get_budgets(self):
        """Test getting budget configuration"""
        loader = PolicyLoader(self.policy_path)
        loader.load()

        budgets = loader.get_budgets()
        self.assertEqual(budgets["max_cost_per_day"], 10.0)
        self.assertEqual(budgets["max_requests_per_hour"], 100)

    def test_get_fallback_rules(self):
        """Test getting fallback rules"""
        loader = PolicyLoader(self.policy_path)
        loader.load()

        rules = loader.get_fallback_rules()
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["condition"], "timeout")
        self.assertEqual(rules[0]["action"], "use_fallback")

    def test_is_offline_enabled(self):
        """Test offline mode check"""
        loader = PolicyLoader(self.policy_path)
        loader.load()

        self.assertFalse(loader.is_offline_enabled())

    def test_missing_llm_section(self):
        """Test validation fails when llm section missing"""
        policy = self.valid_policy.copy()
        del policy["llm"]

        with open(self.policy_path, "w") as f:
            yaml.dump(policy, f)

        loader = PolicyLoader(self.policy_path)
        with self.assertRaises(PolicyValidationError) as cm:
            loader.load()

        self.assertIn("llm", str(cm.exception))

    def test_missing_primary_provider(self):
        """Test validation fails when primary_provider missing"""
        policy = self.valid_policy.copy()
        del policy["llm"]["primary_provider"]

        with open(self.policy_path, "w") as f:
            yaml.dump(policy, f)

        loader = PolicyLoader(self.policy_path)
        with self.assertRaises(PolicyValidationError) as cm:
            loader.load()

        self.assertIn("primary_provider", str(cm.exception))

    def test_invalid_primary_provider(self):
        """Test validation fails when primary_provider not in providers"""
        policy = self.valid_policy.copy()
        policy["llm"]["primary_provider"] = "nonexistent"

        with open(self.policy_path, "w") as f:
            yaml.dump(policy, f)

        loader = PolicyLoader(self.policy_path)
        with self.assertRaises(PolicyValidationError) as cm:
            loader.load()

        self.assertIn("nonexistent", str(cm.exception))

    def test_missing_export_section(self):
        """Test validation fails when export section missing"""
        policy = self.valid_policy.copy()
        del policy["export"]

        with open(self.policy_path, "w") as f:
            yaml.dump(policy, f)

        loader = PolicyLoader(self.policy_path)
        with self.assertRaises(PolicyValidationError) as cm:
            loader.load()

        self.assertIn("export", str(cm.exception))

    def test_missing_audit_section(self):
        """Test validation fails when audit section missing"""
        policy = self.valid_policy.copy()
        del policy["audit"]

        with open(self.policy_path, "w") as f:
            yaml.dump(policy, f)

        loader = PolicyLoader(self.policy_path)
        with self.assertRaises(PolicyValidationError) as cm:
            loader.load()

        self.assertIn("audit", str(cm.exception))

    def test_policy_not_found(self):
        """Test error when policy file doesn't exist"""
        loader = PolicyLoader("/nonexistent/policy.yaml")

        with self.assertRaises(FileNotFoundError):
            loader.load()

    def test_empty_policy_file(self):
        """Test error when policy file is empty"""
        empty_path = Path(self.temp_dir) / "empty.yaml"
        empty_path.write_text("")

        loader = PolicyLoader(empty_path)
        with self.assertRaises(PolicyValidationError) as cm:
            loader.load()

        self.assertIn("empty", str(cm.exception))

    def test_get_config_before_load(self):
        """Test error when accessing config before loading"""
        loader = PolicyLoader(self.policy_path)

        with self.assertRaises(RuntimeError) as cm:
            loader.get_llm_config()

        self.assertIn("not loaded", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
