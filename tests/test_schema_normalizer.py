"""
Test suite for schema_normalizer.py

Validates null → [] conversions for array fields
"""
import os
import sys
import unittest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from schema_normalizer import normalize_intake_output, normalize_output


class TestSchemaNoralizer(unittest.TestCase):
    """Test schema normalizer functions"""

    # Generic normalize_output tests

    def test_null_to_array(self) -> None:
        """Test: null → [] for array fields"""
        schema = {"type": "object", "properties": {"items": {"type": "array"}}}
        output = {"items": None}

        normalized = normalize_output(output, schema)

        self.assertEqual(normalized["items"], [])

    def test_null_to_object(self) -> None:
        """Test: null → {} for object fields"""
        schema = {"type": "object", "properties": {"metadata": {"type": "object"}}}
        output = {"metadata": None}

        normalized = normalize_output(output, schema)

        self.assertEqual(normalized["metadata"], {})

    def test_array_type_with_null_union(self) -> None:
        """Test: ["array", "null"] type spec"""
        schema = {"type": "object", "properties": {"tags": {"type": ["array", "null"]}}}
        output = {"tags": None}

        normalized = normalize_output(output, schema)

        self.assertEqual(normalized["tags"], [])

    def test_missing_required_field_array(self) -> None:
        """Test: Add missing required array field"""
        schema = {
            "type": "object",
            "properties": {"items": {"type": "array"}},
            "required": ["items"],
        }
        output = {}

        normalized = normalize_output(output, schema)

        self.assertIn("items", normalized)
        self.assertEqual(normalized["items"], [])

    def test_missing_required_field_object(self) -> None:
        """Test: Add missing required object field"""
        schema = {
            "type": "object",
            "properties": {"metadata": {"type": "object"}},
            "required": ["metadata"],
        }
        output = {}

        normalized = normalize_output(output, schema)

        self.assertIn("metadata", normalized)
        self.assertEqual(normalized["metadata"], {})

    def test_nested_object_normalization(self) -> None:
        """Test: Recursively normalize nested objects"""
        schema = {
            "type": "object",
            "properties": {
                "parent": {"type": "object", "properties": {"child_array": {"type": "array"}}}
            },
        }
        output = {"parent": {"child_array": None}}

        normalized = normalize_output(output, schema)

        self.assertEqual(normalized["parent"]["child_array"], [])

    def test_preserve_valid_values(self) -> None:
        """Test: Don't modify valid values"""
        schema = {
            "type": "object",
            "properties": {"items": {"type": "array"}, "count": {"type": "integer"}},
        }
        output = {"items": ["a", "b"], "count": 5}

        normalized = normalize_output(output, schema)

        self.assertEqual(normalized["items"], ["a", "b"])
        self.assertEqual(normalized["count"], 5)

    # IntakeCoach-specific normalize_intake_output tests

    def test_intake_symptoms_null_to_array(self) -> None:
        """Test: symptoms null → []"""
        output = {
            "demographics": {},
            "chief_complaint": None,
            "symptoms": None,  # Should become []
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "LOW",
        }

        normalized = normalize_intake_output(output)

        self.assertEqual(normalized["symptoms"], [])

    def test_intake_medical_history_allergies_null(self) -> None:
        """Test: medical_history.allergies null → []"""
        output = {
            "demographics": {},
            "symptoms": [],
            "medical_history": {
                "allergies": None,  # Should become []
                "medications": [],
                "conditions": [],
            },
            "urgency": "LOW",
        }

        normalized = normalize_intake_output(output)

        self.assertEqual(normalized["medical_history"]["allergies"], [])

    def test_intake_medical_history_medications_null(self) -> None:
        """Test: medical_history.medications null → []"""
        output = {
            "demographics": {},
            "symptoms": [],
            "medical_history": {
                "allergies": [],
                "medications": None,  # Should become []
                "conditions": [],
            },
            "urgency": "LOW",
        }

        normalized = normalize_intake_output(output)

        self.assertEqual(normalized["medical_history"]["medications"], [])

    def test_intake_medical_history_conditions_null(self) -> None:
        """Test: medical_history.conditions null → []"""
        output = {
            "demographics": {},
            "symptoms": [],
            "medical_history": {
                "allergies": [],
                "medications": [],
                "conditions": None,  # Should become []
            },
            "urgency": "LOW",
        }

        normalized = normalize_intake_output(output)

        self.assertEqual(normalized["medical_history"]["conditions"], [])

    def test_intake_case_7_scenario(self) -> None:
        """Test: Case 7 scenario (truncated medical_history)"""
        output = {
            "demographics": {"name": None, "age": 28, "gender": None, "contact": None},
            "chief_complaint": None,
            "symptoms": [],
            "medical_history": {
                "allergies": ["penicillin"],
                "medications": None,  # TRUNCATED
                "conditions": None,  # TRUNCATED
            },
            "urgency": None,
            "notes": None,
        }

        normalized = normalize_intake_output(output)

        # Check that truncated fields are fixed
        self.assertEqual(normalized["medical_history"]["medications"], [])
        self.assertEqual(normalized["medical_history"]["conditions"], [])

        # Check that valid data is preserved
        self.assertEqual(normalized["medical_history"]["allergies"], ["penicillin"])
        self.assertEqual(normalized["demographics"]["age"], 28)

    def test_intake_missing_medical_history(self) -> None:
        """Test: Missing medical_history object"""
        output = {
            "demographics": {},
            "symptoms": [],
            "urgency": "LOW",
            # medical_history is missing
        }

        normalized = normalize_intake_output(output)

        self.assertIn("medical_history", normalized)
        self.assertEqual(normalized["medical_history"]["allergies"], [])
        self.assertEqual(normalized["medical_history"]["medications"], [])
        self.assertEqual(normalized["medical_history"]["conditions"], [])

    def test_intake_medical_history_null(self) -> None:
        """Test: medical_history is null"""
        output = {
            "demographics": {},
            "symptoms": [],
            "medical_history": None,  # Null object
            "urgency": "LOW",
        }

        normalized = normalize_intake_output(output)

        self.assertIn("medical_history", normalized)
        self.assertEqual(normalized["medical_history"]["allergies"], [])
        self.assertEqual(normalized["medical_history"]["medications"], [])
        self.assertEqual(normalized["medical_history"]["conditions"], [])

    def test_intake_missing_medications_field(self) -> None:
        """Test: medications field completely missing"""
        output = {
            "demographics": {},
            "symptoms": [],
            "medical_history": {
                "allergies": [],
                # medications missing
                "conditions": [],
            },
            "urgency": "LOW",
        }

        normalized = normalize_intake_output(output)

        self.assertIn("medications", normalized["medical_history"])
        self.assertEqual(normalized["medical_history"]["medications"], [])

    def test_intake_preserve_valid_arrays(self) -> None:
        """Test: Don't modify valid array values"""
        output = {
            "demographics": {},
            "symptoms": ["headache", "nausea"],
            "medical_history": {
                "allergies": ["penicillin"],
                "medications": ["aspirin"],
                "conditions": ["hypertension"],
            },
            "urgency": "MODERATE",
        }

        normalized = normalize_intake_output(output)

        # All arrays should be preserved
        self.assertEqual(normalized["symptoms"], ["headache", "nausea"])
        self.assertEqual(normalized["medical_history"]["allergies"], ["penicillin"])
        self.assertEqual(normalized["medical_history"]["medications"], ["aspirin"])
        self.assertEqual(normalized["medical_history"]["conditions"], ["hypertension"])


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
