"""Frugívoro improvisa por función y balance, y no se cuelga un dato de umami que no aplica.

24-nov-2026, investigación con fuentes:
- el ~8x de sinergia umami se midió con inosinato (IMP), que sólo existe en tejido
  animal; la DNA lo atribuía a kombu + shiitake, que corre con guanilato (GMP);
- el maridaje por compuestos aromáticos compartidos (Ahn 2011) no es ley: Asia
  oriental y la India hacen lo contrario, y Spence (2020) lo da por desacreditado;
- los LLMs que "inventan" recetas convergen en muletillas (paprika ahumada en más
  de la mitad, Mizrahi et al. 2025) y mejoran recombinando platos reales.

Test del TEXTO de la DNA, igual que test_frugivoro_vegan_by_deduction.py.
"""

from __future__ import annotations

from pathlib import Path

DNA = Path(__file__).resolve().parents[2] / "shared" / "personas" / "frugivoro.md"


def bullet(marker: str) -> str:
    body = DNA.read_text(encoding="utf-8").lower()
    found = body.find(marker)
    assert found != -1, f"la DNA ya no contiene «{marker}»"
    start = body.rfind("\n- ", 0, found)
    end = body.find("\n- ", found)
    return body[start : end if end != -1 else len(body)]


def test_the_8x_belongs_to_inosinate_not_to_plants():
    umami = bullet("umami con mecanismo nombrado")
    assert "inosinato" in umami and "animal" in umami, "se perdió que el 8x medido es con IMP, de origen animal"
    assert "guanilato" in umami and "shiitake seco" in umami, "se perdió la sinergia vegetal real (GMP)"
    assert "kombu + shiitake ≈ 8\u00d7" not in umami, "volvió el 8x atribuido a kombu + shiitake"


def test_shared_compounds_is_not_the_pairing_law():
    method = bullet("improvisas por función y balance")
    assert "no una ley" in method
    assert "spence" in method


def test_improvisation_recombines_real_dishes_and_names_the_guess():
    method = bullet("improvisas por función y balance")
    assert "recombinas" in method, "se perdió partir de platos reales"
    assert "nunca de la nada" in method
    assert "improvisada" in method and "probarla" in method, "se perdió declarar qué parte es improvisada"
    assert method.index("recombinas") < method.index("contraste"), "el orden del método se invirtió"


def test_the_crutch_check_names_smoked_paprika():
    crutch = bullet("desconfías de tu primera muletilla")
    assert "paprika ahumada" in crutch


def test_humor_rides_with_the_data_never_at_the_user():
    humor = bullet("con humor, siempre de buen talante")
    assert "va con el dato" in humor
    assert "nunca es a costa de quien pregunta" in humor
