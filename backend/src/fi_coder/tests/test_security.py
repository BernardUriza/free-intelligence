from __future__ import annotations

import unittest

from ..security.validator import SecurityValidator


class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.validator = SecurityValidator()

    def test_allowed_task(self):
        self.assertTrue(self.validator.validate_task_name("lint"))
        self.assertTrue(self.validator.validate_task_name("test"))

    def test_disallowed_task(self):
        self.assertFalse(self.validator.validate_task_name("rm -rf /"))

    def test_working_directory_validation(self):
        self.assertTrue(self.validator.validate_working_directory("/Users/bernardurizaorozco/Documents/free-intelligence"))
        self.assertFalse(self.validator.validate_working_directory("/tmp"))

    def test_parameter_validation(self):
        # Valid parameters
        self.assertTrue(self.validator.validate_parameters("lint", {"repo_root_path": "/tmp"}))

        # Invalid parameters with shell injection
        self.assertFalse(self.validator.validate_parameters("lint", {"args": "fix; rm -rf /"}))
        self.assertFalse(self.validator.validate_parameters("lint", {"args": "fix | cat"}))


if __name__ == "__main__":
    unittest.main()