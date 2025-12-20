"""
Persona Schemas - Free Intelligence v2.0

Pydantic models for validating persona YAML templates.
"""

from pydantic import BaseModel, Field, field_validator

from .constants import DEFAULT_VOICE, VALID_OPENAI_VOICES


class PersonaTemplateModel(BaseModel):
    """Schema for validating YAML persona templates.

    This model validates the structure and values of persona YAML files.
    It supports both OpenAI and Azure voice names for TTS compatibility.

    Attributes:
        persona: Unique identifier for the persona (1-64 chars)
        description: Human-readable description
        system_prompt: The system prompt template (min 20 chars)
        temperature: LLM temperature (0.0-1.0)
        max_tokens: Maximum response tokens (256-8192)
        voice: TTS voice name (OpenAI or Azure)
        version: Semantic version string
    """

    persona: str = Field(..., min_length=1, max_length=64)
    description: str = Field(default="")
    system_prompt: str = Field(..., min_length=20)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=256, le=8192)
    voice: str = Field(default=DEFAULT_VOICE)
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$|^\d+$")

    # Optional fields that may exist in YAML but we don't use in config
    model: str | None = None
    examples: list | None = None
    created_at: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None

    @field_validator("voice", mode="before")
    @classmethod
    def validate_voice(cls, v: str) -> str:
        """Validate voice name - accept both OpenAI and Azure voices."""
        if v in VALID_OPENAI_VOICES or v.startswith("es-MX-"):
            return v
        # Default fallback
        return DEFAULT_VOICE

    @field_validator("version", mode="before")
    @classmethod
    def normalize_version(cls, v) -> str:
        """Normalize version to semver format."""
        if isinstance(v, int):
            return f"{v}.0.0"
        return str(v)
