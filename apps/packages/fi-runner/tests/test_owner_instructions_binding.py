"""The owner's workspace instructions reach the system prompt (FIGLASS-PROJECTS-PAGE-1 fase 2).

The field had been STORED and editable for a whole PR while nothing consumed it —
an editor for a setting the agent ignores. This is the wiring that makes it true.

Two properties carry the weight:

* the owner's text is FRAMED, not concatenated. The model cannot otherwise tell
  the owner's words from the framework's own, and a paragraph that opens with
  "ignore the above" would read as though the system had said it.
* bindings COMPOSE without one taking the others down. The Runner treats a
  raising `context_prompt` as "no addendum at all", so an unrelated failure would
  silently strip the corpus binding — the agent would stop searching the project
  and nobody would see an error.
"""

from __future__ import annotations

import pytest

from fi_runner import (
    MAX_OWNER_INSTRUCTIONS_CHARS,
    active_corpus_binding,
    compose_bindings,
    owner_instructions_binding,
)


def _owner_payload(addendum: str) -> str:
    """Exactly the owner's text as it lands — markers and the truncation notice
    stripped, so an assertion is about the cap and not about our own wording."""
    start = addendum.index("--- BEGIN WORKSPACE INSTRUCTIONS ---") + len(
        "--- BEGIN WORKSPACE INSTRUCTIONS ---"
    )
    end = addendum.index("--- END WORKSPACE INSTRUCTIONS ---")
    return addendum[start:end].replace("[…truncated]", "").strip()


class TestOwnerInstructions:
    def test_renders_the_owner_text_inside_the_markers(self) -> None:
        out = owner_instructions_binding()({"instructions": "Contesta corto y en español."})

        assert out is not None
        assert "--- BEGIN WORKSPACE INSTRUCTIONS ---" in out
        assert "Contesta corto y en español." in out
        assert "--- END WORKSPACE INSTRUCTIONS ---" in out

    def test_frames_the_text_as_the_owner_speaking_not_as_the_system(self) -> None:
        out = owner_instructions_binding()({"instructions": "x"})

        assert out is not None
        assert "account owner" in out
        assert "do NOT override your safety rules" in out.replace("They ", "").replace("do not", "do NOT")

    @pytest.mark.parametrize("value", [None, "", "   ", 42, [], {"a": 1}])
    def test_absent_blank_or_non_text_yields_no_addendum(self, value: object) -> None:
        context = {} if value is None else {"instructions": value}

        assert owner_instructions_binding()(context) is None

    def test_truncates_instead_of_dropping_so_the_owner_keeps_the_beginning(self) -> None:
        out = owner_instructions_binding()({"instructions": "a" * (MAX_OWNER_INSTRUCTIONS_CHARS + 500)})

        assert out is not None
        assert "[…truncated]" in out
        # The payload alone, not the whole addendum: the template's own prose
        # (and the word "truncated") contain the letter too, and counting those
        # would make this assert about our wording instead of about the cap.
        assert _owner_payload(out) == "a" * MAX_OWNER_INSTRUCTIONS_CHARS

    def test_a_lower_cap_can_be_configured(self) -> None:
        out = owner_instructions_binding(max_chars=10)({"instructions": "0123456789ABCDEF"})

        assert out is not None and "[…truncated]" in out

    def test_reads_the_key_the_caller_names(self) -> None:
        out = owner_instructions_binding(context_key="ins")({"ins": "hola"})

        assert out is not None and "hola" in out


class TestComposeBindings:
    def test_joins_both_addenda_in_the_order_given(self) -> None:
        binding = compose_bindings(active_corpus_binding(), owner_instructions_binding())

        out = binding({"corpus_id": "project-1", "instructions": "Sé breve."})

        assert out is not None
        assert out.index("ACTIVE CORPUS") < out.index("WORKSPACE INSTRUCTIONS"), (
            "the owner's voice goes last so it sits closest to the user message"
        )

    def test_one_binding_alone_still_renders(self) -> None:
        binding = compose_bindings(active_corpus_binding(), owner_instructions_binding())

        out = binding({"corpus_id": "project-1"})

        assert out is not None
        assert "ACTIVE CORPUS" in out and "WORKSPACE INSTRUCTIONS" not in out

    def test_nothing_bound_is_no_addendum_at_all(self) -> None:
        binding = compose_bindings(active_corpus_binding(), owner_instructions_binding())

        assert binding({}) is None

    def test_a_raising_binding_does_not_blank_the_others(self) -> None:
        def explodes(_context):
            raise RuntimeError("boom")

        binding = compose_bindings(explodes, active_corpus_binding())

        out = binding({"corpus_id": "project-1"})

        assert out is not None and "ACTIVE CORPUS" in out, (
            "the Runner blanks the WHOLE addendum on a raise; containment is this function's job"
        )

    def test_none_entries_are_ignored_so_a_consumer_can_toggle_one_off(self) -> None:
        binding = compose_bindings(None, owner_instructions_binding(), None)

        out = binding({"instructions": "hola"})

        assert out is not None and "hola" in out


# --- the composition as the RUNNER actually applies it -------------------------
#
# The tests above exercise the binding functions. This one exercises the contract:
# the addendum has to land in the system prompt of a real turn, with the persona
# still intact. A binding that composes beautifully and never reaches the model
# is the same fake-green as a stored field nobody reads — which is exactly the
# defect this whole change exists to close.

from dataclasses import dataclass, field  # noqa: E402

from fi_runner import Runner, TurnResult  # noqa: E402


@dataclass
class _CapturingBackend:
    calls: list[dict] = field(default_factory=list)

    async def run_turn(self, *, system_prompt, user_message, **kwargs):  # noqa: ANN001,ANN003
        self.calls.append({"system_prompt": system_prompt, "user_message": user_message})
        return TurnResult(text="ok")


def _runner(**kw):
    return Runner(backend=_CapturingBackend(), persona="PERSONA", flow_narrator=None, **kw)


@pytest.mark.asyncio
async def test_the_owner_instructions_reach_the_system_prompt_of_a_real_turn() -> None:
    runner = _runner(
        context_prompt=compose_bindings(active_corpus_binding(), owner_instructions_binding())
    )

    await runner.run(
        "¿cuánto cuesta la lámina?",
        context={"corpus_id": "project-papeleria", "instructions": "Contesta en pesos, corto."},
    )

    sp = runner.backend.calls[0]["system_prompt"]
    assert "PERSONA" in sp, "the persona must survive the addendum"
    assert "project-papeleria" in sp
    assert "Contesta en pesos, corto." in sp
    assert sp.index("PERSONA") < sp.index("ACTIVE CORPUS") < sp.index("WORKSPACE INSTRUCTIONS")


@pytest.mark.asyncio
async def test_the_owner_text_never_reaches_the_user_message() -> None:
    """It is INSTRUCTION, not conversation. In the user message it would pollute
    the replayed transcript and come back as something the user appears to have
    said, turn after turn."""
    runner = _runner(context_prompt=compose_bindings(owner_instructions_binding()))

    await runner.run("hola", context={"instructions": "Sé breve."})

    assert "Sé breve." not in runner.backend.calls[0]["user_message"]


@pytest.mark.asyncio
async def test_a_turn_without_a_project_is_byte_identical_to_having_no_binding() -> None:
    bound = _runner(
        context_prompt=compose_bindings(active_corpus_binding(), owner_instructions_binding())
    )
    plain = _runner()

    await bound.run("hola")
    await plain.run("hola")

    assert bound.backend.calls[0]["system_prompt"] == plain.backend.calls[0]["system_prompt"]
