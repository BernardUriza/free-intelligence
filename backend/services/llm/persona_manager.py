"""
PersonaManager - Free Intelligence

Gestiona diferentes "personas" (modos) del asistente Free-Intelligence.

ARQUITECTURA (Template + Override Pattern):
- Templates: /backend/config/personas/*.yaml (immutable base, version-controlled)
- Overrides: PostgreSQL user_persona_configs table (per-user customizations)
- Merge logic: User override takes precedence, NULL = use template default

Personas disponibles:
- onboarding_guide: Presentación en onboarding (obsesiva, empática, filosa)
- soap_editor: Editor de notas SOAP (preciso, médico)
- clinical_advisor: Asesor clínico (basado en evidencia)
- general_assistant: Asistente general médico

Multi-tenancy:
- Each user gets cloned personas from templates on signup
- Users can customize prompts, temperature, max_tokens independently
- Template updates don't affect existing user customizations
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from backend.models.db_models import UserPersonaConfig


@dataclass
class PersonaConfig:
    """Configuración de una persona del asistente."""

    persona: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 2048
    description: str = ""
    voice: str = "nova"  # Azure TTS voice (nova, alloy, echo, fable, onyx, shimmer)


class PersonaManager:
    """Gestor de personas de Free-Intelligence.

    Carga configuraciones desde /backend/config/personas/*.yaml
    No embebe prompts en código - solo parámetros.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """Inicializa el gestor de personas.

        Args:
            config_dir: Directorio de configs (default: /backend/config/personas/)
        """
        self._personas: dict[str, PersonaConfig] = {}
        self._config_dir = config_dir or (
            Path(__file__).parent.parent.parent / "config" / "personas"
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
                self._personas[persona_name] = PersonaConfig(  # type: ignore[call-arg]
                    persona=persona_name,
                    system_prompt=config_data["system_prompt"],
                    temperature=config_data.get("temperature", 0.7),
                    max_tokens=config_data.get("max_tokens", 2048),
                    description=config_data.get("description", ""),
                    voice=config_data.get("voice", "nova"),
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

    def route_persona(self, user_message: str) -> str:
        """Intelligent persona routing using Two-Model Strategy.

        Uses cheap Haiku ($0.25/1M tokens) to decide which persona
        is most appropriate for the user's query.

        Cost optimization:
        - Routing: $0.00003 per query (Haiku)
        - Response: $0.005 per query (GPT-4/Sonnet)
        - Benefit: Auto-selects best persona without user knowledge

        Args:
            user_message: User's input message

        Returns:
            Persona name (e.g., "clinical_advisor", "soap_editor")
        """
        # TODO: Implement actual Haiku routing call
        # For now, use rule-based routing

        message_lower = user_message.lower()

        # Rule-based routing (fallback until Haiku integration)
        if any(
            keyword in message_lower
            for keyword in ["soap", "nota", "documentar", "transcripción", "editar"]
        ):
            return "soap_editor"
        elif any(
            keyword in message_lower
            for keyword in [
                "diagnóstico",
                "tratamiento",
                "evidencia",
                "guidelines",
                "recomendación",
            ]
        ):
            return "clinical_advisor"
        elif any(keyword in message_lower for keyword in ["hola", "bienvenid", "ayuda", "qué"]):
            return "onboarding_guide"
        else:
            return "general_assistant"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MULTI-TENANT PERSONA MANAGEMENT (Template + Override Pattern)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_user_persona(self, persona: str, user_id: str, db: Session) -> PersonaConfig:
        """Get persona config with user-specific overrides merged.

        Architecture: Template + Override Pattern
        1. Load base template from YAML
        2. Query user_persona_configs for overrides
        3. Merge: user override takes precedence, NULL = use template

        Args:
            persona: Persona identifier (e.g., "soap_editor")
            user_id: User UUID
            db: SQLAlchemy session

        Returns:
            PersonaConfig with user overrides applied

        Raises:
            ValueError: If persona doesn't exist in templates
        """
        # 1. Load base template
        template = self.get_persona(persona)

        # 2. Query user overrides
        override = (
            db.query(UserPersonaConfig).filter_by(user_id=user_id, persona_id=persona).first()
        )

        # 3. No override = return template as-is
        if override is None:
            return template

        # 4. Merge: user override takes precedence
        return PersonaConfig(
            persona=persona,
            system_prompt=override.custom_prompt or template.system_prompt,
            temperature=override.temperature
            if override.temperature is not None
            else template.temperature,
            max_tokens=override.max_tokens
            if override.max_tokens is not None
            else template.max_tokens,
            voice=override.voice if override.voice is not None else template.voice,
            description=template.description,  # Description always from template
        )

    def clone_personas_for_user(self, user_id: str, db: Session) -> list[str]:
        """Clone all template personas for a new user (onboarding seed).

        Creates user_persona_configs entries with all NULL overrides,
        meaning user starts with exact template defaults but can customize later.

        Args:
            user_id: User UUID
            db: SQLAlchemy session

        Returns:
            List of cloned persona IDs
        """
        cloned = []

        for persona_id in self.list_personas():
            # Check if already exists
            existing = (
                db.query(UserPersonaConfig)
                .filter_by(user_id=user_id, persona_id=persona_id)
                .first()
            )

            if existing is not None:
                continue  # Already cloned

            # Create with all NULL overrides (= use template defaults)
            config = UserPersonaConfig(
                user_id=user_id,
                persona_id=persona_id,
                custom_prompt=None,  # NULL = use template
                temperature=None,  # NULL = use template
                max_tokens=None,  # NULL = use template
                is_active=True,
            )
            db.add(config)
            cloned.append(persona_id)

        db.commit()
        return cloned

    def update_user_persona(
        self,
        user_id: str,
        persona_id: str,
        db: Session,
        custom_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        voice: str | None = None,
    ) -> PersonaConfig:
        """Update user's persona overrides.

        Args:
            user_id: User UUID
            persona_id: Persona identifier
            db: SQLAlchemy session
            custom_prompt: Override system prompt (None = keep current)
            temperature: Override temperature (None = keep current)
            max_tokens: Override max tokens (None = keep current)
            voice: Override Azure TTS voice (None = keep current)

        Returns:
            Updated PersonaConfig with overrides applied

        Raises:
            ValueError: If persona doesn't exist in templates
        """
        # Verify persona exists in templates
        self.get_persona(persona_id)  # Raises ValueError if not found

        # Get or create user config
        config = (
            db.query(UserPersonaConfig).filter_by(user_id=user_id, persona_id=persona_id).first()
        )

        if config is None:
            # Create new override entry
            config = UserPersonaConfig(
                user_id=user_id,
                persona_id=persona_id,
                custom_prompt=custom_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                voice=voice,
                is_active=True,
            )
            db.add(config)
        else:
            # Update existing overrides (only non-None values)
            if custom_prompt is not None:
                config.custom_prompt = custom_prompt
            if temperature is not None:
                config.temperature = temperature
            if max_tokens is not None:
                config.max_tokens = max_tokens
            if voice is not None:
                config.voice = voice

        db.commit()
        db.refresh(config)

        # Return merged config
        return self.get_user_persona(persona_id, user_id, db)
