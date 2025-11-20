"""
Tests para PersonaManager - response_mode feature

Valida que el sistema prompt se ajuste correctamente según el response_mode
del contexto (concise, explanatory, o valores inválidos).
"""

from pathlib import Path

import pytest

from backend.services.llm.persona_manager import PersonaManager


@pytest.fixture
def persona_manager():
    """Instancia del PersonaManager para testing."""
    # Usa el directorio real de configuraciones (en la raíz del proyecto)
    # Path desde test file: backend/tests/services/llm/test_*.py
    # Subir 4 niveles para llegar a la raíz del proyecto
    project_root = Path(__file__).parent.parent.parent.parent.parent
    config_dir = project_root / "config" / "personas"
    return PersonaManager(config_dir=config_dir)


@pytest.mark.parametrize(
    "context,expected,absent",
    [
        # Default (sin context) -> explanatory
        (
            None,
            "Responde de manera detallada y educativa.",
            "Responde de manera breve y directa (máximo 3-4 oraciones).",
        ),
        # context vacío -> explanatory
        (
            {},
            "Responde de manera detallada y educativa.",
            "Responde de manera breve y directa (máximo 3-4 oraciones).",
        ),
        # explanatory explícito
        (
            {"response_mode": "explanatory"},
            "Responde de manera detallada y educativa.",
            "Responde de manera breve y directa (máximo 3-4 oraciones).",
        ),
        # concise
        (
            {"response_mode": "concise"},
            "Responde de manera breve y directa (máximo 3-4 oraciones).",
            "Responde de manera detallada y educativa.",
        ),
        # valor inválido -> fallback a explanatory
        (
            {"response_mode": "unknown"},
            "Responde de manera detallada y educativa.",
            "Responde de manera breve y directa (máximo 3-4 oraciones).",
        ),
        (
            {"response_mode": "verbose"},
            "Responde de manera detallada y educativa.",
            "Responde de manera breve y directa (máximo 3-4 oraciones).",
        ),
    ],
)
def test_response_mode_instruction(persona_manager, context, expected, absent):
    """Valida que se agregue la instrucción correcta según response_mode."""
    # Usa una persona existente (asumiendo que existe 'general_assistant')
    # Si no existe, el test fallará y mostrará las personas disponibles
    try:
        prompt = persona_manager.build_system_prompt("general_assistant", context)
    except ValueError:
        # Si la persona no existe, usar la primera disponible
        personas = persona_manager.list_personas()
        if not personas:
            pytest.skip("No hay personas configuradas")
        prompt = persona_manager.build_system_prompt(personas[0], context)

    # Verificar que la instrucción esperada está presente
    assert expected in prompt, f"Expected '{expected}' not found in prompt"

    # Verificar que la instrucción contraria NO está presente
    assert absent not in prompt, f"Unexpected '{absent}' found in prompt"


def test_idempotency_no_duplication(persona_manager):
    """Valida que llamar dos veces con el mismo contexto no duplique instrucciones."""
    context = {"response_mode": "concise"}

    try:
        personas = persona_manager.list_personas()
        if not personas:
            pytest.skip("No hay personas configuradas")
        persona = personas[0]
    except Exception:
        pytest.skip("No se pudo obtener una persona válida")

    # Primera llamada
    prompt1 = persona_manager.build_system_prompt(persona, context)

    # Segunda llamada con el mismo contexto
    prompt2 = persona_manager.build_system_prompt(persona, context)

    # Ambas deben ser idénticas
    assert prompt1 == prompt2, "Prompts should be identical"

    # Verificar que la instrucción aparece exactamente una vez
    expected = "Responde de manera breve y directa (máximo 3-4 oraciones)."
    count = prompt1.count(expected)
    assert count == 1, f"Expected instruction to appear exactly once, found {count} times"


def test_response_mode_preserves_base_prompt(persona_manager):
    """Valida que agregar response_mode no modifique el prompt base de la persona."""
    try:
        personas = persona_manager.list_personas()
        if not personas:
            pytest.skip("No hay personas configuradas")
        persona = personas[0]
    except Exception:
        pytest.skip("No se pudo obtener una persona válida")

    # Prompt con contexto
    contextualized_prompt = persona_manager.build_system_prompt(
        persona, {"response_mode": "concise"}
    )

    # El prompt contextualizado debe contener el base prompt
    # (pero puede tener contenido adicional al final)
    config = persona_manager.get_persona(persona)
    base_content = config.system_prompt

    assert base_content in contextualized_prompt, "Base prompt should be preserved"


def test_all_personas_support_response_mode(persona_manager):
    """Valida que todas las personas configuradas soporten response_mode."""
    personas = persona_manager.list_personas()

    if not personas:
        pytest.skip("No hay personas configuradas")

    for persona in personas:
        # Test concise
        prompt_concise = persona_manager.build_system_prompt(persona, {"response_mode": "concise"})
        assert "Responde de manera breve y directa (máximo 3-4 oraciones)." in prompt_concise

        # Test explanatory
        prompt_explanatory = persona_manager.build_system_prompt(
            persona, {"response_mode": "explanatory"}
        )
        assert "Responde de manera detallada y educativa." in prompt_explanatory
