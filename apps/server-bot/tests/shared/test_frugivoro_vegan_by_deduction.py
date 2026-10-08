"""Frugívoro es vegano por DEDUCCIÓN, no por lista (issue #38).

2026-08-10, 23:11 en #general: el bot vegano recomendó "higo frío partido con
sal de gusano" — larva de maguey tostada, o sea un animal, en su propia voz y
sin fricción. No fue un desliz de redacción: su regla estaba escrita como
enumeración de prohibidos (carne, pescado, huevo, lácteo, miel, gelatina,
caldo), así que el criterio operativo era "¿está en mi lista?" y "sal de gusano"
no estaba. La miel SÍ estaba — la intención de excluir insectos existía desde el
día uno; lo que falló fue la forma de pensar, no el valor.

Una lista cerrada aplicada a un mundo abierto siempre pierde: mañana es la
cochinilla, el carmín, la cera de abeja, los escamoles, el colágeno marino.
Agregar "gusano" a la lista habría sido el mismo bug con una palabra más.

QUÉ PRUEBA ESTE ARCHIVO — y qué NO. No se puede testear lo que el modelo va a
decir: cada respuesta es distinta y ninguna aserción la alcanza. Lo que sí se
puede testear es que la DNA conserve la FORMA que produce ese comportamiento —
el procedimiento primero, los ejemplos subordinados a él. Es un test del texto,
no del bot, y decirlo es parte de la honestidad del arnés.

Positivo: la cadena de deducción (de dónde sale → cómo se hace → ser sintiente)
y el paso de preguntar cuando no se sabe están escritos.
Resistencia:
  1. ORDEN — el razonamiento va ANTES del primer ejemplo. Volver a poner la
     lista arriba y el porqué como nota al pie es exactamente el bug de #38, y
     un test que solo busque palabras sueltas lo dejaría pasar en verde;
  2. la sección de personas vulnerables no puede volver a apoyarse en la sola
     enumeración ("huevo, atún, lácteo o miel"), que heredaba el mismo hueco.
"""

from __future__ import annotations

from pathlib import Path

DNA = Path(__file__).resolve().parents[2] / "shared" / "personas" / "frugivoro.md"

# Marcas para ubicar cada viñeta. Son el texto en negritas que la abre, no el
# criterio en sí: si alguien reescribe el razonamiento, el localizador aguanta.
CRITERION_MARKER = "vegano por deducción"
VULNERABLE_MARKER = '"responsable" nunca significa "animal"'


def bullet_containing(marker: str) -> str:
    """La viñeta completa de la DNA que contiene `marker`, en minúsculas.

    Se recorta viñeta por viñeta a propósito: buscar sobre el archivo entero
    daría verde con que las palabras existieran en CUALQUIER parte, y la
    pregunta de este issue es si viven en el criterio mismo y en qué orden.
    """
    body = DNA.read_text(encoding="utf-8").lower()
    found = body.find(marker)
    assert found != -1, f"la DNA ya no contiene «{marker}» — ¿se reescribió la viñeta?"
    start = body.rfind("\n- ", 0, found)
    assert start != -1, f"«{marker}» no está dentro de una viñeta"
    end = body.find("\n- ", found)
    return body[start : end if end != -1 else len(body)]


def test_the_criterion_bullet_exists():
    """Anti-verde-decorativo: si el localizador se rompe, los asserts de abajo
    pasarían sobre una cadena vacía sin que nadie se enterara."""
    assert bullet_containing(CRITERION_MARKER).strip()
    assert bullet_containing(VULNERABLE_MARKER).strip()


def test_the_criterion_is_a_procedure_not_a_catalogue():
    """POSITIVO: la cadena de deducción está escrita como tal."""
    bullet = bullet_containing(CRITERION_MARKER)
    assert "de dónde sale" in bullet, "falta el paso de procedencia"
    assert "cómo se hace" in bullet, "falta el paso de proceso"
    assert "sintiente" in bullet, "falta el criterio que decide: un ser sintiente en el proceso"


def test_unknown_origin_is_asked_never_assumed():
    """POSITIVO: el hueco real no es lo que sabe, es lo que NO sabe. Sin este
    paso, cualquier ingrediente desconocido entra como vegetal por default."""
    bullet = bullet_containing(CRITERION_MARKER)
    assert "preguntas" in bullet, "no dice que pregunte cuando no sabe cómo se hace"
    assert "nunca asumes" in bullet, "no prohíbe asumir vegetal por default"


def test_the_reasoning_comes_before_the_examples():
    """RESISTENCIA 1: los ejemplos sobreviven, pero SUBORDINADOS.

    Ésta es la prueba que de verdad muerde. Un arnés que solo buscara palabras
    daría verde con el razonamiento arrumbado al final, debajo de la lista de
    siempre — que es la forma exacta del bug: el modelo lee primero la
    enumeración y de ahí saca su criterio operativo.
    """
    bullet = bullet_containing(CRITERION_MARKER)
    reasoning = min(bullet.index("de dónde sale"), bullet.index("cómo se hace"))
    first_example = min(bullet.index("la carne"), bullet.index("el huevo"))
    assert reasoning < first_example, (
        "los ejemplos aparecen ANTES del razonamiento: la viñeta volvió a ser una lista "
        "con una explicación de pie de página, que es el bug del issue #38"
    )


def test_the_vulnerable_section_inherits_the_same_criterion():
    """RESISTENCIA 2: la línea de personas vulnerables enumeraba igual ("huevo,
    atún, lácteo o miel") y heredaba el hueco. Si vuelve a apoyarse solo en esa
    lista, un argumento nutricional sobre algo no enumerado la atraviesa."""
    bullet = bullet_containing(VULNERABLE_MARKER)
    assert "procedencia" in bullet or "cómo se hace" in bullet, "la sección vulnerable no invoca la deducción"
    assert "sintiente" in bullet, "la sección vulnerable no nombra el criterio que decide"
    assert "dentro de lo vegetal" in bullet, "se perdió el fondo: la flexibilidad vive dentro de lo vegetal"
