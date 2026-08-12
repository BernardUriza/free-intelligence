"""What a turn cost, read off both shapes the result arrives in (#32d/#28).

This test exists because the invited-key ceiling did not bite: `turn_cost` read
the SDK's dataclass only, the HTTP surface handed it the flattened dict, and the
answer was a silent $0.00 on every turn. Two live turns at $0.108 and $0.116 left
`spent_usd = 0` in `aire_token`. A money function that cannot tell "no result"
from "a shape I do not know" fails as free money, so both shapes are pinned here.
"""

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from aire.engine.drain import turn_cost


@dataclass
class _Result:
    text: str
    usage: dict[str, Any] | None = None


def _flattened(event: dict[str, Any]) -> dict[str, Any]:
    """Exactly what `messages.py` does to an event before it hits the wire."""
    return {k: asdict(v) if is_dataclass(v) and not isinstance(v, type) else v
            for k, v in event.items()}


def _event() -> dict[str, Any]:
    return {"type": "result", "result": _Result("hi", {"total_cost_usd": 0.108})}


def test_reads_the_sdk_dataclass() -> None:
    assert turn_cost(_event()) == 0.108


def test_reads_the_flattened_dict() -> None:
    assert turn_cost(_flattened(_event())) == 0.108


def test_a_turn_without_a_result_is_free() -> None:
    assert turn_cost({"type": "text", "text": "still thinking"}) == 0.0


def test_a_result_without_usage_is_free() -> None:
    assert turn_cost({"type": "result", "result": _Result("hi")}) == 0.0
