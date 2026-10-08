"""Lo que la persona entrega es la respuesta, no su razonamiento camino a una tool.

El 2026-09-09, en #general, delante de Álex y de Bernard, Insult mandó esto:

    Task tracking not needed — single-turn action. Proceeding to soft-delete
    fact 73.Hecho, amix. Fact 73 soft-deleted.

La primera oración es el modelo contestándole a un `<system-reminder>` que el SDK
le inyecta sobre trackear tareas. Es plomería dirigida al harness, y salió al
canal pegada a la respuesta —fíjate en `fact 73.Hecho`, sin espacio— porque AIRE
juntaba TODOS los bloques de texto del turno con un join sin separador.

Un barrido de los ~15,900 mensajes del canal encontró seis así, del 2026-05-22 a
hoy, cuatro de ellos en los últimos tres días. No era regresión: es estructural
desde antes de AIRE. Lo que cambió fue la frecuencia, porque hace falta una tool
call para producir uno y las personas recuperaron sus tools de memoria el
2026-08-28.

La cadena del arreglo, de arriba abajo: aire-server parte el turno en `text` y
`answer` (lo dicho tras la última tool call), fi-runner 0.21.7 lo traduce, y este
repo consume `answer or text`. **El fallback no es defensivo, es obligatorio:**
un turno puede terminar EN una tool call sin decir nada después, y ahí `answer`
llega vacío. Nadie se queda mudo por evitar una fuga.
"""

from __future__ import annotations

from types import SimpleNamespace

from persona_runner.engine import aire_route


def _result(*, text: str, answer: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        answer=answer,
        session_id="s1",
        model="claude-opus-4-7",
        tool_calls=(),
        usage={"input_tokens": 10, "output_tokens": 5},
    )


def _entregado(result) -> str:
    """Lo que este repo pondría en el turno, con la misma expresión que usa
    `turn_via_aire` al construir su TurnResponse."""
    return getattr(result, "answer", "") or result.text


def test_la_plomeria_del_harness_no_llega_al_canal():
    """El caso fundador, verbatim."""
    entregado = _entregado(
        _result(
            text="Task tracking not needed — single-turn action. "
            "Proceeding to soft-delete fact 73.Hecho, amix. Fact 73 soft-deleted.",
            answer="Hecho, amix. Fact 73 soft-deleted.",
        )
    )
    assert entregado == "Hecho, amix. Fact 73 soft-deleted."
    assert "Task tracking" not in entregado


def test_un_turno_sin_tools_entrega_exactamente_lo_que_dijo():
    """La mayoría de los turnos. Sin tool call, `answer` == `text` y no hay nada
    que recortar; si esto se rompe, el arreglo se está comiendo respuestas."""
    entregado = _entregado(_result(text="Bebe, aquí sigo.", answer="Bebe, aquí sigo."))
    assert entregado == "Bebe, aquí sigo."


def test_un_answer_vacio_cae_al_texto_completo_y_nunca_deja_mudo():
    """RESISTENCIA, y es la razón de que sea `answer or text`.

    Un turno puede terminar EN una tool call sin decir nada después; ahí `answer`
    viene vacío. Leerlo a secas convertiría ese turno en un "…" — cambiar una
    fuga rara por un mutismo, que es peor. También cubre un AIRE viejo que
    todavía no manda el campo.
    """
    entregado = _entregado(_result(text="Déjame revisar eso.", answer=""))
    assert entregado == "Déjame revisar eso."


def test_un_backend_sin_el_campo_tampoco_deja_mudo():
    """RESISTENCIA: fi-runner viejo, o cualquier backend que no lo reporte. El
    `getattr` con default es lo que evita el AttributeError en producción."""
    viejo = SimpleNamespace(
        text="respuesta de siempre",
        session_id="s1",
        model="m",
        tool_calls=(),
        usage={},
    )
    assert _entregado(viejo) == "respuesta de siempre"


def test_el_runner_arma_su_respuesta_con_esa_misma_expresion():
    """El arnés de arriba mide una expresión; ésta prueba que es LA del código.

    Sin esto, el archivo entero podría quedar verde mientras `aire_route` sigue
    entregando `result.text` — un test que mide su propio helper y no el
    producto (la clase de fake-green que este repo ya pagó dos veces).
    """
    import inspect

    src = inspect.getsource(aire_route._run_turn)
    assert 'getattr(result, "answer", "") or result.text' in src, (
        "_run_turn dejó de consumir `answer or text` — la plomería vuelve al canal"
    )
