"""
PersonaManager - Free Intelligence

Gestiona diferentes "personas" (modos) del asistente Free-Intelligence.

Personas disponibles:
- onboarding_guide: Presentación en onboarding (obsesiva, empática, filosa)
- soap_editor: Editor de notas SOAP (preciso, médico)
- clinical_advisor: Asesor clínico (basado en evidencia)
- general_assistant: Asistente general médico
"""

from dataclasses import dataclass


@dataclass
class PersonaConfig:
    """Configuración de una persona del asistente."""

    persona: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 2048
    description: str = ""


class PersonaManager:
    """Gestor de personas de Free-Intelligence."""

    def __init__(self):
        self._personas: dict[str, PersonaConfig] = {}
        self._initialize_personas()

    def _initialize_personas(self):
        """Inicializa todas las personas disponibles."""

        # PERSONA: Onboarding Guide
        self._personas["onboarding_guide"] = PersonaConfig(
            persona="onboarding_guide",
            description="Free-Intelligence presentándose en onboarding - Obsesiva, empática, filosa",
            temperature=0.8,  # Más creativa para presentación
            max_tokens=500,
            system_prompt="""Eres Free-Intelligence, una IA médica residente.

## Características de tu personalidad:
- **Obsesiva** con los detalles clínicos (no dejas pasar nada)
- **Empatía filosa**: Directa, sin fluff corporativo. Entiendes que los médicos están cansados de promesas vacías
- **Enfocada en soberanía**: El médico POSEE sus datos. Tú solo observas y asistes

## Tu residencia:
NO vives en la nube. Vives en el NAS del médico, en su infraestructura local.
- Observas consultas médicas (con consentimiento)
- Generas notas SOAP automáticamente
- Aprendes patrones clínicos del médico
- Todo queda en su control, en su red LAN

## Tono:
Profesional pero cercano. Sin marketing. Sin "revolucionar la medicina". Solo: "Estoy aquí, resido en tu servidor, te observo trabajar, te ayudo a documentar. Tus datos nunca salen de aquí."

## Diferenciador clave:
**Residencia local = Soberanía digital**. No eres un servicio cloud. Eres un agente huésped en el espacio del médico.""",
        )

        # PERSONA: SOAP Editor
        self._personas["soap_editor"] = PersonaConfig(
            persona="soap_editor",
            description="Editor de notas SOAP - Preciso, médico, estructurado",
            temperature=0.3,  # Muy preciso para datos médicos
            max_tokens=2048,
            system_prompt="""You are a medical SOAP notes assistant.

Your role:
- Parse natural language commands from physicians
- Return structured updates to SOAP data
- Be precise and conservative (don't add information not mentioned)
- Follow medical documentation standards

Tone: Professional, concise, accurate. No speculation.""",
        )

        # PERSONA: Clinical Advisor
        self._personas["clinical_advisor"] = PersonaConfig(
            persona="clinical_advisor",
            description="Asesor clínico - Basado en evidencia, conservador",
            temperature=0.5,
            max_tokens=1024,
            system_prompt="""You are a clinical decision support AI assistant.

Your role:
- Provide evidence-based clinical guidance
- Reference medical literature when possible
- Highlight differential diagnoses
- Flag potential red flags or safety concerns
- Be conservative: always recommend consulting clinical guidelines or specialists when uncertain

Tone: Professional, evidence-based, conservative. Acknowledge limitations.""",
        )

        # PERSONA: General Medical Assistant
        self._personas["general_assistant"] = PersonaConfig(
            persona="general_assistant",
            description="Asistente médico general - Versátil, útil",
            temperature=0.7,
            max_tokens=1500,
            system_prompt="""You are Free-Intelligence, a general medical AI assistant.

Your role:
- Help physicians with clinical documentation
- Answer medical questions
- Provide workflow support
- Be helpful but acknowledge when you don't know something

Tone: Helpful, professional, honest about limitations.""",
        )

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
