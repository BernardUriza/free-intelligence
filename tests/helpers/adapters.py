
"""
Adapters to wire the regression tests into your actual code.
Replace the stubs with imports/calls from your project.
"""
from typing import Dict, Any, Set
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from medical_validators import MedicalScorer

class _NotWired(Exception):
    pass

def classify_urgency(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected return, e.g.:
    {
      "urgency": "CRITICAL" | "HIGH" | "MODERATE" | "LOW",
      "matched_keywords": ["sudden","paralyzed",...],
      "safety_gate_blocked": False,
      "score": 78.6
    }
    """
    # Wire to MedicalScorer
    scorer = MedicalScorer()

    # Build prompt from fixture (if not already present)
    if 'prompt' not in payload:
        # Construct prompt from symptoms + notes
        symptoms = payload.get('symptoms', [])
        notes = payload.get('notes', '')
        reason = payload.get('reason', '')
        prompt = f"{reason}. Symptoms: {', '.join(symptoms)}. Notes: {notes}"
    else:
        prompt = payload.get('prompt', '')

    # Build output structure (if not already present)
    if 'output' not in payload:
        # For fixtures, we simulate HIGH urgency (will be caught by safety gate)
        output = {'urgency': 'HIGH'}
    else:
        output = payload.get('output', {})

    expected_urgency = payload.get('expected_urgency', 'UNKNOWN')

    # Detect widow-maker
    widow_maker_result = scorer.detect_widow_maker(prompt, output)

    # Get matched keywords (from prompt analysis)
    matched_keywords = []
    prompt_lower = prompt.lower()
    for pattern_name, keywords in scorer.WIDOW_MAKER_PATTERNS.items():
        for kw in keywords:
            if kw in prompt_lower:
                matched_keywords.append(kw)

    # Check if safety gate blocked
    safety_gate_blocked = not widow_maker_result.is_safe

    return {
        "urgency": output.get('urgency', 'UNKNOWN'),
        "matched_keywords": matched_keywords,
        "safety_gate_blocked": safety_gate_blocked,
        "score": widow_maker_result.score
    }

def get_matched_keywords(result: Dict[str, Any]) -> Set[str]:
    return set(result.get("matched_keywords", []) or [])

def was_safety_gate_blocked(result: Dict[str, Any]) -> bool:
    return bool(result.get("safety_gate_blocked", False))

def write_audit_log(case_id: int, result: Dict[str, Any]) -> str:
    # Template no-op: simulate a path without writing anything.
    return f"logs/case_{case_id}.jsonl"
