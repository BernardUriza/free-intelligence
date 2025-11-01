"""
Test for Case 31 pediatric validator crash fix.

Verifies that None values in output['notes'] don't cause crashes.
"""
import unittest

from backend.medical_validators import PediatricValidator


class TestPediatricCrashFix(unittest.TestCase):
    """Test Case 31 fix: None guards in pediatric validator"""

    def setUp(self) -> None:
        self.validator = PediatricValidator()

    def test_notes_is_none(self) -> None:
        """Test: notes field is None (not just missing)"""
        output = {
            "notes": None  # THIS CAUSED CRASH IN CASE 31
        }
        case_prompt = "My 4-year-old has fever of 103F for 2 days with ear pain."

        # Should not crash
        result = self.validator.validate_pediatric_response(output, case_prompt)

        # Should pass (no contraindications)
        self.assertTrue(result.is_safe)
        self.assertEqual(result.score, 100.0)
        self.assertIn("Pediatric safety OK", result.reason)

    def test_notes_is_empty_string(self) -> None:
        """Test: notes field is empty string"""
        output = {"notes": ""}
        case_prompt = "My 4-year-old has fever."

        result = self.validator.validate_pediatric_response(output, case_prompt)
        self.assertTrue(result.is_safe)
        self.assertEqual(result.score, 100.0)

    def test_notes_missing(self) -> None:
        """Test: notes field is missing entirely"""
        output = {}
        case_prompt = "My 4-year-old has fever."

        result = self.validator.validate_pediatric_response(output, case_prompt)
        self.assertTrue(result.is_safe)
        self.assertEqual(result.score, 100.0)

    def test_notes_valid_with_contraindication(self) -> None:
        """Test: notes field has contraindicated drug"""
        output = {"notes": "Recommend ciprofloxacin 250mg PO BID for UTI"}
        case_prompt = "My 5-year-old daughter has a UTI"

        result = self.validator.validate_pediatric_response(output, case_prompt)
        self.assertFalse(result.is_safe)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.severity, "BLOCKER")
        self.assertIn("cipro", result.reason.lower())
        self.assertIn("contraindicated", result.reason.lower())


if __name__ == "__main__":
    unittest.main()
