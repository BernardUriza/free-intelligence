"""LLM API Layer - Internal endpoints for LLM interactions.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Infrastructure Migration)
"""

from .internal import router as internal_router

__all__ = ["internal_router"]
