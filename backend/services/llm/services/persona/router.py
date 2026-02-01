"""
Persona Router - Free Intelligence v2.0

Routes user messages to appropriate personas based on content analysis.
"""

from functools import lru_cache


class PersonaRouter:
    """Routes messages to appropriate personas.

    Uses keyword-based routing with LRU cache for performance.
    Future: Could be extended with ML-based routing.

    Usage:
        router = PersonaRouter()
        persona = router.route("Necesito editar una nota SOAP")  # -> "soap_editor"
    """

    # Routing rules: keyword patterns -> persona
    ROUTING_RULES = {
        "soap_editor": [
            "soap",
            "nota",
            "documentar",
            "transcripción",
            "editar",
        ],
        "clinical_advisor": [
            "diagnóstico",
            "tratamiento",
            "evidencia",
            "guidelines",
            "recomendación",
            "síntomas",
            "medicamento",
        ],
        "onboarding_guide": [
            "hola",
            "bienvenid",
            "ayuda",
            "cómo funciona",
            "empezar",
        ],
    }

    DEFAULT_PERSONA = "general_assistant"

    def __init__(self, default_persona: str | None = None):
        """Initialize router.

        Args:
            default_persona: Fallback persona when no rules match
        """
        self._default = default_persona or self.DEFAULT_PERSONA

    def route(self, message: str) -> str:
        """Route message to appropriate persona.

        Args:
            message: User's input message

        Returns:
            Persona identifier
        """
        return self._route_by_keywords(message.lower())

    @lru_cache(maxsize=256)
    def _route_by_keywords(self, message_lower: str) -> str:
        """Rule-based routing with LRU cache.

        Args:
            message_lower: Lowercase message for matching

        Returns:
            Persona identifier
        """
        for persona, keywords in self.ROUTING_RULES.items():
            if any(kw in message_lower for kw in keywords):
                return persona

        return self._default

    def clear_cache(self) -> None:
        """Clear the routing cache."""
        self._route_by_keywords.cache_clear()
