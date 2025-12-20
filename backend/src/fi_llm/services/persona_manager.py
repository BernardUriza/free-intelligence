"""
PersonaManager - Free Intelligence v2.0

DEPRECATED: This file is maintained for backward compatibility.
Import from backend.services.llm.persona instead.

Example:
    from backend.services.llm.persona import PersonaManager, PersonaConfig, PersonaNotFound
"""

# Re-export everything from the new modular structure
from backend.services.llm.persona import (
    DEFAULT_CACHE_TTL_S,
    DEFAULT_MAX_RAG_CHARS,
    MODE_MARKERS,
    CacheEntry,
    PersonaConfig,
    PersonaConfigInvalid,
    PersonaError,
    PersonaManager,
    PersonaNotFound,
    PersonaRouter,
    PersonaTemplateModel,
    PromptBuilder,
)

__all__ = [
    # Constants
    "DEFAULT_CACHE_TTL_S",
    "DEFAULT_MAX_RAG_CHARS",
    "MODE_MARKERS",
    # Exceptions
    "PersonaError",
    "PersonaNotFound",
    "PersonaConfigInvalid",
    # Schemas
    "PersonaTemplateModel",
    # Config
    "PersonaConfig",
    "CacheEntry",
    # Classes
    "PromptBuilder",
    "PersonaRouter",
    "PersonaManager",
]


# ============================================================================
# CLI (Dev Tool)
# ============================================================================

if __name__ == "__main__":
    import sys

    manager = PersonaManager()

    if len(sys.argv) < 2:
        print("Usage: python -m backend.services.llm.persona_manager [ls|show <persona>]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "ls":
        print("Available personas:")
        for p in manager.list_personas():
            config = manager.get_persona(p)
            print(f"  - {p} (v{config.template_version}, sha:{config.template_sha256})")

    elif cmd == "show" and len(sys.argv) >= 3:
        persona = sys.argv[2]
        try:
            config = manager.get_persona(persona)
            print(f"Persona: {config.persona}")
            print(f"Version: {config.template_version}")
            print(f"SHA256: {config.template_sha256}")
            print(f"Temperature: {config.temperature}")
            print(f"Max Tokens: {config.max_tokens}")
            print(f"Voice: {config.voice}")
            print(f"Description: {config.description}")
            print(f"\nSystem Prompt:\n{config.system_prompt[:500]}...")
        except PersonaNotFound as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Unknown command. Use 'ls' or 'show <persona>'")
        sys.exit(1)
