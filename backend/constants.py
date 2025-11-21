"""
Free Intelligence - Centralized Constants

This module consolidates all hardcoded constants from across the backend,
following the DRY (Don't Repeat Yourself) principle.

Created as part of FI-BACKEND-CHORE-001 to eliminate scattered constants.
"""

# ============================================================================
# LLM Provider Models
# ============================================================================

# Claude (Anthropic) Models
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5-20250929"  # Latest official Claude Sonnet 4.5

# Ollama Models (Local Inference)
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_0"  # Default for local inference
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text:latest"  # For embeddings

# ============================================================================
# API Endpoints and URLs
# ============================================================================

# Ollama API Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_API_CHAT_ENDPOINT = "/api/chat"
OLLAMA_API_GENERATE_ENDPOINT = "/api/generate"
OLLAMA_API_EMBEDDINGS_ENDPOINT = "/api/embeddings"

# ============================================================================
# Timeouts and Performance
# ============================================================================

# Request Timeouts (in seconds)
CLAUDE_TIMEOUT_SEC = 60.0  # Claude is typically faster
OLLAMA_TIMEOUT_SEC = 120.0  # Local models may need more time
DEFAULT_API_TIMEOUT = 30.0  # General API timeout

# ============================================================================
# Embedding Dimensions
# ============================================================================

# Standard embedding dimension for HDF5 storage
STANDARD_EMBEDDING_DIM = 768  # Unified dimension for all embeddings

# ============================================================================
# API Versions
# ============================================================================

# Minimum supported versions for compatibility
MIN_OLLAMA_API_VERSION = "0.12"  # Ollama API v0.12+ required
MIN_CLAUDE_API_VERSION = "2023-01-01"  # Claude API version

# ============================================================================
# CORS Configuration
# ============================================================================

# Default allowed origins for CORS
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:9000",
    "http://localhost:9050",
    "https://app.aurity.io",
]

# ============================================================================
# Provider Enums
# ============================================================================


class LLMProvider:
    """LLM Provider identifiers."""

    CLAUDE = "claude"
    OLLAMA = "ollama"
    OPENAI = "openai"  # Future support


# ============================================================================
# Notes
# ============================================================================

"""
Migration Notes:
- Previously these constants were scattered across:
  * backend/services/diarization/llm_diarizer.py
  * backend/schemas/preset_loader.py
  * backend/providers/llm.py
  * backend/app/main.py

API Version Compatibility:
- Ollama API v0.12+ introduced breaking changes in chat format
- Claude API uses ISO 8601 date versioning
- Always check compatibility before upgrading

Usage:
    from backend.constants import DEFAULT_CLAUDE_MODEL, OLLAMA_BASE_URL

    # Use in provider initialization
    model = DEFAULT_CLAUDE_MODEL
    base_url = OLLAMA_BASE_URL
"""
