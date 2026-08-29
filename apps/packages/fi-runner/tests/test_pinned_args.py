"""Tool ARGUMENTS are a boundary, not a suggestion.

`allowed_tools` decides which tools may run. Nothing decided what they may be
called WITH — and fi-core's stateful capabilities namespace their data by an
argument the MODEL types: ``corpus_id`` on rag_store, ``session_id`` on
task_tracker. So a multi-tenant consumer's isolation rested on a paragraph in
the system prompt asking the agent to use the right id, next to tools called
``delete_document`` and ``delete_corpus``.

og118's own wiring said so out loud: *"`active_corpus_binding` es un addendum al
prompt, no una frontera: instruye al modelo a usar un corpus, no le impide tocar
otro."* These tests pin the frontier that comment was missing.
"""

from __future__ import annotations

import pytest

from fi_runner import (
    MCPServerSpec,
    Runner,
    TurnResult,
    pinned_arg_violation,
    pinned_corpus_args,
)

_RAG = "fi-core-rag-store"


def _spec(**kw) -> MCPServerSpec:
    return MCPServerSpec(name=_RAG, command="python", args=["-m", "x"], **kw)


# --- the verdict itself (pure, no harness) -----------------------------------


def test_a_call_on_the_pinned_value_is_allowed():
    specs = [_spec(pinned_args={"corpus_id": "project-mine"})]
    assert pinned_arg_violation(
        f"mcp__{_RAG}__search_documents", {"corpus_id": "project-mine", "query": "q"}, specs
    ) is None


def test_a_call_on_another_tenants_corpus_is_denied():
    specs = [_spec(pinned_args={"corpus_id": "project-mine"})]
    reason = pinned_arg_violation(
        f"mcp__{_RAG}__search_documents", {"corpus_id": "project-yours", "query": "q"}, specs
    )
    assert reason is not None
    assert "project-yours" in reason and "project-mine" in reason


def test_the_destructive_tools_are_pinned_like_every_other():
    """delete_corpus is 'tenant teardown' exposed to the model under BYPASS."""
    specs = [_spec(pinned_args={"corpus_id": "project-mine"})]
    for tool in ("delete_corpus", "delete_document", "ingest_document"):
        assert pinned_arg_violation(
            f"mcp__{_RAG}__{tool}", {"corpus_id": "project-yours"}, specs
        ) is not None


def test_an_unpinned_server_is_untouched():
    specs = [_spec(), MCPServerSpec(name="other", command="python", pinned_args={"corpus_id": "x"})]
    assert pinned_arg_violation(
        f"mcp__{_RAG}__search_documents", {"corpus_id": "anything"}, specs
    ) is None


def test_builtin_tools_are_not_the_pins_business():
    specs = [_spec(pinned_args={"corpus_id": "project-mine"})]
    assert pinned_arg_violation("WebFetch", {"corpus_id": "project-yours"}, specs) is None


def test_an_omitted_argument_is_not_pinned_into_existence():
    """A pin constrains what a value may BE, never that the tool must carry it —
    otherwise `stats()` on a server-defaulted corpus would start failing."""
    specs = [_spec(pinned_args={"corpus_id": "project-mine"})]
    assert pinned_arg_violation(f"mcp__{_RAG}__stats", {}, specs) is None


def test_int_and_str_forms_of_the_same_id_are_the_same_id():
    specs = [_spec(pinned_args={"corpus_id": 42})]
    assert pinned_arg_violation(f"mcp__{_RAG}__stats", {"corpus_id": "42"}, specs) is None
    assert pinned_arg_violation(f"mcp__{_RAG}__stats", {"corpus_id": "43"}, specs) is not None


# --- the Runner seam: pins are per-TURN, because the corpus is ---------------


class _CapturingBackend:
    """Records the specs the runner handed it for the turn.

    Declares :attr:`enforces_pinned_args` because it stands in for the backend
    that WILL gate tool input once aire-server accepts a pin in the turn body.
    No shipped backend does today (see the last test); this fake is how the
    contract stays covered until one does. :class:`_UngatedBackend` is the
    other half — every real backend behaves like that one right now."""

    enforces_pinned_args = True

    def __init__(self) -> None:
        self.seen: list[MCPServerSpec] = []

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        self.seen = list(kwargs["mcp_servers"])
        return TurnResult(text="ok")


class _UngatedBackend:
    """A backend that never sees tool arguments — AIRE's door, Codex's CLI."""

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text="ok")


def _runner(backend, **kw) -> Runner:
    return Runner(
        backend=backend,
        persona="p",
        extra_mcp_servers=[_spec()],
        flow_narrator=None,
        **kw,
    )


@pytest.mark.asyncio
async def test_the_turns_corpus_is_stamped_onto_the_spec():
    backend = _CapturingBackend()
    runner = _runner(backend, pin_tool_args=pinned_corpus_args())
    await runner.run("hi", context={"corpus_id": "project-mine"})
    assert backend.seen[0].pinned_args == {"corpus_id": "project-mine"}


@pytest.mark.asyncio
async def test_a_turn_with_no_active_corpus_pins_nothing():
    backend = _CapturingBackend()
    runner = _runner(backend, pin_tool_args=pinned_corpus_args())
    await runner.run("hi", context={})
    assert backend.seen[0].pinned_args == {}


@pytest.mark.asyncio
async def test_a_runner_without_the_hook_is_byte_identical():
    backend = _CapturingBackend()
    await _runner(backend).run("hi", context={"corpus_id": "project-mine"})
    assert backend.seen[0].pinned_args == {}


@pytest.mark.asyncio
async def test_two_turns_do_not_share_a_pin():
    """The specs are resolved per turn; a stamped one must never leak forward."""
    backend = _CapturingBackend()
    runner = _runner(backend, pin_tool_args=pinned_corpus_args())
    await runner.run("hi", context={"corpus_id": "project-a"})
    await runner.run("hi", context={"corpus_id": "project-b"})
    assert backend.seen[0].pinned_args == {"corpus_id": "project-b"}
    assert runner.extra_mcp_servers[0].pinned_args == {}, "the runner's own spec was mutated"


@pytest.mark.asyncio
async def test_a_raising_binding_surfaces_loudly_and_does_not_kill_the_turn():
    events: list[tuple[str, dict]] = []

    def boom(_context):  # noqa: ANN001, ANN202
        raise RuntimeError("bad binding")

    backend = _CapturingBackend()
    runner = _runner(
        backend,
        pin_tool_args=boom,
        on_event=lambda e, f: events.append((e, f)),
    )
    result = await runner.run("hi", context={"corpus_id": "project-mine"})
    assert result.text == "ok"
    assert any(e == "pin_tool_args_error" for e, _ in events), (
        "a binding that fails open MUST be alertable — that is the whole mitigation"
    )


@pytest.mark.asyncio
async def test_the_pin_event_reports_names_but_never_values():
    events: list[tuple[str, dict]] = []
    backend = _CapturingBackend()
    runner = _runner(
        backend,
        pin_tool_args=pinned_corpus_args(),
        on_event=lambda e, f: events.append((e, f)),
    )
    await runner.run("hi", context={"corpus_id": "project-secret"})
    pinned = [f for e, f in events if e == "tool_args_pinned"]
    assert pinned and pinned[0]["args"] == ["corpus_id"]
    assert "project-secret" not in str(pinned[0]), "a corpus id is tenant data, not telemetry"


# --- after the AIRE consolidation, NOTHING can enforce a pin -----------------


def test_no_shipped_backend_can_enforce_a_pin_today():
    """`ClaudeCodeBackend` was the only one that gated tool INPUT, and it was
    deleted with the local SDK/CLI hosts on 2026-08-29. AIRE receives tool NAMES
    over HTTP and never sees the arguments.

    So the machinery above is a CONTRACT waiting for aire-server, and the
    refusal is what keeps the gap honest in the meantime. The day the door
    accepts a pin in the turn body, `AIREBackend.enforces_pinned_args` flips to
    True and every test above starts covering production."""
    from fi_runner import AIREBackend

    assert getattr(AIREBackend(project="p"), "enforces_pinned_args", False) is False
