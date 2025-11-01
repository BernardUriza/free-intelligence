"""
Test suite for IntakeCoach preset and JSON schema

Validates:
- YAML preset loading and structure
- JSON schema validation
- Urgency classification rules
- Required fields enforcement
"""

import json
import unittest
from pathlib import Path

import yaml


class TestIntakeCoachPreset(unittest.TestCase):
    """Test IntakeCoach YAML preset"""

    def setUp(self) -> None:
        """Load preset file"""
        preset_path = Path(__file__).parent.parent / "backend" / "prompts" / "intake_coach.yaml"
        with open(preset_path) as f:
            self.preset = yaml.safe_load(f)

    def test_preset_has_required_fields(self) -> None:
        """Test: Preset contains all required top-level fields"""
        required_fields = ["name", "version", "description", "provider", "model", "system_prompt"]

        for field in required_fields:
            self.assertIn(field, self.preset, f"Missing required field: {field}")

    def test_preset_name_and_version(self) -> None:
        """Test: Preset has correct name and version"""
        self.assertEqual(self.preset["name"], "IntakeCoach")
        self.assertIsNotNone(self.preset["version"])
        self.assertRegex(self.preset["version"], r"^\d+\.\d+\.\d+$")  # Semantic versioning

    def test_system_prompt_not_empty(self) -> None:
        """Test: System prompt is non-empty"""
        self.assertIsInstance(self.preset["system_prompt"], str)
        self.assertGreater(len(self.preset["system_prompt"]), 100)

    def test_urgency_rules_defined(self) -> None:
        """Test: Urgency classification rules exist"""
        self.assertIn("urgency_rules", self.preset)

        urgency_levels = ["CRITICAL", "HIGH", "MODERATE", "LOW"]
        for level in urgency_levels:
            self.assertIn(level, self.preset["urgency_rules"])

    def test_critical_urgency_keywords(self) -> None:
        """Test: CRITICAL urgency has proper keywords"""
        critical = self.preset["urgency_rules"]["CRITICAL"]

        self.assertIn("keywords", critical)
        keywords = critical["keywords"]

        # Must include life-threatening symptoms
        life_threatening = ["chest pain", "difficulty breathing", "severe bleeding"]
        for symptom in life_threatening:
            self.assertIn(symptom, keywords)

    def test_required_fields_list(self) -> None:
        """Test: Required fields are specified"""
        self.assertIn("required_fields", self.preset)

        required = self.preset["required_fields"]
        expected_required = ["name", "age_or_dob", "chief_complaint", "symptoms"]

        for field in expected_required:
            self.assertIn(field, required)

    def test_phi_redaction_enabled(self) -> None:
        """Test: PHI redaction is enabled"""
        self.assertIn("phi_redaction", self.preset)
        self.assertTrue(self.preset["phi_redaction"]["enabled"])

        fields_to_redact = self.preset["phi_redaction"]["fields_to_redact"]
        self.assertIn("name", fields_to_redact)
        self.assertIn("phone", fields_to_redact)
        self.assertIn("email", fields_to_redact)

    def test_llm_config_parameters(self) -> None:
        """Test: LLM configuration has valid parameters"""
        self.assertIn("llm_config", self.preset)

        config = self.preset["llm_config"]
        self.assertIn("max_tokens", config)
        self.assertIn("temperature", config)
        self.assertIn("timeout_seconds", config)

        # Validate ranges
        self.assertGreater(config["max_tokens"], 0)
        self.assertGreaterEqual(config["temperature"], 0.0)
        self.assertLessEqual(config["temperature"], 1.0)
        self.assertGreater(config["timeout_seconds"], 0)


class TestIntakeSchema(unittest.TestCase):
    """Test intake JSON schema"""

    def setUp(self) -> None:
        """Load schema file"""
        schema_path = Path(__file__).parent.parent / "backend" / "schemas" / "intake.schema.json"
        with open(schema_path) as f:
            self.schema = json.load(f)

    def test_schema_is_valid_json(self) -> None:
        """Test: Schema is valid JSON"""
        self.assertIsInstance(self.schema, dict)

    def test_schema_has_required_properties(self) -> None:
        """Test: Schema defines required properties"""
        self.assertIn("required", self.schema)

        required = self.schema["required"]
        expected = ["demographics", "chief_complaint", "symptoms", "urgency"]

        for field in expected:
            self.assertIn(field, required)

    def test_demographics_schema(self) -> None:
        """Test: Demographics has proper structure"""
        demographics = self.schema["properties"]["demographics"]

        self.assertEqual(demographics["type"], "object")
        self.assertIn("name", demographics["properties"])
        self.assertIn("age", demographics["properties"])

        # Name validation
        name_schema = demographics["properties"]["name"]
        self.assertEqual(name_schema["type"], "string")
        self.assertIn("minLength", name_schema)

        # Age validation
        age_schema = demographics["properties"]["age"]
        self.assertEqual(age_schema["type"], "integer")
        self.assertGreaterEqual(age_schema["minimum"], 0)
        self.assertLessEqual(age_schema["maximum"], 150)

    def test_symptoms_schema(self) -> None:
        """Test: Symptoms is array with required fields"""
        symptoms = self.schema["properties"]["symptoms"]

        self.assertEqual(symptoms["type"], "array")
        self.assertIn("minItems", symptoms)
        self.assertEqual(symptoms["minItems"], 1)

        # Symptom item schema
        item_schema = symptoms["items"]
        self.assertIn("required", item_schema)

        required_fields = item_schema["required"]
        self.assertIn("description", required_fields)
        self.assertIn("onset", required_fields)
        self.assertIn("severity", required_fields)

        # Severity must be 1-10
        severity = item_schema["properties"]["severity"]
        self.assertEqual(severity["minimum"], 1)
        self.assertEqual(severity["maximum"], 10)

    def test_urgency_schema(self) -> None:
        """Test: Urgency has level and reasoning"""
        urgency = self.schema["properties"]["urgency"]

        self.assertEqual(urgency["type"], "object")
        self.assertIn("required", urgency)

        required = urgency["required"]
        self.assertIn("level", required)
        self.assertIn("reasoning", required)

        # Level must be enum
        level_schema = urgency["properties"]["level"]
        self.assertEqual(level_schema["type"], "string")
        self.assertIn("enum", level_schema)

        valid_levels = level_schema["enum"]
        self.assertEqual(set(valid_levels), {"LOW", "MODERATE", "HIGH", "CRITICAL"})


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation with sample data"""

    def setUp(self) -> None:
        """Load schema"""
        schema_path = Path(__file__).parent.parent / "backend" / "schemas" / "intake.schema.json"
        with open(schema_path) as f:
            self.schema = json.load(f)

    def test_valid_intake_data(self) -> None:
        """Test: Valid intake data passes schema"""
        # Install jsonschema if available, otherwise skip
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        valid_data = {
            "demographics": {"name": "John Doe", "age": 45},
            "chief_complaint": "Chest pain for 2 hours",
            "symptoms": [{"description": "Chest pain", "onset": "2 hours ago", "severity": 8}],
            "urgency": {
                "level": "CRITICAL",
                "reasoning": "Chest pain requires immediate evaluation",
            },
        }

        # Should not raise exception
        jsonschema.validate(instance=valid_data, schema=self.schema)

    def test_invalid_urgency_level(self) -> None:
        """Test: Invalid urgency level fails validation"""
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        invalid_data = {
            "demographics": {"name": "John Doe", "age": 45},
            "chief_complaint": "Headache",
            "symptoms": [{"description": "Headache", "onset": "1 day", "severity": 5}],
            "urgency": {
                "level": "INVALID_LEVEL",  # Invalid!
                "reasoning": "Test",
            },
        }

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_data, schema=self.schema)


if __name__ == "__main__":
    unittest.main(verbosity=2)
