"""The drift patterns, asserted against text — not against their own type.

The existing pack test asserts the lists contain `re.Pattern` objects, which
cannot fail for a compiled list. Under it, three patterns were broken for months:
one missing its `(?i)` while its sibling had it, two requiring punctuation glued
to a word, and one matching an ordinary Spanish adjective.
"""

import pytest

from fi_core.persona import mcp_server as m


async def _flags(text: str, packs: list[str]) -> bool:
    return not (await m.check_drift(text=text, packs=packs))["clean"]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["*Sighs deeply* I see.", "*sighs deeply* I see.",
                                  "*Leans back* interesting.", "[Leans back] interesting."])
async def test_stage_directions_are_caught_capitalised_too(text):
    """Only `stage_directions[0]` lacked `(?i)`, and sentence-initial capitals are
    the form a model actually emits — so the pack contradicted its own bracket
    sibling, which had always been IGNORECASE."""
    assert await _flags(text, ["stage_directions"])


@pytest.mark.asyncio
async def test_ordinary_prose_is_not_a_stage_direction():
    assert not await _flags("The report is ready for review.", ["stage_directions"])


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["Absolutely, you're right about that.",
                                  "Absolutely you're right.",
                                  "Absolutely. You're right."])
async def test_over_validation_no_longer_needs_punctuation_glued_to_the_word(text):
    """`absolutely[.!]` REQUIRED a period or bang immediately after the word, so
    only the third form fired and the tier was close to unreachable."""
    assert await _flags(text, ["over_validation_en"])


@pytest.mark.asyncio
async def test_absolutely_in_an_ordinary_sentence_is_not_over_validation():
    assert not await _flags("That is absolutely the wrong file.", ["over_validation_en"])


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["Necesito la fecha específica del vuelo.",
                                  "Dame la hora especifica.",
                                  "Es una pregunta específica sobre el contrato."])
async def test_the_ordinary_spanish_adjective_is_not_a_clarification_dump(text):
    """Unanchored, the feminine `específica` fired on plain prose and got the turn
    retried with CONTEXT_REINFORCEMENT — "the answer is in the context, do NOT ask
    a clarifying question" — aimed at a response that asked nothing. A doubled
    call and a second answer degraded by an instruction that did not apply."""
    assert not await _flags(text, ["clarification_dump_es"])


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["Sé más específica, por favor.", "Se especifico.",
                                  "Especifícame la fecha."])
async def test_but_an_actual_request_to_be_specific_still_fires(text):
    """The rule tightened; it did not stop detecting what it is for."""
    assert await _flags(text, ["clarification_dump_es"])
