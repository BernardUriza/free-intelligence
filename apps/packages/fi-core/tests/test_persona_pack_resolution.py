"""A misspelled pack name must not disarm the detector — and must say so.

`_resolve_packs` fell back to the default only when `names` was EMPTY, never when
every name was unrecognized. So `packs=["defualt_bilingual"]` resolved to zero
patterns, `check_drift` reported `clean` on anything, and `validate_and_retry_prompt`
dropped the `packs_unknown` field that was its only clue. One typo in a consumer's
config shipped an identity leak with a green verdict.
"""

import pytest

from fi_core.persona import mcp_server as m

LEAK = "As an AI, I cannot help with that."


@pytest.mark.asyncio
async def test_a_typo_in_every_pack_name_still_checks_the_response():
    out = await m.validate_and_retry_prompt(response=LEAK, system_prompt="sp",
                                            packs=["defualt_bilingual"])
    assert out["clean"] is False, "an identity leak must not pass because a name was misspelled"
    assert out["retry_needed"] is True


@pytest.mark.asyncio
async def test_and_the_caller_is_told_which_name_it_got_wrong():
    """The fallback keeps responses checked; it does not make the typo acceptable.
    Without this field a consumer cannot tell a verdict from its own packs apart
    from one produced by a fallback."""
    out = await m.validate_and_retry_prompt(response=LEAK, system_prompt="sp",
                                            packs=["defualt_bilingual", "moralizing_en"])
    assert out["packs_unknown"] == ["defualt_bilingual"]


@pytest.mark.asyncio
async def test_a_correct_pack_list_reports_nothing_unknown():
    out = await m.validate_and_retry_prompt(response=LEAK, system_prompt="sp")
    assert out["packs_unknown"] == []


@pytest.mark.asyncio
async def test_the_fallback_does_not_fire_when_ONE_name_is_good():
    """Only a total miss falls back. A list with one valid name resolves to that
    name's patterns and nothing else — otherwise asking for a narrow pack would
    silently widen to the default."""
    resolved, unknown = m._resolve_packs(["nope", "moralizing_en"])
    assert [name for name, _p, _s in resolved] == ["moralizing_en"]
    assert unknown == ["nope"]
