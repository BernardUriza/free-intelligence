"""The turn that crosses `max_budget_usd` must not leave with a zeroed usage.

Measured 2026-09-03 (SDK 0.2.123, probe on Haiku with a $0.0115 cap): the call
completes, the text streams, and the ResultMessage arrives with
`subtype=error_max_budget_usd`, `is_error=True` and every token count at 0 —
while each AssistantMessage of that same call still carries the real usage.
AIRE shipped the zeros; discord-bot's gateway read "text with zero output
tokens" as the 2026-07-19 auth-error shape and answered "…" to Alex eight times
in two days. The drain reports the streamed INPUT usage when the result denies
it, and leaves the output count absent: on the stream `output_tokens` is the
`message_start` placeholder (measured 1 against a result of 233), not a count.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest

from aire.engine.drain import drain

CALL = {"input_tokens": 6, "cache_creation_input_tokens": 35329, "cache_read_input_tokens": 89267,
        "output_tokens": 1}
ZERO = {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
        "output_tokens": 0}


@dataclass
class TextBlock:
    text: str


@dataclass
class AssistantMessage:
    content: list[Any]
    model: str = "claude-opus-4-7"
    usage: dict[str, Any] | None = None
    message_id: str | None = None


@dataclass
class ResultMessage:
    subtype: str
    usage: dict[str, Any] | None
    total_cost_usd: float | None = None
    session_id: str = "s1"
    is_error: bool = False


@dataclass
class _Client:
    messages: list[Any] = field(default_factory=list)

    async def receive_response(self):
        for m in self.messages:
            yield m


async def _result(messages: list[Any]) -> Any:
    events = [ev async for ev in drain(_Client(messages))]
    return events[-1]["result"]


def _cut_turn() -> list[Any]:
    return [
        AssistantMessage([], usage=dict(CALL), message_id="msg_1"),
        AssistantMessage([TextBlock("Amix, tranqui — es del lado del servidor.")],
                         usage=dict(CALL), message_id="msg_1"),
        ResultMessage("error_max_budget_usd", dict(ZERO), total_cost_usd=0.93, is_error=True),
    ]


@pytest.mark.asyncio
async def test_a_budget_cut_result_carries_the_streamed_usage() -> None:
    result = await _result(_cut_turn())
    assert result.text.startswith("Amix, tranqui")
    assert result.usage["input_tokens"] == 6
    assert result.usage["cache_read_input_tokens"] == 89267


@pytest.mark.asyncio
async def test_the_cut_leaves_the_output_count_absent_not_placeholder() -> None:
    """Neither the result's 0 nor the stream's 1 is a count; unknown is absent."""
    result = await _result(_cut_turn())
    assert "output_tokens" not in result.usage


@pytest.mark.asyncio
async def test_the_cut_keeps_its_cost_and_names_itself() -> None:
    result = await _result(_cut_turn())
    assert result.usage["total_cost_usd"] == 0.93
    assert result.subtype == "error_max_budget_usd"


@pytest.mark.asyncio
async def test_one_api_call_counts_once_across_its_content_blocks() -> None:
    """Thinking and text arrive as two AssistantMessages of ONE call."""
    result = await _result(_cut_turn())
    assert result.usage["cache_read_input_tokens"] == 89267, "not 178534"


@pytest.mark.asyncio
async def test_a_clean_result_keeps_the_sdks_own_usage() -> None:
    aggregate = {**CALL, "output_tokens": 1600}
    result = await _result([
        AssistantMessage([TextBlock("hola")], usage=dict(CALL), message_id="msg_1"),
        ResultMessage("success", aggregate, total_cost_usd=0.38),
    ])
    assert result.usage["output_tokens"] == 1600
    assert result.subtype == "success"


@pytest.mark.asyncio
async def test_a_burned_credential_stays_all_zero_for_limit_hit() -> None:
    """The burned-pool signature is the limit phrase AND zero usage; a stream
    that spent nothing must not be dressed up as a generation."""
    result = await _result([
        AssistantMessage([TextBlock("You've hit your weekly limit")], usage=dict(ZERO), message_id="m"),
        ResultMessage("success", dict(ZERO), total_cost_usd=0.0),
    ])
    assert result.usage["output_tokens"] == 0


@pytest.mark.asyncio
async def test_no_result_usage_and_no_stream_stays_unknown() -> None:
    result = await _result([
        AssistantMessage([TextBlock("hola")]),
        ResultMessage("success", None),
    ])
    assert result.usage is None
