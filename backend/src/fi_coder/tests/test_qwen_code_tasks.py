from __future__ import annotations

import unittest
from unittest.mock import patch

from ..config.policies import COMMAND_TEMPLATES, TASK_CATALOG
from ..execution.executor import TaskExecutor
from ..models.task import Task
from ..security.validator import SecurityValidator
from ..storage.task_storage import TaskStorage


class TestQwenCodeTasks(unittest.TestCase):
    def setUp(self):
        self.storage = TaskStorage()
        self.security = SecurityValidator()
        self.executor = TaskExecutor(self.storage, self.security)

    def test_qwen_code_tasks_in_catalog(self):
        """Test that qwen-code specialized tasks are in catalog."""
        expected_tasks = [
            "fix_lint", "refactor", "fix_and_test", 
            "analyze_code", "pipeline_fix_lint_test"
        ]
        for task in expected_tasks:
            self.assertIn(task, TASK_CATALOG)

    def test_task_parameters(self):
        """Test task parameter handling."""
        task = Task(
            name="fix_lint", 
            parameters={
                "repo_root_path": "/repo",
                "modules": "admin auth"
            }
        )
        self.assertEqual(task.parameters["modules"], "admin auth")

    def test_task_command_resolution(self):
        """Test that commands are resolved from catalog."""
        # This would be tested in integration, but here we check catalog
        command = COMMAND_TEMPLATES["fix_lint"]
        self.assertIn("qwen-code", command)
        self.assertIn("{modules}", command)

    # Negative tests
    def test_invalid_task_name(self):
        """Test that invalid task names are rejected."""
        task = Task(name="invalid_task", parameters={})
        with self.assertRaises(ValueError):
            self.executor.submit_task(task)

    def test_missing_required_parameters(self):
        """Test that tasks with missing required parameters are rejected."""
        task = Task(name="fix_lint", parameters={"repo_root_path": "/repo"})  # Missing modules
        with self.assertRaises(ValueError):
            self.executor.submit_task(task)

    def test_shell_injection_prevention(self):
        """Test that shell injection attempts are blocked."""
        task = Task(
            name="qwen-code",
            parameters={
                "repo_root_path": "/repo",
                "args": "fix; rm -rf /"  # Injection attempt
            }
        )
        with self.assertRaises(ValueError):
            self.executor.submit_task(task)

    def test_path_traversal_prevention(self):
        """Test that path traversal is blocked."""
        task = Task(
            name="fix_lint",
            parameters={
                "repo_root_path": "/repo/../../../etc",
                "modules": "admin"
            }
        )
        with self.assertRaises(ValueError):
            self.executor.submit_task(task)

    def test_forbidden_directory_access(self):
        """Test that access to forbidden directories is blocked."""
        task = Task(
            name="fix_lint",
            parameters={
                "repo_root_path": "/repo",
                "modules": "storage"  # Forbidden
            }
        )
        with self.assertRaises(ValueError):
            self.executor.submit_task(task)

    @patch('fi_coder.execution.executor.TaskExecutor._calculate_fingerprint')
    def test_execution_fingerprint_created(self, mock_fingerprint):
        """Test that execution fingerprint is created before execution."""
        mock_fingerprint.return_value = None
        task = Task(
            name="lint",
            parameters={"repo_root_path": "/repo"}
        )
        # This would normally submit, but we mock to avoid actual execution
        # In real test, check that fingerprint is set
        pass  # Placeholder for integration test


if __name__ == "__main__":
    unittest.main()