#!/usr/bin/env python3
"""
Tests for IntakeCoach preset

Validates:
1. Preset loading from YAML
2. JSON Schema validation
3. 10 test prompts → 0 validation errors
4. Cache key computation
5. LLM integration

File: tests/test_intake.py
Created: 2025-10-28
"""

import json
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import jsonschema

from backend.preset_loader import get_preset_loader


class TestPresetLoader(unittest.TestCase):
    """Test PresetLoader basic functionality"""

    def setUp(self):
        self.loader = get_preset_loader()

    def test_load_intake_coach_preset(self):
        """Test loading intake_coach.yaml"""
        preset = self.loader.load_preset("intake_coach")

        # Verify basic fields
        self.assertEqual(preset.preset_id, "intake_coach")
        self.assertEqual(preset.version, "1.0.0")
        self.assertIn("intake", preset.description.lower())

        # Verify LLM config
        self.assertEqual(preset.provider, "ollama")
        self.assertEqual(preset.model, "qwen2.5:7b-instruct-q4_0")
        self.assertEqual(preset.temperature, 0.3)
        self.assertEqual(preset.max_tokens, 2048)
        self.assertFalse(preset.stream)

        # Verify system prompt exists
        self.assertIsNotNone(preset.system_prompt)
        self.assertGreater(len(preset.system_prompt), 100)

        # Verify validation config
        self.assertTrue(preset.validation_enabled)
        self.assertTrue(preset.validation_strict)
        self.assertEqual(preset.output_schema_path, "schemas/intake.schema.json")

        # Verify cache config
        self.assertTrue(preset.cache_enabled)
        self.assertEqual(preset.cache_ttl_seconds, 3600)
        self.assertIn("prompt", preset.cache_key_fields)

        # Verify examples
        self.assertGreater(len(preset.examples), 0)

    def test_list_presets(self):
        """Test listing available presets"""
        presets = self.loader.list_presets()
        self.assertIn("intake_coach", presets)

    def test_load_schema(self):
        """Test loading JSON Schema"""
        schema = self.loader.load_schema("schemas/intake.schema.json")

        # Verify schema structure
        self.assertEqual(schema["$schema"], "http://json-schema.org/draft-07/schema#")
        self.assertEqual(schema["type"], "object")
        self.assertIn("demographics", schema["properties"])
        self.assertIn("chief_complaint", schema["properties"])
        self.assertIn("symptoms", schema["properties"])
        self.assertIn("medical_history", schema["properties"])
        self.assertIn("urgency", schema["properties"])

        # Verify urgency enum
        urgency_enum = schema["properties"]["urgency"]["enum"]
        self.assertEqual(urgency_enum, ["LOW", "MODERATE", "HIGH", "CRITICAL"])

    def test_cache_key_computation(self):
        """Test cache key computation"""
        preset = self.loader.load_preset("intake_coach")

        key1 = self.loader.compute_cache_key(preset, "Test prompt 1")
        key2 = self.loader.compute_cache_key(preset, "Test prompt 2")
        key3 = self.loader.compute_cache_key(preset, "Test prompt 1")  # Same as key1

        # Different prompts = different keys
        self.assertNotEqual(key1, key2)

        # Same prompt = same key
        self.assertEqual(key1, key3)

        # Keys are SHA256 hashes (64 hex chars)
        self.assertEqual(len(key1), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in key1))


class TestIntakeSchemaValidation(unittest.TestCase):
    """Test JSON Schema validation for intake data"""

    def setUp(self):
        self.loader = get_preset_loader()
        self.schema = self.loader.load_schema("schemas/intake.schema.json")

    def test_valid_complete_intake(self):
        """Test validation of complete valid intake"""
        intake = {
            "demographics": {
                "name": "John Doe",
                "age": 45,
                "gender": "M",
                "contact": "john@example.com",
            },
            "chief_complaint": "Chest pain",
            "symptoms": ["chest pain", "shortness of breath"],
            "medical_history": {
                "allergies": ["penicillin"],
                "medications": ["lisinopril"],
                "conditions": ["hypertension"],
            },
            "urgency": "CRITICAL",
            "notes": "Requires immediate evaluation",
        }

        # Should not raise
        self.assertTrue(self.loader.validate_output(intake, self.schema))

    def test_valid_minimal_intake(self):
        """Test validation with null/empty fields"""
        intake = {
            "demographics": {"name": None, "age": None, "gender": None, "contact": None},
            "chief_complaint": None,
            "symptoms": [],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "LOW",
            "notes": None,
        }

        # Should not raise
        self.assertTrue(self.loader.validate_output(intake, self.schema))

    def test_invalid_urgency_value(self):
        """Test validation fails with invalid urgency"""
        intake = {
            "demographics": {"name": None, "age": None, "gender": None, "contact": None},
            "chief_complaint": "Test",
            "symptoms": [],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "INVALID",  # Not in enum
            "notes": None,
        }

        with self.assertRaises(jsonschema.ValidationError):
            self.loader.validate_output(intake, self.schema)

    def test_invalid_gender_value(self):
        """Test validation fails with invalid gender"""
        intake = {
            "demographics": {
                "name": "Test",
                "age": 30,
                "gender": "X",  # Not in enum (should be M, F, O, or None)
                "contact": None,
            },
            "chief_complaint": "Test",
            "symptoms": [],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "LOW",
            "notes": None,
        }

        with self.assertRaises(jsonschema.ValidationError):
            self.loader.validate_output(intake, self.schema)

    def test_missing_required_field(self):
        """Test validation fails with missing required field"""
        intake = {
            "demographics": {"name": "Test", "age": 30, "gender": "M", "contact": None},
            # Missing chief_complaint
            "symptoms": [],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "LOW",
        }

        with self.assertRaises(jsonschema.ValidationError):
            self.loader.validate_output(intake, self.schema)


class TestIntakePrompts(unittest.TestCase):
    """Test 10 intake prompts with LLM"""

    def setUp(self):
        self.loader = get_preset_loader()
        self.preset = self.loader.load_preset("intake_coach")
        self.schema = self.loader.load_schema(self.preset.output_schema_path)

        # Load test prompts
        test_prompts_path = Path(__file__).parent / "test_intake_prompts.json"
        with open(test_prompts_path) as f:
            self.test_prompts = json.load(f)

    def test_all_prompts_validation(self):
        """Test all 10 prompts produce valid JSON"""
        from backend.llm_router import llm_generate

        errors = []

        for test_case in self.test_prompts:
            prompt = test_case["prompt"]
            expected_urgency = test_case["expected_urgency"]

            print(f"\n{'='*70}")
            print(f"Test Case {test_case['id']}: {test_case['name']}")
            print(f"{'='*70}")
            print(f"Prompt: {prompt}")

            try:
                # Generate with LLM
                full_prompt = (
                    f"{self.preset.system_prompt}\n\nPatient Input:\n{prompt}\n\nJSON Output:"
                )

                response = llm_generate(
                    prompt=full_prompt,
                    provider=self.preset.provider,
                    temperature=self.preset.temperature,
                    max_tokens=self.preset.max_tokens,
                )

                print(f"\nLLM Response ({len(response.content)} chars):")
                print(response.content[:500])

                # Parse JSON
                try:
                    output = json.loads(response.content)
                except json.JSONDecodeError as e:
                    errors.append(f"Test {test_case['id']}: JSON parse error: {e}")
                    print(f"❌ JSON Parse Error: {e}")
                    continue

                # Validate against schema
                try:
                    self.loader.validate_output(output, self.schema)
                    print("✅ Schema Validation: PASSED")
                except jsonschema.ValidationError as e:
                    errors.append(f"Test {test_case['id']}: Schema validation error: {e.message}")
                    print(f"❌ Schema Validation: FAILED - {e.message}")
                    continue

                # Check urgency level
                actual_urgency = output.get("urgency")
                print(f"🎯 Urgency: Expected={expected_urgency}, Actual={actual_urgency}")

                if actual_urgency != expected_urgency:
                    print("⚠️  Urgency mismatch (not an error, but noteworthy)")

                print(f"✅ Test Case {test_case['id']}: PASSED")

            except Exception as e:
                errors.append(f"Test {test_case['id']}: Unexpected error: {e}")
                print(f"❌ Error: {e}")

        # Print summary
        print(f"\n{'='*70}")
        print("📊 Test Summary")
        print(f"{'='*70}")
        print(f"Total tests: {len(self.test_prompts)}")
        print(f"Errors: {len(errors)}")

        if errors:
            print("\n❌ Errors:")
            for error in errors:
                print(f"  - {error}")

        # AC: 10 prompts → 0 validation errors
        self.assertEqual(len(errors), 0, "All 10 prompts should produce valid JSON")


def main():
    """Run tests"""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
