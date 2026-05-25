"""FI Prompts - Centralized Prompt Library.

This package provides a standardized way to manage and retrieve
prompts across the Free Intelligence application.

Features:
- Template-based prompts with parameter injection
- Standardized prompt types
- YAML preset integration
- CLI access to prompts
- Extensible architecture for new prompt types

Usage:
    from backend.utils.prompts import get_prompt

    # Get a medical consultation prompt with parameters
    prompt = get_prompt(
        "medical_consultation",
        demographics="65-year-old male",
        chief_complaint="Chest pain for 2 hours",
        medications="Aspirin, Metformin, Lisinopril",
        allergies="Penicillin (rash)",
    )
"""

from backend.utils.prompts.prompt_provider import (
    PromptProvider,
    PromptType,
    get_available_prompts,
    get_prompt,
    get_prompt_provider,
)

__all__ = [
    "PromptProvider",
    "PromptType",
    "get_available_prompts",
    "get_prompt",
    "get_prompt_provider",
]
