"""
Persona Config - Free Intelligence v2.0

Immutable runtime configuration dataclasses.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PersonaConfig:
    """Immutable configuration for a persona at runtime.

    This dataclass is frozen (immutable) and uses slots for memory efficiency.
    It represents the final, resolved configuration after all overrides are applied.

    Attributes:
        persona: Unique identifier
        system_prompt: The system prompt to use
        model: LLM model ID (e.g., 'qwen3:1.7b', 'gpt-4o')
        temperature: LLM sampling temperature
        max_tokens: Maximum tokens for response
        description: Human-readable description
        voice: TTS voice name
        template_sha256: Hash of the source template (for cache invalidation)
        template_version: Semantic version from template
        response_format: Optional JSON schema for structured output (Ollama format param)
    """

    persona: str
    system_prompt: str
    model: str = "qwen3:1.7b"
    temperature: float = 0.7
    max_tokens: int = 2048
    description: str = ""
    voice: str = "nova"
    template_sha256: str = ""
    template_version: str = "1.0.0"
    response_format: dict | None = None


@dataclass
class CacheEntry:
    """Cache entry with metadata for hot-reload detection.

    Stores the loaded configuration along with metadata needed to detect
    when the source file has changed and requires reloading.

    Attributes:
        config: The loaded PersonaConfig
        sha256: Hash of the YAML content when loaded
        mtime: File modification time when loaded
        loaded_at: Unix timestamp when this entry was cached
    """

    config: PersonaConfig
    sha256: str
    mtime: float
    loaded_at: float
