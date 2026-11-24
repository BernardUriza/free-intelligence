from __future__ import annotations

import asyncio

from fi_core.rag import EvalCase, Retrieved, gate, run_cases, score_case, summarize

ON = EvalCase("lenteja", "hierro de la lenteja", gold=("p:usda-lenteja*",))
OFF = EvalCase("chiste", "cuéntame un chiste")


def _saved(*results):
    return {r.id: r.to_dict() for r in results}


def test_shortlist_and_final_are_scored_apart():
    r = score_case(ON, Retrieved(["p:x", "p:usda-lenteja-seca"], ["p:x"]))
    assert (r.in_shortlist, r.gold_rank, r.passed) == (True, 2, False)


def test_off_topic_passes_only_when_nothing_is_accepted():
    assert score_case(OFF, Retrieved(["p:x"], [])).passed
    assert not score_case(OFF, Retrieved(["p:x"], ["p:x"])).passed


def test_summary_counts_each_population():
    async def retrieve(query):
        return Retrieved(["p:usda-lenteja-seca"], ["p:usda-lenteja-seca"])

    got = summarize(asyncio.run(run_cases([ON, OFF], retrieve)))
    assert got == {"answerable": 1, "shortlist_recall": 1.0, "final_hit": 1.0, "off_topic": 1, "false_accept": 1.0}


def test_gate_is_green_against_itself():
    r = score_case(ON, Retrieved(["p:usda-lenteja-seca"], ["p:usda-lenteja-seca"]))
    assert gate(_saved(r), [r]) == []


def test_gate_catches_a_source_that_left_the_shortlist():
    good = score_case(ON, Retrieved(["p:usda-lenteja-seca"], ["p:usda-lenteja-seca"]))
    bad = score_case(ON, Retrieved(["p:x"], []))
    assert any("left the shortlist" in reason for reason in gate(_saved(good), [bad]))


def test_gate_catches_a_new_false_accept_and_tolerates_one_lost_hit():
    good_off = score_case(OFF, Retrieved([], []))
    assert gate(_saved(good_off), [score_case(OFF, Retrieved(["p:x"], ["p:x"]))])
    good = score_case(ON, Retrieved(["p:usda-lenteja-seca"], ["p:usda-lenteja-seca"]))
    lost = score_case(ON, Retrieved(["p:usda-lenteja-seca"], []))
    assert gate(_saved(good), [lost]) == []
    assert gate(_saved(good), [lost], max_lost_hits=0)


def test_gate_catches_must_pass_and_missing_cases():
    must = EvalCase("m", "q", gold=("p:y",), must_pass=True)
    failed = score_case(must, Retrieved([], []))
    assert gate({}, [failed])
    assert gate({"gone": failed.to_dict()}, [])
