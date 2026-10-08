"""Los headers de corpus PIDEN atribuir — y no se contradicen a sí mismos.

2026-07-27: se añadió al final de cada header un párrafo pidiendo citar la
procedencia, sin quitar de la primera línea la prohibición vieja ("no las
anuncies como fuente"). El bloque quedó auto-contradictorio y ganó la
prohibición: era más categórica y venía primero. Unborn Being respondió con el
corpus inyectado (`__corpus_unborn__`, similitud 0.865) y sin una sola cita.

Un parche aditivo que deja viva la regla que lo anula no es un cambio de
comportamiento — es la misma clase de fallo que dejar en pie el path que se
suponía migrado.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_HEADERS = sorted((Path(__file__).resolve().parents[2] / "shared" / "corpus" / "headers").glob("*.md"))

# Frases que prohíben ATRIBUIR. Cualquiera anula la instrucción de citar que
# vive en el mismo bloque, sin importar lo que diga el resto del header.
#
# Deliberadamente NO incluye "no cites" a secas: los headers dicen "si no la
# recuerdas, no cites", que es lo contrario — preferir el silencio a inventar
# una etiqueta. Un matcher que confunde ambas prohíbe la regla correcta, y esta
# nota existe porque el primer intento de este arnés hizo exactamente eso.
_CONTRADICTORY = (
    "no las anuncies como fuente",
    "no anuncies la fuente",
    "no anuncies su fuente",
    "no digas de dónde",
    "sin decir de dónde",
)


def test_there_are_headers_to_check():
    """Si el glob se rompe, los asserts de abajo pasarían vacíos — el fake-green
    clásico de un test parametrizado sobre archivos."""
    assert _HEADERS, "no se encontró ningún header de corpus"


@pytest.mark.parametrize("path", _HEADERS, ids=lambda p: p.stem)
def test_header_asks_for_attribution(path: Path):
    body = path.read_text(encoding="utf-8").lower()
    assert "procedencia" in body, f"{path.name} no explica que el pasaje trae procedencia"
    assert "corchetes" in body, f"{path.name} no dice dónde viene la etiqueta"


@pytest.mark.parametrize("path", _HEADERS, ids=lambda p: p.stem)
def test_header_does_not_forbid_attribution(path: Path):
    """RESISTENCIA: la prohibición legítima es de ESTILO (nada de bibliografía,
    nada de escudo de autoridad). Prohibir ATRIBUIR anula la cita entera."""
    body = path.read_text(encoding="utf-8").lower()
    for phrase in _CONTRADICTORY:
        assert phrase not in body, (
            f"{path.name} contiene «{phrase}», que contradice la instrucción de citar "
            "que vive en el mismo bloque — el modelo obedece la prohibición"
        )


@pytest.mark.parametrize("path", _HEADERS, ids=lambda p: p.stem)
def test_header_still_forbids_the_academic_costume(path: Path):
    """RESISTENCIA en la otra dirección: atribuir no puede volverlos académicos.
    La prohibición de estilo debe seguir viva, o el personaje se pierde."""
    body = path.read_text(encoding="utf-8").lower()
    assert "bibliografía" in body, f"{path.name} ya no prohíbe convertirlo en bibliografía"
    assert "literal" in body, f"{path.name} ya no prohíbe copiar literal"


@pytest.mark.parametrize("path", _HEADERS, ids=lambda p: p.stem)
def test_header_forbids_inventing_a_source(path: Path):
    """Una etiqueta inventada es peor que no citar: la cita solo vale si es
    verificable contra la lista realmente inyectada."""
    body = path.read_text(encoding="utf-8").lower()
    assert "inventes" in body, f"{path.name} no prohíbe inventar la procedencia"
