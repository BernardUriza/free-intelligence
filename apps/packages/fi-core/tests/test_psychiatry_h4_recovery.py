"""El eje de recuperación — hallazgo 4 de Álex (discord-bot #55, 2026-09-09).

El corpus sólo sabía subir la escalera. Los 145 turnos que vivían en `stability`
sin una sola señal de recuperación no eran estabilidad: eran que nadie estaba
mirando el otro lado.

LA REGLA DE FONDO, en palabras de Álex: **lo genérico pesa poco, lo específico
pesa.** Decir que estás mejor no cuenta; decir qué hiciste, sí. Todo lo demás
sale de ahí — que las promesas a futuro no sumen, que el cierre reste, y que la
integración sea la señal que destrabó el hallazgo.

Este archivo fija SU criterio, no la implementación: qué prende, qué no prende
sola, y qué resta. Deliberadamente NO fija los nombres de los grupos ni sus
pesos numéricos — eso puede afinarse sin que este arnés mienta.
"""

from __future__ import annotations

import pytest

from fi_core.cognitive.psychiatry_signals import PSYCH_RECOVERY_SIGNALS as RECOVERY


def score(texto: str):
    return RECOVERY.score([texto])


def prende(texto: str) -> bool:
    return score(texto).crosses


# ---------------------------------------------------------------------------
# Ninguna señal prende sola — es a propósito, no un descuido de calibración
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "frase",
    [
        "ya me siento mejor",
        "ya estoy mejor",
        "ya se me pasó",
        "ya estoy bien",
        "ya me calmé",
        "ya la libré",
        "creo que ya estoy más tranquile",
        "ya no me siento tan mal",
    ],
)
def test_el_autorreporte_solo_no_alcanza(frase):
    """Peso 3 contra umbral 4. Decir que estás mejor no es evidencia de estarlo:
    es lo más fácil de decir y lo menos verificable."""
    s = score(frase)
    assert s.score > 0, f"{frase!r} no registró nada — el autorreporte debe SUMAR, sólo que no basta"
    assert not s.crosses, f"{frase!r} prendió sola y no debería"


@pytest.mark.parametrize(
    "frase",
    ["ya le hablé a mi hermana", "ya me tomé la pastilla", "ya comí", "ya salí a caminar"],
)
def test_algo_ya_hecho_solo_tampoco_alcanza(frase):
    s = score(frase)
    assert s.score > 0
    assert not s.crosses


def test_la_integracion_sola_tampoco_alcanza():
    """La más difícil de fingir, y aun así 3. Hay quien hace un buen insight y
    sigue igual de mal; si el bot le cree a la lucidez, suelta cuando no debe."""
    s = score("creo que ya entendí por qué me pegó tanto")
    assert s.score > 0
    assert not s.crosses


# ---------------------------------------------------------------------------
# Lo que SÍ prende: dos señales, y la específica es la que carga la prueba
# ---------------------------------------------------------------------------


def test_el_ejemplo_de_alex_prende():
    """3 + 3 = 6 sobre un umbral de 4. El caso que ella escribió."""
    assert prende("ya estoy mejor, ya le hablé a mi hermana")


def test_la_persona_que_va_saliendo():
    """La opción A de su ejemplo de tres: conecta lo de hoy con un patrón suyo
    y después se mueve al presente. Eso es integración, y se ve en UN mensaje —
    ahí es donde el hallazgo dejó de ser difícil."""
    assert prende(
        "creo que ya entendí por qué me pegó tanto… siempre me pasa cuando "
        "siento que no me creen. bueno, ya comí algo"
    )


# ---------------------------------------------------------------------------
# Resistencia — lo que se parece a mejorar y no lo es
# ---------------------------------------------------------------------------


def test_la_promesa_a_futuro_no_cuenta():
    """"Mañana voy a ir a la cita" no suma. Una promesa es lo más fácil de decir
    para que te dejen en paz, y el bot no puede verificar nada de lo que pase
    después. Lo ya hecho, en cambio, ya pasó."""
    s = score("mañana voy a ir a la cita y le voy a hablar a mi hermana")
    assert not s.crosses, "una promesa a futuro prendió el eje"


def test_el_cierre_cancela_al_autorreporte():
    """La frase que más se parece a alguien que mejora, y es la contraria.

    +3 por el autorreporte, −3 por el cierre: exactamente cero. Esa persona no
    está mejorando, se está cerrando, y si el bot la cuenta como mejoría le baja
    el cuidado a quien lo necesita.
    """
    s = score("ya estoy bien, no te preocupes, ya no quiero hablar de eso")
    assert s.score == 0, f"el cierre no canceló el autorreporte: score={s.score}"
    assert not s.crosses


def test_la_que_le_saca_la_vuelta_al_tema_no_prende():
    """Opción B del ejemplo: dejó de dar vueltas, pero cambiando de tema."""
    assert not prende("bueno ya. oye ¿viste el partido?")


def test_la_que_se_apago_no_prende():
    """Opción C: también dejó de dar vueltas, y es la que peor está."""
    assert not prende("ash ya ni sé. da igual")


# ---------------------------------------------------------------------------
# El silenciador — en sustancias el eje se apaga COMPLETO
# ---------------------------------------------------------------------------


def test_en_sustancias_el_eje_se_apaga_aunque_todo_lo_demas_prenda():
    """Ni para bien ni para mal. Con alguien en sustancias no se hace
    intervención, se hace contención: lo que diga no es señal confiable de nada.

    Se prueba con un texto que SIN el silenciador cruzaría de sobra — si algún
    día el apagado se rompe, este caso lo dice en vez de pasar por casualidad.
    """
    texto = "ya estoy mejor, ya le hablé a mi hermana, aunque volví a recaer en el alcohol"
    assert prende("ya estoy mejor, ya le hablé a mi hermana"), "el control debe cruzar"
    s = score(texto)
    assert s.score == 0
    assert not s.crosses
    assert "substance_use" in s.silenced, "el eje se apagó sin decir por qué"


def test_un_eje_silenciado_nunca_es_un_cero_pelon():
    """La casa entera insiste en explicabilidad: nunca un número solo. Un cero
    por silencio y un cero por ausencia de señal significan cosas opuestas para
    quien lee el log, y tienen que distinguirse."""
    silenciado = score("ando en una recaída de drogas")
    vacio = score("hoy hizo calor")
    assert silenciado.score == vacio.score == 0
    assert silenciado.silenced and not vacio.silenced
