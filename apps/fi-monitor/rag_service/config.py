"""RAG Service configuration constants."""

from __future__ import annotations

import os

# Model: Same as backend for consistency
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Security: API key for authentication
RAG_API_KEY = os.getenv("RAG_API_KEY", "change-me-in-production")

# GPU Requirement: Fail-hard if no GPU (override: RAG_REQUIRE_GPU=false)
RAG_REQUIRE_GPU = os.getenv("RAG_REQUIRE_GPU", "true").lower() in ("true", "1", "yes")
