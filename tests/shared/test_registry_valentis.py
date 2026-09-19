"""Valentis (2026-08-25) — la persona de acompañamiento, registrada de verdad.

Positivo: existe en el registry con su ADN, su guidance y su bot id real.
Resistencia — y es la mitad que importa: que estar registrada NO le abrió el
ruteo por tema. La revelación personal sigue siendo de insult, el host, por dos
incidentes reales que pusieron esa regla en `host_routing.md`. Una persona de
acompañamiento es exactamente la que un futuro editor tendría la tentación de
volver el destino natural del dolor; el test de abajo se pone rojo si lo hace.
"""

from __future__ import annotations

from pathlib import Path

from demux_ai import llm_shadow_router
from shared.personas import gateway_personas, get_persona
from shared.personas.registry import persona_id_by_role_name

ROOT = Path(__file__).parents[2]


def test_valentis_is_a_registered_persona():
    v = get_persona("valentis")
    assert v is not None
    assert v.persona_file == "valentis.md"
    assert v.token_env == "VALENTIS_DISCORD_TOKEN"  # noqa: S105 — env-var NAME, not a secret
    assert v.bot_user_id == "1541815100023767131"
    assert v.gateway_enabled is True


def test_valentis_stays_mention_only():
    """El issue #43 lo pide explícito: una palabra suelta que la despierte en una
    conversación que no era para ella es, EN ESTE TEMA, peor que no estar."""
    v = get_persona("valentis")
    assert v.aliases == []


def test_valentis_has_her_corpus_and_it_tells_her_when_not_to_cite():
    """Fase 2 abierta el 2026-09-16 (#61 B, decisión de Álex): era la única de las
    seis sin corpus, y entra con ética del cuidado.

    La resistencia de ESTE test es el header: en las demás personas citar la
    procedencia es siempre lo correcto; aquí no. A alguien que está mal no se le
    cita literatura, y su ADN nace justo de la referencia sin tacto que "se siente
    como una puerta cerrándose". Si un futuro editor le quita esa cláusula para
    homogeneizar los headers, esto se pone rojo.
    """
    v = get_persona("valentis")
    assert v.corpus_namespace == "__corpus_valentis__"

    header = ROOT / "shared" / "corpus" / "headers" / "valentis.md"
    assert header.is_file()
    texto = header.read_text(encoding="utf-8").lower()
    assert "antes de citar, decide si citar viene al caso" in texto
    assert "no se le cita literatura" in texto

    manifest = ROOT / "data" / "corpus" / "valentis" / "MANIFEST.md"
    assert manifest.is_file(), "el MANIFEST viaja con el repo aunque las fuentes no"


def test_valentis_dna_and_guidance_are_in_place():
    dna = ROOT / "shared" / "personas" / "valentis.md"
    assert dna.is_file()
    assert dna.stat().st_size > 1000
    preset = ROOT / "shared" / "personas" / "guidance" / "valentis" / "presets"
    assert (preset / "preset_guidance_respectful_serious.md").is_file()


def test_valentis_is_gateway_enabled():
    assert any(p.persona_id == "valentis" for p in gateway_personas())


def test_valentis_resolves_from_a_role_named_exactly_like_her():
    assert persona_id_by_role_name("Valentis") == "valentis"


def test_valentis_is_a_routable_target_the_prompt_actually_describes():
    """Un target que el parser acepta pero el prompt no describe es una persona
    inalcanzable en silencio — la falla de frugívoro del 2026-07-06."""
    assert "valentis" in llm_shadow_router._VALID_TARGETS
    instr = llm_shadow_router._routing_instruction().lower()
    assert "valentis" in instr
    assert '"valentis" -> valentis' in instr


def test_registering_valentis_did_not_hand_her_the_confession():
    """LA resistencia. El #43 prohíbe abrir el ruteo del desahogo personal, y esa
    regla se mide con `scripts/router_eval.py` contra el set congelado, no se
    cambia de pasada al registrar una persona nueva."""
    instr = llm_shadow_router._routing_instruction().lower()

    # sigue en pie la cláusula que le da la confesión al host
    assert "personal disclosure and emotional weight belong to insult" in instr

    # y la entrada de valentis dice, textual, que no es el destino del dolor
    linea = next(ln for ln in instr.splitlines() if ln.startswith("- valentis:"))
    assert "only when the user explicitly asks for valentis by name" in linea
    assert "never route to valentis on topic" in linea
    assert "stay with insult" in linea
