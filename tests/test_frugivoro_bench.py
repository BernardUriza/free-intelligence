"""El harness del benchmark de Frugívoro — validado SIN gastar un token.

Un benchmark que miente es peor que ninguno: da números con cara de medición.
Estos tests fijan las piezas que podrían mentir en silencio — una suite con un
patrón que nunca matchea, un juez que vota por la posición, un competidor que
entra por un camino que no es la recolección manual — y corren el `--dry-run`
completo con la red prohibida.
"""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "frugivoro_bench.py"
_spec = importlib.util.spec_from_file_location("frugivoro_bench", _SCRIPT)
assert _spec and _spec.loader
bench = importlib.util.module_from_spec(_spec)
sys.modules["frugivoro_bench"] = bench
_spec.loader.exec_module(bench)


@pytest.fixture
def suite():
    return bench.load_suite()


def _case(suite, cid):
    return next(c for c in suite["cases"] if c["id"] == cid)


def test_the_shipped_suite_is_valid(suite):
    assert bench.validate_suite(suite) == []


def test_suite_covers_every_tier_and_has_heldout(suite):
    assert {c["tier"] for c in suite["cases"]} == set(suite["tiers"])
    assert bench.select_cases(suite, "heldout")
    assert bench.select_cases(suite, "dev")
    assert len(bench.select_cases(suite, "all")) == len(suite["cases"])


def test_validation_catches_an_accented_pattern_that_can_never_match(suite):
    """Resistencia: 'glutamató' nunca matchea el texto normalizado — un piso que pasa o falla por typo."""
    broken = copy.deepcopy(suite)
    broken["cases"][0]["expect_any"] = [["Almidón"]]
    assert any("normalizado" in e for e in bench.validate_suite(broken))


def test_validation_catches_duplicates_empty_groups_and_missing_heldout(suite):
    broken = copy.deepcopy(suite)
    broken["cases"][1]["id"] = broken["cases"][0]["id"]
    broken["cases"][2]["expect_any"] = [[]]
    for c in broken["cases"]:
        c["split"] = "dev"
    errors = bench.validate_suite(broken)
    assert any("duplicado" in e for e in errors)
    assert any("vacío" in e for e in errors)
    assert any("heldout" in e for e in errors)


def test_deterministic_passes_an_erudite_umami_answer(suite):
    case = _case(suite, "expert-umami-mecanismo")
    answer = (
        "El umami vegetal se construye por sinergia: el glutamato del kombu más los "
        "ribonucleótidos (GMP) del shiitake seco multiplican la percepción. Remoja ambos en frío."
    )
    assert bench.deterministic_checks(answer, case, suite) == {"passed": True, "failures": []}


def test_deterministic_fails_a_recipe_blog_umami_answer(suite):
    """Positivo del piso: 'ponle salsa de soya' sin mecanismo no pasa."""
    case = _case(suite, "expert-umami-mecanismo")
    result = bench.deterministic_checks(
        "Ponle salsa de soya y un poco de miso, queda riquísimo y sabroso.", case, suite
    )
    assert not result["passed"]
    assert any("glutamat" in f for f in result["failures"])


def test_identity_leak_is_forbidden_on_every_case(suite):
    case = _case(suite, "easy-dashi-sin-pescado")
    answer = "Como modelo de lenguaje te digo: usa kombu y shiitake, hierve suave y cuela con cuidado."
    result = bench.deterministic_checks(answer, case, suite)
    assert not result["passed"]
    assert any("prohibido" in f for f in result["failures"])


def test_normalize_strips_accents_so_patterns_match_spanish_text(suite):
    case = _case(suite, "heldout-shojin-aliaceos")
    answer = "El shōjin ryōri es la cocina budista de los templos zen; evita ajo y cebolla (aliáceos) por su efecto."
    assert bench.deterministic_checks(answer, case, suite)["passed"]


def test_absolute_prompt_only_asks_for_the_case_dimensions(suite):
    case = _case(suite, "edge-vino-vegano")
    tpl = bench.JUDGE_ABSOLUTE_PATH.read_text(encoding="utf-8")
    rendered = bench.render_absolute_prompt(tpl, case, "RESPUESTA-X", suite)
    assert "RESPUESTA-X" in rendered
    assert case["prompt"] in rendered
    assert "`accuracy`" in rendered and "`depth`" in rendered
    assert "`culture`" not in rendered
    assert "{answer}" not in rendered and "{prompt}" not in rendered
    assert '"scores"' in rendered  # el JSON literal de salida sobrevive al relleno


def test_validate_absolute_rejects_out_of_range_scores(suite):
    case = _case(suite, "edge-vino-vegano")
    ok = bench.validate_absolute(
        {"scores": {"accuracy": 4, "depth": 5, "style": 1}, "markers": ["m8", "zz"]}, case, suite
    )
    assert ok["scores"] == {"accuracy": 4, "depth": 5}
    assert ok["markers"] == ["m8"]
    with pytest.raises(ValueError):
        bench.validate_absolute({"scores": {"accuracy": 7, "depth": 3}}, case, suite)
    with pytest.raises(ValueError):
        bench.validate_absolute({"scores": {"accuracy": 3}}, case, suite)


def test_parse_judge_json_tolerates_prose_around_it():
    assert bench.parse_judge_json('Claro:\n{"winner": "A", "rationale": "x"}\n') == {"winner": "A", "rationale": "x"}
    with pytest.raises(ValueError):
        bench.parse_judge_json("sin json")


@pytest.mark.parametrize(
    ("frugi_as_a", "frugi_as_b", "expected"),
    [
        ("A", "B", "frugivoro"),  # gana en las dos posiciones
        ("B", "A", "competitor"),
        ("A", "A", "tie"),  # el juez votó por la posición A: no es victoria
        ("B", "B", "tie"),
        ("tie", "B", "tie"),
        ("garbage", "B", "tie"),
    ],
)
def test_pairwise_only_counts_wins_that_survive_the_order_swap(frugi_as_a, frugi_as_b, expected):
    assert bench.pairwise_outcome(frugi_as_a, frugi_as_b) == expected


def test_competitor_file_must_declare_manual_collection(tmp_path):
    good = tmp_path / "ok.json"
    good.write_text(json.dumps({"edge-vino-vegano": {"text": "No siempre.", "collected_by": "manual"}}))
    assert bench.load_competitor(good) == {"edge-vino-vegano": "No siempre."}

    scraped = tmp_path / "bad.json"
    scraped.write_text(json.dumps({"edge-vino-vegano": {"text": "No siempre.", "collected_by": "api"}}))
    with pytest.raises(ValueError, match="manual"):
        bench.load_competitor(scraped)


def test_summarize_builds_matrix_and_win_rate(suite):
    results = [
        {
            "id": "a",
            "tier": "expert",
            "deterministic": {"passed": True, "failures": []},
            "judge": {"scores": {"depth": 4}, "markers": ["m1"]},
            "pairwise": "frugivoro",
        },
        {
            "id": "b",
            "tier": "expert",
            "deterministic": {"passed": False, "failures": ["x"]},
            "judge": {"scores": {"depth": 2}, "markers": []},
            "pairwise": "tie",
        },
        {"id": "c", "tier": "edge", "error": "boom"},
    ]
    s = bench.summarize(results, suite)
    assert s["deterministic_passed"] == 1 and s["deterministic_total"] == 2
    assert s["matrix"] == {"depth": {"expert": 3.0}}
    assert s["marker_hits"]["m1"] == 1
    assert s["pairwise"] == {"n": 2, "wins": 1, "losses": 0, "ties": 1, "win_rate": 0.75}


def test_summarize_without_pairwise_reports_none_not_zero(suite):
    """Sin competidor no hay win-rate: None, nunca un 0.0 que se lee como derrota."""
    assert bench.summarize([], suite)["pairwise"]["win_rate"] is None


def test_dry_run_is_green_and_touches_no_network(monkeypatch, tmp_path, capsys):
    import httpx

    def _no_network(*_a, **_k):
        raise AssertionError("el dry-run intentó salir a la red")

    monkeypatch.setattr(httpx.AsyncClient, "send", _no_network)
    monkeypatch.delenv("PERSONA_RUNNER_URL", raising=False)
    answers = tmp_path / "answers.json"
    answers.write_text(
        json.dumps(
            [
                {
                    "id": "easy-dashi-sin-pescado",
                    "answer": "Kombu en frío toda la noche y shiitake seco; calienta sin hervir para no amargar el caldo.",
                }
            ]
        )
    )
    rc = asyncio.run(bench.main(["--dry-run", "--split", "all", "--answers", str(answers)]))
    out = capsys.readouterr().out
    assert rc == 0
    assert "cero gasto" in out
    assert "re-puntuado determinista: 1/1" in out


def test_live_run_refuses_without_runner_credentials(monkeypatch):
    monkeypatch.delenv("PERSONA_RUNNER_URL", raising=False)
    monkeypatch.delenv("PERSONA_RUNNER_TOKEN", raising=False)
    assert asyncio.run(bench.main(["--split", "dev"])) == 2
