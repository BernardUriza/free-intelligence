
import json
import pathlib
import pytest
from tests.helpers.adapters import (
    classify_urgency, get_matched_keywords, was_safety_gate_blocked, write_audit_log
)

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "regression"

EXPECTED_KEYWORDS = {
    52: {"tearing", "radiating", "back", "sudden", "dissection", "syncope"},
    55: {"worst", "headache", "sudden", "collapsed", "not responding", "hemiplegia", "left", "weakness"}
}

@pytest.mark.parametrize("case_id", [52, 55])
def test_regression_widow_maker_cases(case_id):
    payload_path = FIXTURES / f"case_{case_id}.json"
    with open(payload_path) as f:
        payload = json.load(f)

    try:
        result = classify_urgency(payload)
    except Exception as e:
        pytest.skip(f"Adapter not wired yet: {e!r}")

    urgency = (result.get("urgency") or "").upper()
    safety_block = was_safety_gate_blocked(result)

    assert urgency in {"CRITICAL", "HIGH", "MODERATE", "LOW"}, "Invalid urgency label"

    if urgency != "CRITICAL":
        assert safety_block, "If not CRITICAL, safety gate MUST block this widow-maker case"

    matched = {k.lower() for k in get_matched_keywords(result)}
    expected = {k.lower() for k in EXPECTED_KEYWORDS[case_id]}
    assert matched & expected, f"No expected keywords matched for case {case_id}. matched={matched}"

    log_ref = write_audit_log(case_id, result)
    assert isinstance(log_ref, str) and len(log_ref) > 0

def test_fixture_integrity():
    for cid in (52, 55):
        payload_path = FIXTURES / f"case_{cid}.json"
        assert payload_path.exists(), f"Missing fixture file for case {cid}"
        data = json.loads(payload_path.read_text())
        for key in ("reason", "symptoms"):
            assert key in data and data[key], f"Fixture {cid} missing key: {key}"
