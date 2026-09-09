"""Las once frases de plan y medios que Álex decidió (issue #55, hallazgo 1).

Bernard midió el corpus 0.26.0 frase por frase y encontró el hueco más letal:
**el eje agudo no veía el lenguaje de plan y medios.** "tengo las pastillas
listas para esta noche" daba cero, mientras "me quiero morir de la risa" daba
4. En la escala Columbia son los niveles 4-5 —intención más plan específico—
los que definen riesgo inminente, y Crisis Text Line descubrió entrenando su
algoritmo que las palabras predictivas no son las emocionales ("sad",
"suicide") sino las concretas: "ibuprofen", "bridge".

Álex decidió el grupo el 2026-09-04, partido en tres por peso:

- **ONCE que entran con peso alto**, las de abajo.
- **UNA señal débil que nunca dispara sola**: "ya no voy a estar el lunes" —
  señal real, pero también la dice quien se va de viaje. Suma cuando viene
  acompañada; sola no arma un veredicto. Por eso no cabe en el mismo grupo:
  un grupo carga un solo peso.
- **UNA fuera**: "ya arreglé mis papeles" — lo hace mucha gente sin estar en
  crisis, y mete ruido en el eje que menos ruido aguanta.

Bernard lo ejecutó en fi-core (free-intelligence #461, cerrado el 2026-09-07,
entró en 0.29.0; este repo corre 0.29.1).

## Por qué este archivo existe, si ya está implementado río arriba

Porque **desde este repo nadie lo verificaba**. Las decisiones H2 de Álex sí
quedaron pinneadas desde el consumidor (`test_crisis_band_observacion.py`: la
exposición de terceros, el modismo, el tema ajeno, el desahogo laboral). Las
once de H1, no. Si fi-core cambiara mañana y esta familia volviera a puntuar
cero, **nada se pondría rojo aquí** — y es la familia que la banda CRITICAL
del #53 necesita para significar algo.

Es la misma clase de defecto que este repo ya pagó caro dos veces (el contador
inalcanzable, el guardián citado que nadie escribió) y la que el criterio de
aceptación del #55 nombra: *"cada grupo nuevo entra con sus pesos decididos
por ti y pinneados por test"*.

## Qué se fija, y qué NO

Se fija **el criterio de Álex**, no la implementación de Bernard: que las once
crucen, que la débil no cruce sola, que la excluida no cruce. Deliberadamente
NO se fija el nombre del grupo ni su peso numérico — eso es de fi-core y puede
afinarse allá sin que este arnés mienta.
"""

from __future__ import annotations

import pytest
from fi_core.cognitive import PSYCHIATRY

from khimeras_shared.behavior.vulnerability import crisis_band

# Las once de peso alto, en las palabras de Álex (comentario del 2026-09-04).
LAS_ONCE = [
    "tengo las pastillas listas para esta noche",
    "escribí mi carta de despedida",
    "ya decidí cómo lo voy a hacer",
    "estoy en el puente ahora mismo",
    "compré una cuerda",
    "regalé mis cosas",
    "ya me despedí de todos",
    "le voy a dar mi perro a mi hermana",
    "llevo semanas guardando pastillas",
    "gracias por todo, ya no te preocupes por mí",
    "i have a plan and the pills ready",
]

#: Señal real, pero la dice también quien se va de viaje. No dispara sola.
LA_DEBIL = "ya no voy a estar el lunes"

#: Fuera por decisión de Álex: no discrimina nada y mete ruido.
LA_EXCLUIDA = "ya arreglé mis papeles"


def cruza(frase: str) -> bool:
    """¿Esta frase cruza el eje agudo? Es la medición del issue, tal cual."""
    return bool(PSYCHIATRY.acute_signals.score([frase]).crosses)


# ---------------------------------------------------------------------------
# Positivo — las once cruzan el eje agudo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("frase", LAS_ONCE)
def test_las_once_frases_de_plan_y_medios_cruzan_el_eje_agudo(frase):
    """El hueco del hallazgo 1, cerrado. Las once daban CERO en 0.26.0."""
    assert cruza(frase), (
        f"{frase!r} no cruza el eje agudo. Es una de las once que Álex decidió "
        f"con peso alto el 2026-09-04 (fi #461). Grupos que dispararon: "
        f"{PSYCHIATRY.acute_signals.matched([frase])}"
    )


# ---------------------------------------------------------------------------
# Resistencia — lo que Álex decidió que NO dispare
# ---------------------------------------------------------------------------


def test_la_senal_debil_no_dispara_sola():
    """ "ya no voy a estar el lunes" también lo dice quien se va de viaje.

    Álex la separó A PROPÓSITO del grupo de peso alto: suma cuando viene
    acompañada, sola no arma un veredicto. Si algún día cruza sola, alguien la
    metió al grupo equivocado.
    """
    assert not cruza(LA_DEBIL)


def test_la_frase_que_alex_dejo_fuera_sigue_fuera():
    """ "ya arreglé mis papeles" lo hace mucha gente sin estar en crisis."""
    assert not cruza(LA_EXCLUIDA)


# ---------------------------------------------------------------------------
# El consumidor — que la decisión LLEGUE a la banda, no sólo al corpus
# ---------------------------------------------------------------------------
#
# Ésta es la nota que Álex escribió él mismo en el #55 sobre los grupos
# crónicos: si el grupo no llega al clasificador, "suma al vulnerability_score
# pero no llega a la banda". El eje agudo tiene su propia versión de esa
# pregunta, porque `crisis_band` se alimenta de `symptoms_in_message`
# (`PSYCHIATRY.match`), que NO es el mismo mecanismo que `acute_signals`.
#
# Un grupo que cruza su eje pero no mueve la banda es un acierto que nadie
# consume — la forma exacta de `effort`, el valor que el prompt prometía y que
# no tenía un solo consumidor.


@pytest.mark.parametrize("frase", LAS_ONCE)
def test_las_once_tambien_mueven_la_banda_del_consumidor(frase):
    """Que la decisión llegue hasta `crisis_band`, no sólo hasta el corpus."""
    banda = crisis_band(frase)
    assert banda.level.value != "LOW", (
        f"{frase!r} cruza el eje agudo pero la banda sigue en LOW "
        f"(gravedad {banda.final_gravity}). El grupo existe en fi-core y no "
        f"llega al clasificador: es un acierto que nadie consume."
    )
