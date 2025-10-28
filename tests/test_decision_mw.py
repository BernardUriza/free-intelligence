#!/usr/bin/env python3
"""
Tests for Decision Middleware

Validates:
1. Rules loading from YAML
2. Condition evaluation (all operators)
3. Rule matching and event emission
4. Integration with IntakeCoach output

File: tests/test_decision_mw.py
Created: 2025-10-28
"""

import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.decision_mw import (
    DecisionMiddleware,
    ConditionEvaluator,
    DecisionEvent,
    get_decision_middleware
)


class TestConditionEvaluator(unittest.TestCase):
    """Test ConditionEvaluator operators"""

    def setUp(self):
        self.evaluator = ConditionEvaluator()

    def test_equals_operator(self):
        """Test equals operator"""
        condition = {"field": "urgency", "operator": "equals", "value": "CRITICAL"}
        data = {"urgency": "CRITICAL"}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"urgency": "LOW"}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_not_equals_operator(self):
        """Test not_equals operator"""
        condition = {"field": "urgency", "operator": "not_equals", "value": "LOW"}
        data = {"urgency": "CRITICAL"}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"urgency": "LOW"}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_greater_than_operator(self):
        """Test greater_than operator"""
        condition = {"field": "age", "operator": "greater_than", "value": 65}
        data = {"age": 70}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"age": 60}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_less_than_operator(self):
        """Test less_than operator"""
        condition = {"field": "age", "operator": "less_than", "value": 18}
        data = {"age": 5}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"age": 25}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_contains_operator(self):
        """Test contains operator"""
        condition = {"field": "complaint", "operator": "contains", "value": "chest pain"}
        data = {"complaint": "Patient has chest pain and shortness of breath"}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"complaint": "Headache"}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_array_contains_operator(self):
        """Test array_contains operator"""
        condition = {"field": "symptoms", "operator": "array_contains", "value": "fever"}
        data = {"symptoms": ["fever", "cough", "headache"]}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"symptoms": ["cough", "headache"]}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_array_not_empty_operator(self):
        """Test array_not_empty operator"""
        condition = {"field": "allergies", "operator": "array_not_empty"}
        data = {"allergies": ["penicillin"]}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"allergies": []}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_array_length_gte_operator(self):
        """Test array_length_gte operator"""
        condition = {"field": "conditions", "operator": "array_length_gte", "value": 3}
        data = {"conditions": ["hypertension", "diabetes", "COPD"]}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"conditions": ["hypertension"]}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_is_null_operator(self):
        """Test is_null operator"""
        condition = {"field": "name", "operator": "is_null"}
        data = {"name": None}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"name": "John"}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_is_not_null_operator(self):
        """Test is_not_null operator"""
        condition = {"field": "name", "operator": "is_not_null"}
        data = {"name": "John"}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"name": None}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_nested_field_access(self):
        """Test dot notation for nested fields"""
        condition = {"field": "demographics.age", "operator": "less_than", "value": 18}
        data = {"demographics": {"age": 5}}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"demographics": {"age": 30}}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_and_operator(self):
        """Test AND logical operator"""
        condition = {
            "operator": "and",
            "conditions": [
                {"field": "urgency", "operator": "equals", "value": "HIGH"},
                {"field": "age", "operator": "less_than", "value": 18}
            ]
        }

        data = {"urgency": "HIGH", "age": 5}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"urgency": "LOW", "age": 5}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_or_operator(self):
        """Test OR logical operator"""
        condition = {
            "operator": "or",
            "conditions": [
                {"field": "urgency", "operator": "equals", "value": "CRITICAL"},
                {"field": "urgency", "operator": "equals", "value": "HIGH"}
            ]
        }

        data = {"urgency": "CRITICAL"}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"urgency": "HIGH"}
        self.assertTrue(self.evaluator.evaluate(condition, data))

        data = {"urgency": "LOW"}
        self.assertFalse(self.evaluator.evaluate(condition, data))

    def test_always_operator(self):
        """Test always operator (default rule)"""
        condition = {"operator": "always"}
        data = {}
        self.assertTrue(self.evaluator.evaluate(condition, data))


class TestDecisionMiddleware(unittest.TestCase):
    """Test DecisionMiddleware"""

    def setUp(self):
        self.mw = get_decision_middleware()

    def test_load_rules(self):
        """Test rules loading from YAML"""
        presets = self.mw.list_presets()
        self.assertIn("intake_coach", presets)

    def test_get_preset_rules(self):
        """Test getting rules for a preset"""
        rules = self.mw.get_preset_rules("intake_coach")
        self.assertIn("schema", rules)
        self.assertIn("rules", rules)
        self.assertGreater(len(rules["rules"]), 0)

    def test_critical_urgency_rule(self):
        """Test CRITICAL urgency triggers correct event"""
        data = {
            "demographics": {"name": "John", "age": 45, "gender": "M", "contact": None},
            "chief_complaint": "Chest pain",
            "symptoms": ["chest pain", "shortness of breath"],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "CRITICAL",
            "notes": None
        }

        events = self.mw.apply_rules("intake_coach", data, stop_on_first_match=True)

        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].event, "CRITICAL_TRIAGE_REQUIRED")
        self.assertEqual(events[0].priority, "P0")

    def test_pediatric_urgent_rule(self):
        """Test pediatric + HIGH urgency triggers correct event"""
        data = {
            "demographics": {"name": "Child", "age": 5, "gender": "F", "contact": None},
            "chief_complaint": "Fever",
            "symptoms": ["fever", "cough"],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "HIGH",
            "notes": None
        }

        events = self.mw.apply_rules("intake_coach", data, stop_on_first_match=True)

        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].event, "PEDIATRIC_URGENT_CARE_REQUIRED")
        self.assertEqual(events[0].priority, "P1")

    def test_chest_pain_cardiac_screening(self):
        """Test chest pain triggers cardiac screening"""
        data = {
            "demographics": {"name": "Patient", "age": 50, "gender": "M", "contact": None},
            "chief_complaint": "chest pain",
            "symptoms": [],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "MODERATE",
            "notes": None
        }

        events = self.mw.apply_rules("intake_coach", data, stop_on_first_match=True)

        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].event, "CARDIAC_SCREENING_REQUIRED")

    def test_complex_patient_coordination(self):
        """Test 3+ conditions triggers care coordination"""
        data = {
            "demographics": {"name": "Patient", "age": 65, "gender": "M", "contact": None},
            "chief_complaint": "Follow-up",
            "symptoms": [],
            "medical_history": {
                "allergies": [],
                "medications": [],
                "conditions": ["hypertension", "diabetes", "COPD", "CKD"]
            },
            "urgency": "LOW",
            "notes": None
        }

        events = self.mw.apply_rules("intake_coach", data, stop_on_first_match=False)

        # Should match multiple rules (care coordination + others)
        self.assertGreater(len(events), 0)

        # Check if care coordination event is present
        event_names = [e.event for e in events]
        self.assertIn("CARE_COORDINATION_REQUIRED", event_names)

    def test_allergy_alert(self):
        """Test allergies trigger alert"""
        data = {
            "demographics": {"name": "Patient", "age": 30, "gender": "F", "contact": None},
            "chief_complaint": "Routine",
            "symptoms": [],
            "medical_history": {
                "allergies": ["penicillin", "sulfa"],
                "medications": [],
                "conditions": []
            },
            "urgency": "LOW",
            "notes": None
        }

        events = self.mw.apply_rules("intake_coach", data, stop_on_first_match=False)

        event_names = [e.event for e in events]
        self.assertIn("ALLERGY_ALERT_ACTIVE", event_names)

    def test_incomplete_demographics(self):
        """Test missing demographics triggers completion event"""
        data = {
            "demographics": {"name": None, "age": None, "gender": None, "contact": None},
            "chief_complaint": "Test",
            "symptoms": [],
            "medical_history": {"allergies": [], "medications": [], "conditions": []},
            "urgency": "LOW",
            "notes": None
        }

        events = self.mw.apply_rules("intake_coach", data, stop_on_first_match=False)

        event_names = [e.event for e in events]
        self.assertIn("DEMOGRAPHICS_COMPLETION_REQUIRED", event_names)

    def test_stop_on_first_match(self):
        """Test stop_on_first_match flag"""
        data = {
            "demographics": {"name": "Patient", "age": 30, "gender": "M", "contact": None},
            "chief_complaint": "Test",
            "symptoms": [],
            "medical_history": {
                "allergies": ["penicillin"],
                "medications": [],
                "conditions": []
            },
            "urgency": "LOW",
            "notes": None
        }

        # Without stop_on_first_match (should get multiple events)
        events_all = self.mw.apply_rules("intake_coach", data, stop_on_first_match=False)

        # With stop_on_first_match (should get only first)
        events_first = self.mw.apply_rules("intake_coach", data, stop_on_first_match=True)

        self.assertGreater(len(events_all), len(events_first))
        self.assertEqual(len(events_first), 1)


def main():
    """Run tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    main()
