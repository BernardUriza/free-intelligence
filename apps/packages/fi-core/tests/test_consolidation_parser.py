"""The consolidation parser: a judge is an LLM, so its output is adversarial input.

Two of these were reproduced against the real function before the fix: a one-line
fence raised IndexError out of a parser whose whole contract is to return
`{"ok": False}`, and an inconsistent plan applied a merge the judge never
described — leaving two contradictory facts where there had been one.
"""

import pytest

from fi_core.persona.mcp_server import parse_consolidation_result

FACTS = [
    {"id": 1, "fact": "se mudó a Madrid en 2020", "category": "general"},
    {"id": 2, "fact": "vive en Madrid", "category": "general"},
]


@pytest.mark.asyncio
async def test_a_fence_with_no_newline_returns_a_verdict_instead_of_raising():
    """`text.split("\\n", 1)[1]` on a single-line fence raised IndexError, and
    `consolidate_principal` calls this with no try — so a nightly batch died on
    the first principal whose judge answered on one line."""
    out = await parse_consolidation_result('```[{"op":"NOOP","id":1}]```', FACTS)
    assert out["ok"] is True
    assert {o["op"] for o in out["ops"]} == {"NOOP"}


@pytest.mark.asyncio
async def test_a_json_fence_with_a_newline_still_parses():
    out = await parse_consolidation_result('```json\n[{"op":"NOOP","id":1}]\n```', FACTS)
    assert out["ok"] is True


@pytest.mark.asyncio
async def test_an_inconsistent_merge_is_dropped_whole_not_pruned():
    """The judge claims id 2 twice: once as a NOOP, again inside a merge. Pruning
    `merge_ids` to [1] while KEEPING `new_fact` soft-deleted fact 1, inserted the
    merged sentence and left fact 2 alive beside it — two contradictory facts. A
    partial merge is not a merge, so the op goes and the backfill keeps both ids."""
    plan = ('[{"op":"NOOP","id":2},'
            '{"op":"UPDATE","merge_ids":[1,2],"new_fact":"vive en Madrid desde 2020"}]')
    out = await parse_consolidation_result(plan, FACTS)
    assert [o["op"] for o in out["ops"]] == ["NOOP", "NOOP"]
    assert {o["id"] for o in out["ops"]} == {1, 2}, "no row is lost"


@pytest.mark.asyncio
async def test_a_consistent_merge_still_applies():
    """The rule tightened; it did not disable merging."""
    plan = '[{"op":"UPDATE","merge_ids":[1,2],"new_fact":"vive en Madrid desde 2020"}]'
    out = await parse_consolidation_result(plan, FACTS)
    assert [o["op"] for o in out["ops"]] == ["UPDATE"]
    assert out["ops"][0]["merge_ids"] == [1, 2]


@pytest.mark.asyncio
@pytest.mark.parametrize("new_fact", ['{"text": "x"}', "123", "null", '"   "'])
async def test_a_new_fact_that_is_not_real_text_is_refused(new_fact):
    """It reaches asyncpg as a TEXT parameter, so a dict raised INSIDE the
    transaction rather than being refused as input."""
    plan = f'[{{"op":"UPDATE","merge_ids":[1],"new_fact":{new_fact}}}]'
    out = await parse_consolidation_result(plan, FACTS)
    assert all(o["op"] == "NOOP" for o in out["ops"])


@pytest.mark.asyncio
async def test_an_unparseable_response_is_a_verdict_not_an_exception():
    out = await parse_consolidation_result("not json at all", FACTS)
    assert out["ok"] is False and "json_decode_error" in out["error"]
