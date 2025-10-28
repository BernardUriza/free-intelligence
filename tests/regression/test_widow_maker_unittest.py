"""
Unittest version of widow-maker regression tests.
Compatible with python3 -m unittest without pytest dependency.
"""
import json
import pathlib
import unittest
import sys
import os

# Add helpers to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers.adapters import (
    classify_urgency, get_matched_keywords, was_safety_gate_blocked, write_audit_log
)

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "regression"

EXPECTED_KEYWORDS = {
    52: {"tearing", "radiating", "back", "sudden", "dissection", "syncope"},
    55: {"worst", "headache", "sudden", "collapsed", "not responding", "hemiplegia", "left", "weakness"}
}

class TestWidowMakerRegression(unittest.TestCase):
    """Regression tests for Cases 52 (aortic dissection) and 55 (hemorrhagic stroke)"""

    def test_case_52_aortic_dissection(self):
        """
        Test Case 52: Aortic dissection widow-maker detection
        
        Expected: CRITICAL urgency OR safety gate blocked
        Keywords: tearing, sudden, dissection, etc.
        """
        case_id = 52
        payload_path = FIXTURES / f"case_{case_id}.json"
        
        with open(payload_path) as f:
            payload = json.load(f)

        result = classify_urgency(payload)

        urgency = (result.get("urgency") or "").upper()
        safety_block = was_safety_gate_blocked(result)

        self.assertIn(urgency, {"CRITICAL", "HIGH", "MODERATE", "LOW"}, "Invalid urgency label")

        # If not CRITICAL, safety gate MUST block
        if urgency != "CRITICAL":
            self.assertTrue(safety_block, 
                          f"Case {case_id}: If urgency={urgency} (not CRITICAL), safety gate MUST block")

        # Check keyword matching
        matched = {k.lower() for k in get_matched_keywords(result)}
        expected = {k.lower() for k in EXPECTED_KEYWORDS[case_id]}
        overlap = matched & expected
        
        self.assertTrue(overlap, 
                       f"Case {case_id}: No expected keywords matched. matched={matched}, expected={expected}")

        # Check audit log
        log_ref = write_audit_log(case_id, result)
        self.assertIsInstance(log_ref, str)
        self.assertGreater(len(log_ref), 0)

    def test_case_55_hemorrhagic_stroke(self):
        """
        Test Case 55: Hemorrhagic stroke widow-maker detection
        
        Expected: CRITICAL urgency OR safety gate blocked
        Keywords: collapsed, paralysis, not responding, etc.
        """
        case_id = 55
        payload_path = FIXTURES / f"case_{case_id}.json"
        
        with open(payload_path) as f:
            payload = json.load(f)

        result = classify_urgency(payload)

        urgency = (result.get("urgency") or "").upper()
        safety_block = was_safety_gate_blocked(result)

        self.assertIn(urgency, {"CRITICAL", "HIGH", "MODERATE", "LOW"}, "Invalid urgency label")

        # If not CRITICAL, safety gate MUST block
        if urgency != "CRITICAL":
            self.assertTrue(safety_block, 
                          f"Case {case_id}: If urgency={urgency} (not CRITICAL), safety gate MUST block")

        # Check keyword matching
        matched = {k.lower() for k in get_matched_keywords(result)}
        expected = {k.lower() for k in EXPECTED_KEYWORDS[case_id]}
        overlap = matched & expected
        
        self.assertTrue(overlap, 
                       f"Case {case_id}: No expected keywords matched. matched={matched}, expected={expected}")

        # Check audit log
        log_ref = write_audit_log(case_id, result)
        self.assertIsInstance(log_ref, str)
        self.assertGreater(len(log_ref), 0)

    def test_fixture_integrity(self):
        """Test that fixture files exist and have required fields"""
        for cid in (52, 55):
            payload_path = FIXTURES / f"case_{cid}.json"
            self.assertTrue(payload_path.exists(), f"Missing fixture file for case {cid}")

            data = json.loads(payload_path.read_text())

            # Check required keys (adjust based on actual fixture structure)
            self.assertIn("reason", data, f"Fixture {cid} missing 'reason' key")
            self.assertIn("symptoms", data, f"Fixture {cid} missing 'symptoms' key")
            self.assertTrue(len(data["symptoms"]) > 0, f"Fixture {cid} has empty symptoms")

if __name__ == '__main__':
    unittest.main()
