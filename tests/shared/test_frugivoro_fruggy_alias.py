"""Frugívoro aprende su apodo real: "fruggy" (issue #36).

En #general nadie le escribe "frugivoro" — le dicen "fruggy". Sin ese alias,
"fruggy, ¿esto lleva huevo?" no resolvía a nadie y el mensaje se perdía.

Positivo: "fruggy" (en cualquier caja) resuelve a la persona `frugivoro`, y los
tres alias viejos siguen vivos.
Resistencia (dos, la regla del repo pide ambas):
  1. límite de palabra — "fruggyland" CONTIENE el alias pero no lo es;
  2. marcador de objeto — "dile a fruggy…" habla DE él con alguien más, no CON
     él, y no debe despertarlo (misma ley que ya cuida a "frugi").
"""

from __future__ import annotations

from shared.personas.addressing import alias_is_addressee, any_alias_is_addressee
from shared.personas.registry import get_persona, persona_id_by_role_name


def frugivoro_aliases() -> list[str]:
    """Los alias REALES del registry, nunca una copia a mano en el test.

    Una lista hardcodeada aquí haría que las pruebas de dirección pasaran aunque
    el alias no estuviera registrado — verde decorativo. Leyendo del registry,
    borrar "fruggy" de él pone rojo TODO este archivo, que es el punto.
    """
    frugivoro = get_persona("frugivoro")
    assert frugivoro is not None
    return list(frugivoro.aliases)


def test_fruggy_is_registered_as_an_alias_of_frugivoro():
    frugivoro = get_persona("frugivoro")
    assert frugivoro is not None
    assert "fruggy" in frugivoro.aliases


def test_the_three_old_aliases_survive():
    """El apodo nuevo SUMA; nadie tiene que reaprender cómo llamarlo."""
    frugivoro = get_persona("frugivoro")
    assert frugivoro is not None
    for old in ("frugivoro", "frugi", "frugívoro"):
        assert old in frugivoro.aliases


def test_fruggy_resolves_to_frugivoro_in_any_case():
    """POSITIVO: la resolución es insensible a mayúsculas (y a acentos)."""
    assert persona_id_by_role_name("fruggy") == "frugivoro"
    assert persona_id_by_role_name("Fruggy") == "frugivoro"
    assert persona_id_by_role_name("FRUGGY") == "frugivoro"


def test_fruggy_is_addressed_as_a_vocative():
    """POSITIVO: el caso real del issue — llamarlo por su apodo lo despierta."""
    assert any_alias_is_addressee(frugivoro_aliases(), "fruggy, ¿el pan lleva huevo?")
    assert any_alias_is_addressee(frugivoro_aliases(), "gracias Fruggy")


def test_a_word_that_merely_contains_fruggy_is_not_an_address():
    """RESISTENCIA 1: el alias se busca como palabra completa, no como subcadena.
    Sin esto, cualquier palabra que lo contenga secuestraría el turno."""
    assert not any_alias_is_addressee(frugivoro_aliases(), "fuimos a fruggyland el domingo")
    assert not alias_is_addressee("fruggy", "me encanta el fruggyburger de la esquina")


def test_talking_about_fruggy_to_someone_else_is_not_an_address():
    """RESISTENCIA 2: "dile A fruggy" lo nombra como OBJETO de la frase — el
    mensaje es para otra persona. Es el mismo hueco que en 2026-07-06 dejó un
    turno sin dueño por 5 minutos con "frugi"; el apodo nuevo hereda la ley."""
    assert not any_alias_is_addressee(frugivoro_aliases(), "si quieres dile a fruggy que ya llegué")
    assert not any_alias_is_addressee(frugivoro_aliases(), "estaba hablando de fruggy con Alex")


def test_fruggy_does_not_answer_for_any_sibling():
    """RESISTENCIA 3 (barata y contundente): el apodo nuevo resuelve a Frugívoro
    y a NADIE más. El arnés `test_no_two_personas_share_a_role_candidate` cubre
    la colisión de forma general; esto lo ancla al caso concreto del issue."""
    assert persona_id_by_role_name("fruggy") not in {"insult", "vultur", "alice", "unborn_being"}
