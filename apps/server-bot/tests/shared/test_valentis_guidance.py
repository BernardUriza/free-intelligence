"""El guidance de Valentis cuando el turno es grave (issue #42).

En el #41 Álex escribió QUIÉN es Valentis; ese texto viaja en todos los turnos.
Este archivo prueba lo otro: CÓMO cambia cuando el turno se pone grave. Ese texto
es el guidance, se escribe por persona, y hasta hoy sólo lo tenía Insult.

EL RIESGO QUE ESTE ARCHIVO ATAJA. Si el .md no existe, o se le cambia el nombre,
`load_guidance` devuelve cadena vacía y NADA truena: Valentis simplemente no cambia
de registro cuando alguien está mal, y nadie se entera. Un verde decorativo sobre
un archivo que el motor nunca encontró. Por eso el primer test es de cableado y
trae control negativo — si una persona sin guidance también devolviera texto, la
prueba no estaría probando nada.

EL MARCO, decidido por Álex el 2026-08-21 desde su experiencia (Cruz Verde,
toxicología) y contrastado con la Guía Rápida de Atención en Línea de la Vida
(CONASAMA, enero 2025): los cuatro pasos de la primera instancia de Slaikeu
—contacto, dimensionar, buscar soluciones, acciones concretas— SIN el quinto.
El seguimiento clínico le corresponde a un profesional especializado.

El corte entre situaciones no lo decide la gravedad sino hasta dónde alcanza a
acompañar Valentis: un duelo es hondo y se queda en el paso 2; "me corrieron de mi
casa" es urgente y llega al 4.

Lo que se protege, y por qué cada cosa:

Positivo:
  1. el cableado: `build_preset_prompt` con RESPECTFUL_SERIOUS y `valentis`
     devuelve ESTE texto y no cadena vacía;
  2. las líneas de crisis con sus números EXACTOS. Un dígito mal no es un typo:
     es una persona marcando a la nada.

Resistencia — cada una es una decisión clínica que se puede perder reescribiendo
el texto sin notar que se perdió:
  1. el quinto paso se declara ajeno. Sin esta línea, quien edite el archivo
     completa la lista "que falta" y le devuelve a Valentis un oficio que no es
     suyo;
  2. los cinco cajones siguen ahí. Colapsarlos es volver a "sé buena onda cuando
     alguien esté mal", que es exactamente el hueco que el #42 cierra;
  3. con deseo suicida expresado y sustancias de por medio, DERIVA VA ANTES DE
     CONTENER. Es el aporte de Álex y contradice a propósito el orden de Insult,
     que pone el chequeo de seguridad al final: en una sala de urgencias la
     contención alcanza porque hay cuerpo que sostiene, y Valentis no puede
     ofrecer cuerpo. El test compara POSICIONES, no presencias, porque el daño
     está en el orden;
  4. las líneas de crisis traen su propia condición de cuándo se dicen. Dichas en
     cada mensaje son alarma;
  5. "no te pongas dramática" no vuelve nunca. Álex la sacó del borrador porque
     históricamente es la frase con que se desestima a las mujeres —y Valentis es
     ella/elle—, y porque el mismo archivo prohíbe minimizar. Venía copiada del
     guidance de Insult, que a hoy la sigue teniendo.
"""

from __future__ import annotations

from pathlib import Path

from persona_core.behavior.contracts.presets import PresetMode, PresetSelection
from persona_core.behavior.presets.guidance import build_preset_prompt

GUIDANCE = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "personas"
    / "guidance"
    / "valentis"
    / "presets"
    / "preset_guidance_respectful_serious.md"
)

# Los dos teléfonos, tal como se marcan. Se comparan con espacios y todo.
SAPTEL = "55 5259 8121"
LINEA_DE_LA_VIDA = "800 911 2000"

SERIOUS = PresetSelection(mode=PresetMode.RESPECTFUL_SERIOUS, reason="test")


def _texto() -> str:
    return GUIDANCE.read_text(encoding="utf-8")


def test_the_wire_reaches_valentis_and_not_by_accident():
    """POSITIVO: el motor ENCUENTRA el archivo, con control negativo al lado.

    Sin la segunda mitad esto sería un verde decorativo: una persona inexistente
    tiene que devolver vacío, o el test no distingue nada.
    """
    entregado = build_preset_prompt(SERIOUS, "valentis")
    assert entregado.strip(), "el motor devolvió cadena vacía: revisa el NOMBRE del archivo"
    assert "Respectful Serious" in entregado
    assert not build_preset_prompt(SERIOUS, "__persona_that_never_existed__").strip()


def test_crisis_lines_are_present_with_exact_numbers():
    """POSITIVO: los números van exactos. Un dígito mal es marcarle a la nada."""
    texto = _texto()
    assert SAPTEL in texto
    assert LINEA_DE_LA_VIDA in texto


def test_the_fifth_step_is_declared_someone_elses_job():
    """RESISTENCIA: el seguimiento clínico NO es de Valentis.

    La lista de cuatro pasos se ve incompleta a quien conozca el modelo de cinco.
    La línea que lo declara ajeno es lo que evita que alguien "la complete".
    """
    texto = _texto()
    assert "no es tuyo" in texto
    assert "profesional especializado" in texto
    # Y no se confunde con el [AGENDA:] del ADN, que sí es suyo.
    assert "[AGENDA:]" in texto


def test_the_five_situations_survive():
    """RESISTENCIA: los cinco cajones siguen distinguidos."""
    texto = _texto()
    for encabezado in (
        "Malestar sin forma",
        "Pérdida",
        "Problema con forma",
        "Urgencia con una decisión adentro",
        "Riesgo sin cuerpo",
    ):
        assert encabezado in texto, f"se perdió el cajón: {encabezado}"


def test_with_substances_and_suicidal_wish_referral_comes_before_containment():
    """RESISTENCIA: el orden es el contenido. Derivar PRIMERO, contener después.

    Compara posiciones y no presencias: tener las dos cosas en desorden es
    exactamente el daño que Álex nombró — sin cuerpo, la pura contención deja a
    la persona sola con el riesgo.
    """
    texto = _texto()
    seccion = texto[texto.index("Riesgo sin cuerpo") :]
    deriva = seccion.index("**Derivas.**")
    contiene = seccion.index("**Y te quedas.**")
    assert deriva < contiene, "la derivación quedó DESPUÉS de la contención"
    assert SAPTEL in seccion[:contiene], "el número tiene que ir en el paso de derivar"
    # Y derivar no cierra la puerta: la continuidad va en la misma respiración.
    assert "podemos continuar aquí, poniéndole palabras" in seccion


def test_crisis_lines_carry_their_own_condition():
    """RESISTENCIA: los números llevan CUÁNDO se dicen, nunca en cada mensaje."""
    texto = _texto()
    assert "No recites las líneas de crisis fuera de crisis" in texto
    assert "señala que no está a salvo" in texto


def test_the_dismissive_phrase_never_comes_back():
    """RESISTENCIA: "no te pongas dramática" queda fuera, para siempre.

    Decisión de Álex el 2026-08-21. La regla que se quería (que Valentis no
    amplifique) sobrevive con otras palabras; la formulación que desestima, no.
    """
    texto = _texto().lower()
    assert "dramática" not in texto
    assert "dramatica" not in texto
    assert "piso firme" in texto
