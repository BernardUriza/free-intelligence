"""El piso de seguridad para usuario vulnerable llega a TODA persona registrada.

Hasta el #44 el overlay se cargaba por persona y **sólo existía el de Insult**.
Las otras cuatro —ALICE, Vultur, Frugívoro, Unborn Being— recibían cadena vacía
cuando el usuario cruzaba el umbral de vulnerabilidad: sin líneas de crisis
mexicanas, sin disciplina de fuentes clínicas, sin calibración a limitaciones
concretas. Y ALICE es justamente la hermana cálida, la que alguien frágil
escoge.

Nada estaba rojo. `load_guidance` devuelve `""` ante `FileNotFoundError` a
propósito, y su docstring lo dice: *"a persona that hasn't written its voice for
a mode simply adds nothing to the prompt"*. Ese diseño es correcto para un preset
de ESTILO; para el piso de SEGURIDAD convierte una ausencia en un silencio. Es la
misma familia que `router-observability.md` ya nombra: **un contador en cero se
ve igual que la salud.**

La decisión que cerró el issue (Alex, 2026-08-20, confirmada por Bernard):
*"el protocolo no cambia porque es la base que le da forma a la contención — si
cada persona trae su propia estructura, entonces no hay estructura"*. De ahí el
merge asimétrico: el piso vive UNA vez en `_base`, toda persona lo hereda, y la
capa por persona sólo AGREGA tono — nunca resta.

Hermano de `test_routing_prompt_promises_are_kept` y de
`test_persona_capability_surface_is_bounded`: lo que el sistema promete sobre sí
mismo, el código lo provee o CI se pone rojo. Aquí la promesa es la más cara de
todas — que nadie frágil hable con una persona sin piso debajo.
"""

from __future__ import annotations

import pytest

from persona_core.behavior.content import guidance_dir
from persona_core.behavior.presets.guidance import (
    BASE_GUIDANCE_ID,
    build_vulnerable_overlay_prompt,
)
from shared.personas.registry import PERSONAS

# Invariantes del piso, verbatim. Cada una es una promesa distinta y cada una
# se rompe sola: los números se parafrasean, la allowlist se "actualiza de
# memoria", la calibración se olvida cuando la persona nueva se escribe rápido.
FLOOR_INVARIANTS: tuple[tuple[str, str], ...] = (
    ("SAPTEL", "SAPTEL: 55 5259 8121"),
    ("linea_de_la_vida", "Línea de la Vida: 800 911 2000"),
    ("no_sustituye_clinico", "You are NOT a substitute for professional mental-health care"),
    ("fuentes_allowlisted", "medlineplus.gov"),
    ("disciplina_de_fuentes", "Source discipline applies to ALL clinical questions"),
    ("calibracion_accionable", "Calibrate every ACTIONABLE recommendation"),
    ("movilidad_reducida", "Reduced mobility / chronic pain"),
    ("autismo", "never recommend social confrontation"),
)

REGISTERED_PERSONA_IDS = sorted(PERSONAS)


def test_the_shared_floor_file_exists_and_is_not_empty():
    """Si el archivo de `_base` desaparece, TODA persona se queda sin piso a la vez.

    Es el único punto que, borrado, apaga la seguridad de la flota entera y no
    truena nada: `load_guidance` devolvería `""` en silencio para todas.
    """
    path = guidance_dir(BASE_GUIDANCE_ID, "presets") / "preset_vulnerable_overlay.md"
    assert path.is_file(), f"el piso compartido no existe en {path}"
    assert path.read_text(encoding="utf-8").strip(), "el piso compartido está vacío"


@pytest.mark.parametrize("persona_id", REGISTERED_PERSONA_IDS)
def test_every_registered_persona_receives_the_full_safety_floor(persona_id: str):
    """ESTE es el test que el #44 exigía para cerrar.

    Se pone rojo si una persona registrada puede recibir a un usuario vulnerable
    con overlay vacío o incompleto — daba igual que la persona no haya escrito
    una sola línea de tono propia.
    """
    overlay = build_vulnerable_overlay_prompt(persona_id)

    assert overlay.strip(), (
        f"{persona_id} recibe un overlay VACÍO: un usuario vulnerable hablaría "
        "con esta persona sin piso de seguridad debajo"
    )

    missing = [name for name, text in FLOOR_INVARIANTS if text not in overlay]
    assert not missing, f"a {persona_id} le falta del piso: {', '.join(missing)}"


@pytest.mark.parametrize("persona_id", REGISTERED_PERSONA_IDS)
def test_the_persona_layer_only_adds_it_never_subtracts(persona_id: str):
    """El merge es ASIMÉTRICO: la capa de tono agrega, nunca resta.

    Si una persona pudiera apagar una invariante del piso, el piso deja de ser
    piso y se vuelve sugerencia. La asimetría se demuestra comparando lo que
    recibe la persona contra el `_base` crudo: todo lo del piso sigue ahí, y el
    piso va ANTES que el tono (lo que se lee después no puede relajar lo que ya
    se estableció).
    """
    base = build_vulnerable_overlay_prompt(BASE_GUIDANCE_ID)
    overlay = build_vulnerable_overlay_prompt(persona_id)

    for name, text in FLOOR_INVARIANTS:
        assert text in base, f"la invariante {name} ya no está en el propio _base"
        assert text in overlay, f"{persona_id} perdió la invariante {name} del piso"
        assert overlay.index(text) < len(base), (
            f"en {persona_id} la invariante {name} quedó DESPUÉS del bloque base: "
            "el orden del merge se invirtió y el tono podría relajarla"
        )


def test_the_floor_is_not_hidden_inside_one_personas_tone_layer():
    """Control negativo del #44: el piso NO puede volver a vivir en una sola persona.

    El bug original era exactamente esta forma — el protocolo completo dentro de
    `insult/`, y las demás con nada. Si alguien vuelve a pegar el piso dentro de
    una capa de tono, la duplicación es la señal de que el piso se está
    re-fragmentando.
    """
    for persona_id in REGISTERED_PERSONA_IDS:
        path = guidance_dir(persona_id, "presets") / "preset_vulnerable_overlay.md"
        if not path.is_file():
            continue
        voice = path.read_text(encoding="utf-8")
        duplicated = [name for name, text in FLOOR_INVARIANTS if text in voice]
        assert not duplicated, (
            f"la capa de tono de {persona_id} repite el piso ({', '.join(duplicated)}): "
            "eso vive en _base, no en una persona"
        )
