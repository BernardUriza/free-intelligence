"""What the gateway mirror keeps and what it refuses to keep twice (#41).

The measured problem: over 15 live days the request half of `aire_gateway_log`
was 63.7 MB against 8 MB of responses, because the Messages API is stateless and
a client re-sends the conversation, the system array and every tool schema on
every call. These tests pin the two things that make dropping the repetition
safe — nothing vanishes without saying so, and a value referenced by fingerprint
is a value the log actually holds somewhere.
"""

import json

from aire.gateway_condense import ELIDED, REF, fingerprint, inline, split

SYSTEM = [{"type": "text", "text": "you are a helpful assistant"}]
TOOLS = [{"name": "Read", "input_schema": {"type": "object", "properties": {}}}]


def _body(turns: int) -> dict:
    return {"model": "claude-opus-4-7", "max_tokens": 4096, "stream": True,
            "system": SYSTEM, "tools": TOOLS,
            "messages": [{"role": "user", "content": f"turn {i}"} for i in range(turns)]}


def test_only_the_last_message_is_kept_and_the_row_says_how_many_it_dropped():
    row, _ = split(_body(20))
    assert row["messages"] == [{"role": "user", "content": "turn 19"}]
    assert row[ELIDED]["messages"] == 19, "the row must announce what it does not repeat"


def test_a_single_turn_elides_no_history():
    row, _ = split(_body(1))
    assert len(row["messages"]) == 1
    assert "messages" not in row.get(ELIDED, {})


def test_system_and_tools_leave_a_fingerprint_and_the_value_to_store():
    row, blobs = split(_body(3))
    assert "system" not in row and "tools" not in row
    assert row[ELIDED]["system"] == {REF: fingerprint(SYSTEM)}
    assert row[ELIDED]["tools"] == {REF: fingerprint(TOOLS)}
    assert blobs == {fingerprint(SYSTEM): SYSTEM, fingerprint(TOOLS): TOOLS}


def test_the_same_values_fingerprint_the_same_across_requests():
    """The whole saving rests on this: 33 distinct system arrays were stored 585
    times. Key ordering must not make two identical values look different."""
    a, _ = split({"system": {"b": 1, "a": 2}, "messages": []})
    b, _ = split({"system": {"a": 2, "b": 1}, "messages": []})
    assert a[ELIDED]["system"] == b[ELIDED]["system"]


def test_nothing_is_dropped_without_being_announced():
    body = _body(5)
    row, _ = split(body)
    for key in body:
        assert key in row or key in row[ELIDED], f"{key} vanished silently"


def test_a_failed_blob_write_degrades_to_a_fat_row_never_a_dangling_reference():
    """If the blob could not be stored, the row must carry the value itself. A
    reference to something never written is worse than a big row — the front
    that reads this log cannot repair one."""
    body = _body(5)
    row, blobs = split(body)
    fat = inline(row, blobs, body)
    assert fat["system"] == SYSTEM and fat["tools"] == TOOLS
    assert "system" not in fat.get(ELIDED, {}) and "tools" not in fat.get(ELIDED, {})
    assert fat[ELIDED]["messages"] == 4, "the history count survives the fallback"


def test_a_body_that_is_not_an_object_passes_through_untouched():
    for odd in (None, [1, 2], "hello", 42):
        row, blobs = split(odd)
        assert row == odd and blobs == {}


def test_the_delta_is_actually_smaller():
    body = _body(200)
    row, _ = split(body)
    assert len(json.dumps(row)) * 10 < len(json.dumps(body)), \
        "a 200-turn request must shrink by an order of magnitude"
