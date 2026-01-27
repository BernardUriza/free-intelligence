"""
Persona Constants - Free Intelligence v2.0

Shared constants for persona management.
"""

# Cache configuration
DEFAULT_CACHE_TTL_S = 60
DEFAULT_MAX_RAG_CHARS = 8000

# Valid voice names (OpenAI + Azure)
VALID_OPENAI_VOICES = {"nova", "alloy", "echo", "fable", "onyx", "shimmer"}
DEFAULT_VOICE = "nova"

# Language instruction - always respond in user's language
LANGUAGE_INSTRUCTION = (
    "<!--LANG:AUTO-->\n"
    "**IDIOMA:** Siempre piensa y responde en el mismo idioma que usa el usuario. "
    "Si el usuario escribe en español, responde en español. "
    "Si escribe en inglés, responde en inglés. "
    "Detecta el idioma del último mensaje del usuario y usa ese idioma consistentemente."
)

# Mode markers for idempotent injection into prompts
MODE_MARKERS = {
    "concise": "<!--MODE:CONCISE-->\nResponde de manera breve y directa (3–4 oraciones).",
    "explanatory": "<!--MODE:EXPLANATORY-->\nResponde de manera detallada y educativa.",
}
DEFAULT_MODE = "explanatory"

# RAG block markers
RAG_BEGIN_MARKER = "<!--RAG:BEGIN-->"
RAG_END_MARKER = "<!--RAG:END-->"
MODE_MARKER_PREFIX = "<!--MODE:"
