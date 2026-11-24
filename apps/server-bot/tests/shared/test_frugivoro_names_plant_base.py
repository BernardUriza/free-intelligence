"""Frugívoro nombra la base vegetal de un platillo cuyo nombre implica algo animal (PR #697).

23-nov-2026: Frugi sugirió "quesadilla sellada" y "sincronizado de desayuno" para unas
tortillas de harina. Él pensaba en versiones veganas; la sesión de Claude que transcribió
la receta leyó queso de vaca y jamón de puerco, y las borró "porque Bernard es vegano".
El que lee la palabra sola no tiene el contexto de Frugi.

Es un test del TEXTO de la DNA, no de lo que el modelo diga (ver
test_frugivoro_vegan_by_deduction.py). Protege que la regla siga ahí, que siga
prohibiendo el nombre a secas, que traiga pares de ejemplo con la base nombrada,
y que conserve el porqué: el lector de afuera.
"""

from __future__ import annotations

from pathlib import Path

DNA = Path(__file__).resolve().parents[2] / "shared" / "personas" / "frugivoro.md"
MARKER = "nombras la base vegetal"


def rule_bullet() -> str:
    body = DNA.read_text(encoding="utf-8").lower()
    found = body.find(MARKER)
    assert found != -1, f"la DNA ya no contiene «{MARKER}»: se perdió la regla de PR #697"
    start = body.rfind("\n- ", 0, found)
    assert start != -1, f"«{MARKER}» no está dentro de una viñeta"
    end = body.find("\n- ", found)
    return body[start : end if end != -1 else len(body)]


def test_the_rule_bullet_exists():
    assert rule_bullet().strip()


def test_the_bare_dish_name_is_forbidden():
    bullet = rule_bullet()
    assert "nunca" in bullet and "a secas" in bullet, "la regla ya no prohíbe el nombre del platillo a secas"


def test_examples_pair_the_dish_with_its_plant_base():
    bullet = rule_bullet()
    assert "quesadilla de queso de papa" in bullet
    assert "jamón de seitán" in bullet


def test_the_reason_is_the_outside_reader():
    bullet = rule_bullet()
    assert "quien lee" in bullet, "se perdió el porqué: el lector de afuera no tiene el contexto de Frugi"
    assert "queso de vaca" in bullet, "se perdió la lectura por default que la regla existe para evitar"


def test_an_undefined_base_gets_a_concrete_proposal():
    bullet = rule_bullet()
    assert "propones una concreta" in bullet, "sin base definida, la regla debe obligar a proponer una"
