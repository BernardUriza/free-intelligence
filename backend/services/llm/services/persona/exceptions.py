"""
Persona Exceptions - Free Intelligence v2.0

Custom exception types for persona-related errors.
"""


class PersonaError(RuntimeError):
    """Base exception for persona-related errors."""

    pass


class PersonaNotFound(PersonaError):
    """Raised when a requested persona does not exist.

    Attributes:
        persona: The persona identifier that was not found
        available: List of available persona identifiers
    """

    def __init__(self, persona: str, available: list[str] | None = None):
        self.persona = persona
        self.available = available or []
        available_str = ", ".join(sorted(self.available)) if self.available else "none"
        super().__init__(f"Unknown persona: {persona}. Available: {available_str}")


class PersonaConfigInvalid(PersonaError):
    """Raised when persona configuration fails validation.

    Attributes:
        persona: The persona identifier with invalid config
        reason: Description of the validation failure
    """

    def __init__(self, persona: str, reason: str):
        self.persona = persona
        self.reason = reason
        super().__init__(f"Invalid configuration for persona '{persona}': {reason}")
