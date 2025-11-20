"""
PersonaManager - Free Intelligence

Gestiona diferentes "personas" (modos) del asistente Free-Intelligence.

ARQUITECTURA:
- Prompts: /config/personas/*.yaml (NO en código)
- Código: Solo parámetros y lógica de carga

Personas disponibles:
- onboarding_guide: Presentación en onboarding (obsesiva, empática, filosa)
- soap_editor: Editor de notas SOAP (preciso, médico)
- clinical_advisor: Asesor clínico (basado en evidencia)
- general_assistant: Asistente general médico
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class PersonaConfig:
    """Configuración de una persona del asistente."""

    persona: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 2048
    description: str = ""


class PersonaManager:
    """Gestor de personas de Free-Intelligence.

    Carga configuraciones desde /config/personas/*.yaml
    No embebe prompts en código - solo parámetros.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """Inicializa el gestor de personas.

        Args:
            config_dir: Directorio de configs (default: /config/personas/)
        """
        self._personas: dict[str, PersonaConfig] = {}
        self._config_dir = config_dir or (
            Path(__file__).parent.parent.parent.parent / "config" / "personas"
        )
        self._load_personas()

    def _load_personas(self) -> None:
        """Carga todas las personas desde archivos YAML."""
        if not self._config_dir.exists():
            raise FileNotFoundError(f"Personas config directory not found: {self._config_dir}")

        for yaml_file in self._config_dir.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)

                persona_name = config_data["persona"]
                self._personas[persona_name] = PersonaConfig(
                    persona=persona_name,
                    system_prompt=config_data["system_prompt"],
                    temperature=config_data.get("temperature", 0.7),
                    max_tokens=config_data.get("max_tokens", 2048),
                    description=config_data.get("description", ""),
                )
            except Exception as e:
                # Log pero no fallar si una persona no carga
                print(f"Warning: Failed to load persona from {yaml_file}: {e}")

    def get_persona(self, persona: str) -> PersonaConfig:
        """Obtiene la configuración de una persona.

        Args:
            persona: Nombre de la persona

        Returns:
            PersonaConfig con system_prompt, temperature, etc.

        Raises:
            ValueError: Si la persona no existe
        """
        if persona not in self._personas:
            available = ", ".join(self._personas.keys())
            raise ValueError(f"Unknown persona: {persona}. Available: {available}")

        return self._personas[persona]

    def list_personas(self) -> list[str]:
        """Lista todas las personas disponibles."""
        return list(self._personas.keys())

    def get_persona_description(self, persona: str) -> str:
        """Obtiene la descripción de una persona."""
        config = self.get_persona(persona)
        return config.description

    def build_system_prompt(self, persona: str, context: dict | None = None) -> str:
        """Construye el system prompt ajustado por contexto (response_mode, etc).

        Args:
            persona: Nombre de la persona
            context: Contexto del usuario (response_mode, doctor_name, etc.)

        Returns:
            System prompt modificado según el contexto
        """
        config = self.get_persona(persona)
        base_prompt = config.system_prompt

        # Ajustar según response_mode
        context = context or {}
        mode = context.get("response_mode", "explanatory")

        instruction_map = {
            "concise": "Responde de manera breve y directa (máximo 3-4 oraciones).",
            "explanatory": "Responde de manera detallada y educativa.",
        }

        # Fallback a explanatory si el modo es desconocido
        instruction = instruction_map.get(mode, instruction_map["explanatory"])

        # Idempotencia: no duplicar la instrucción si ya existe
        if instruction not in base_prompt:
            base_prompt = f"{base_prompt}\n\n{instruction}"

        return base_prompt
