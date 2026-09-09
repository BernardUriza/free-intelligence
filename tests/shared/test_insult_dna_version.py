"""Insult no afirma su número de versión (issue #58).

La versión de deploy se estampa en `persona_gateway/delivery.py` DESPUÉS de
que el modelo generó el texto: nada la inyecta al contexto del turno, así que
la persona no puede saberla. Cuando se la preguntaban, la confabulaba — el
2026-09-07 dijo dos veces "v4.32.80" (un deploy real de agosto que vivió
semanas en #general) mientras el tag estampado decía ᵛ⁴·³⁸·⁸ y ᵛ⁴·³⁸·¹⁰.

## Por qué la primera versión de esta regla falló (2026-09-08)

La redacción original razonaba así: *"no sabes tu versión PORQUE nada te la
inyecta y `agent_facts` no tiene nada bajo version/deployment"*. Una regla dura
apoyada en un hecho verificable.

El probe en #general con v4.38.16 la tumbó el mismo día del deploy. Insult NO
desobedeció: **razonó**. Consultó `get_agent_facts`, encontró el self-fact 73
—"discord-bot v4.38.10", escrito el día anterior—, comprobó que la premisa era
falsa, y concluyó que la regla no le aplicaba: *"no invento, lo leo de mi
memoria persistida. Si no, v4.38.10 es mi versión viva."*

La lección, que es de diseño y no de redacción: **una regla dura no puede
apoyarse en un hecho que puede cambiar.** Basta que la realidad se mueva —y
aquí se movió en un día— para que la conclusión deje de seguirse. La regla
nueva es INCONDICIONAL: ninguna fuente califica, y no hay premisa que
verificar.

## QUÉ PRUEBA ESTE ARCHIVO — y qué NO

No se puede testear lo que el modelo va a contestar; eso lo cachó el probe en
#general, no el CI. Lo que sí se puede testear es que el ADN conserve la regla
que produce ese comportamiento, que sea incondicional, y que viva donde no se
la lleve un script.
"""

from pathlib import Path

import pytest

DNA = Path(__file__).resolve().parents[2] / "shared" / "personas" / "insult.md"
START_MARKER = "<!-- CAPABILITIES:START -->"
END_MARKER = "<!-- CAPABILITIES:END -->"

REGLA = "You do NOT know your own deploy version, and nothing can tell you it."

#: Las premisas de la versión que falló. Si alguna vuelve, la regla vuelve a
#: ser refutable y el modelo vuelve a tener por dónde salirse.
PREMISAS_QUE_SE_CAYERON = [
    "holds nothing under",
    "Nothing injects it into your turn",
]


@pytest.fixture(scope="module")
def dna() -> str:
    text = DNA.read_text(encoding="utf-8")
    assert text.strip(), "el ADN de Insult está vacío"
    return text


def test_la_regla_existe_y_es_incondicional(dna: str) -> None:
    assert REGLA in dna
    assert "Never assert a version number" in dna


@pytest.mark.parametrize("fuente", ["what feels familiar", "not from a self-fact", "looks like a receipt"])
def test_la_regla_nombra_las_tres_fuentes(dna: str, fuente: str) -> None:
    """Las tres por las que ya se salió o se podría salir, cerradas por nombre."""
    assert fuente in dna


@pytest.mark.parametrize("premisa", PREMISAS_QUE_SE_CAYERON)
def test_la_regla_no_se_apoya_en_un_hecho_verificable(dna: str, premisa: str) -> None:
    """El guardián de la lección del 2026-09-08.

    Si alguien le devuelve el "porque" a esta regla, le devuelve al modelo la
    salida que usó: comprobar la premisa, encontrarla falsa, y concluir que la
    regla no aplica. Un `assert not in` se ve raro en un test hasta que uno
    recuerda que la versión con premisa duró exactamente un día en producción.
    """
    assert premisa not in dna, (
        f"volvió una premisa verificable a la regla de versión: {premisa!r}. "
        "La regla tiene que ser incondicional — ver el probe fallido del #58."
    )


def test_la_regla_manda_a_la_etiqueta_en_vez_de_quedarse_en_no_se(dna: str) -> None:
    """Decisión de Álex: "no sé" a secas no le sirve a quien pregunta.

    La respuesta útil es dónde SÍ está el dato — el tag que el gateway estampa
    al final de cada mensaje — no la ignorancia de la persona.
    """
    assert "Don't stop at \"I don't know\" either" in dna
    assert "stamped automatically at the end of every message you send" in dna


def test_el_adn_prohibe_guardar_versiones_como_self_fact(dna: str) -> None:
    """Cierra el agujero de raíz: sin esto, el self-fact 73 vuelve a nacer.

    El fact que tumbó el probe no se lo inventó nadie: Insult lo grabó él mismo
    con `add_agent_fact` cuando se cerró el #64. Prohibir citarlo sin prohibir
    escribirlo deja la trampa armada para el siguiente deploy.
    """
    assert "Never record a version number as a self-fact." in dna


def test_las_dos_reglas_viven_fuera_del_bloque_autogenerado(dna: str) -> None:
    """Dentro de CAPABILITIES:START/END el script las borraría en silencio.

    `scripts/sync_capabilities.py` regenera ese bloque desde el código en cada
    commit. Ya se llevó TTS, web search, transcripción, recordatorios y deep
    memory sin que nadie se enterara.
    """
    block = range(dna.index(START_MARKER), dna.index(END_MARKER))
    for regla in (REGLA, "Never record a version number as a self-fact."):
        assert dna.index(regla) not in block, (
            f"la regla {regla!r} quedó dentro del bloque autogenerado: "
            "scripts/sync_capabilities.py la va a borrar en el próximo commit"
        )
