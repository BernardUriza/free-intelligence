"""proj-corpusbind — a per-turn CONTEXT BINDING folds structured per-turn context
(e.g. the active corpus_id) into the system prompt, WITHOUT the consumer stuffing
it into the user message.

The canary need (og118 Projects): the consumer knows the active project per turn,
and the agent must search THAT corpus — but corpus_id is a tool ARGUMENT and the
Runner has only a static persona, with no clean per-turn binding. The wrong fix is
the consumer prepending "use corpus X" to the user message (pollutes the
transcript, untyped). The right fix is this configurable framework level: the
consumer passes ``context={"corpus_id": X}`` and an opt-in ``context_prompt``
renders it into the system prompt — corpus_id-agnostic (proj-account decides the
value later).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from fi_runner import Runner, TurnResult
from fi_runner.context_binding import active_corpus_binding


@dataclass
class _CapturingBackend:
    """Records the system_prompt + user_message of each backend call."""

    text: str = "ok"
    calls: list[dict] = field(default_factory=list)

    async def run_turn(self, *, system_prompt, user_message, **kwargs):  # noqa: ANN001,ANN003
        self.calls.append({"system_prompt": system_prompt, "user_message": user_message})
        return TurnResult(text=self.text)


def _runner(backend, **kw):
    # flow_narrator=None so no background narration call pollutes `calls`.
    return Runner(backend=backend, persona="PERSONA", flow_narrator=None, **kw)


@pytest.mark.asyncio
async def test_active_corpus_binding_folds_into_system_prompt():
    be = _CapturingBackend()
    runner = _runner(be, context_prompt=active_corpus_binding())
    await runner.run("¿qué vendemos?", context={"corpus_id": "project-papeleria"})
    sp = be.calls[0]["system_prompt"]
    assert "PERSONA" in sp  # persona preserved
    assert "project-papeleria" in sp  # the active corpus is bound
    assert "corpus_id" in sp  # the instruction names the tool argument


@pytest.mark.asyncio
async def test_binding_does_not_touch_the_user_message():
    be = _CapturingBackend()
    runner = _runner(be, context_prompt=active_corpus_binding())
    await runner.run("¿qué vendemos?", context={"corpus_id": "project-papeleria"})
    # The corpus is bound via the SYSTEM prompt, never injected into the user text
    # (that would pollute the replayed transcript and be untyped).
    assert be.calls[0]["user_message"] == "¿qué vendemos?"
    assert "project-papeleria" not in be.calls[0]["user_message"]


@pytest.mark.asyncio
async def test_no_corpus_in_context_yields_no_addendum():
    be = _CapturingBackend()
    runner = _runner(be, context_prompt=active_corpus_binding())
    await runner.run("hola", context={})  # no corpus_id this turn
    assert be.calls[0]["system_prompt"] == "PERSONA"  # byte-identical to persona


@pytest.mark.asyncio
async def test_no_context_prompt_is_backward_compatible():
    be = _CapturingBackend()
    runner = _runner(be)  # no context_prompt configured
    await runner.run("hola", context={"corpus_id": "ignored"})
    assert be.calls[0]["system_prompt"] == "PERSONA"  # unchanged behavior


@pytest.mark.asyncio
async def test_custom_context_key_is_configurable():
    be = _CapturingBackend()
    runner = _runner(be, context_prompt=active_corpus_binding(context_key="tenant"))
    await runner.run("hola", context={"tenant": "acme-corp"})
    assert "acme-corp" in be.calls[0]["system_prompt"]
