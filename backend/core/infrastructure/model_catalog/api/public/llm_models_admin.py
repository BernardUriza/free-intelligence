"""LLM Models Admin API - Manage AI Model Configurations.

PUBLIC endpoint for managing LLM models available for persona assignment.
Superadmin only - CRUD operations on model configurations.

Author: Bernard Uriza Orozco
Created: 2025-12-11
"""

from __future__ import annotations

import random

import httpx
from backend.models.llm_model import (
    CostTier,
    LLMModelCreate,
    LLMModelResponse,
    LLMModelUpdate,
    LLMProvider,
)
from backend.services.llm.services.llm_model_service import llm_model_service
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

# Medical test prompts for model validation
MEDICAL_TEST_PROMPTS = [
    "Explica brevemente qué es la presión arterial y por qué es importante medirla.",
    "¿Qué es la diabetes tipo 2 y cuáles son sus síntomas principales?",
    "Describe en 2-3 oraciones qué es una frecuencia cardíaca normal en adultos.",
    "¿Qué significa tener el colesterol alto y cómo afecta la salud?",
    "Explica qué es la hemoglobina y por qué se mide en análisis de sangre.",
    "¿Qué es un electrocardiograma (ECG) y para qué se utiliza?",
    "Describe brevemente qué es la saturación de oxígeno en sangre.",
    "¿Qué son las vacunas y cómo protegen al cuerpo de enfermedades?",
]


class ModelTestResponse(BaseModel):
    """Response from testing an LLM model."""

    success: bool
    model_id: str
    prompt: str
    response: str
    error: str | None = None


router = APIRouter(prefix="/admin/llm-models", tags=["LLM Models Admin"])


@router.get("", response_model=list[LLMModelResponse])
async def list_llm_models(
    include_inactive: bool = Query(False, description="Include inactive models"),
    provider: str | None = Query(None, description="Filter by provider"),
) -> list[LLMModelResponse]:
    """List all available LLM models.

    Returns:
        List of LLM model configurations
    """
    if provider:
        try:
            provider_enum = LLMProvider(provider)
            models = llm_model_service.get_models_by_provider(provider_enum)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider: {provider}. Valid: openai, anthropic, azure",
            ) from err
    else:
        models = llm_model_service.list_models(include_inactive=include_inactive)

    return [LLMModelResponse.from_model(m) for m in models]


@router.get("/{model_id}", response_model=LLMModelResponse)
async def get_llm_model(model_id: str) -> LLMModelResponse:
    """Get a specific LLM model by ID.

    Args:
        model_id: Model identifier (e.g., 'gpt-4o')

    Returns:
        LLM model configuration
    """
    model = llm_model_service.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )
    return LLMModelResponse.from_model(model)


@router.post("", response_model=LLMModelResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_model(data: LLMModelCreate) -> LLMModelResponse:
    """Create a new LLM model configuration.

    Args:
        data: Model creation data

    Returns:
        Created LLM model
    """
    try:
        model = llm_model_service.create_model(data)
        return LLMModelResponse.from_model(model)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.put("/{model_id}", response_model=LLMModelResponse)
async def update_llm_model(model_id: str, data: LLMModelUpdate) -> LLMModelResponse:
    """Update an existing LLM model configuration.

    Args:
        model_id: Model identifier
        data: Update data

    Returns:
        Updated LLM model
    """
    model = llm_model_service.update_model(model_id, data)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )
    return LLMModelResponse.from_model(model)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_model(
    model_id: str,
    hard_delete: bool = Query(False, description="Permanently delete instead of deactivating"),
) -> None:
    """Delete or deactivate an LLM model.

    By default, performs soft delete (deactivation).
    Use hard_delete=true to permanently remove.

    Args:
        model_id: Model identifier
        hard_delete: If true, permanently delete
    """
    success = llm_model_service.delete_model(model_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )


@router.get("/providers/list", response_model=list[str])
async def list_providers() -> list[str]:
    """List all available LLM providers.

    Returns:
        List of provider names
    """
    return [p.value for p in LLMProvider]


@router.get("/cost-tiers/list", response_model=list[str])
async def list_cost_tiers() -> list[str]:
    """List all available cost tiers.

    Returns:
        List of cost tier names
    """
    return [t.value for t in CostTier]


@router.post("/{model_id}/test", response_model=ModelTestResponse)
async def test_llm_model(model_id: str) -> ModelTestResponse:
    """Test an LLM model with a random medical prompt.

    Sends a simple medical question to the model and returns the response.
    Useful for validating model installation and basic functionality.

    Args:
        model_id: Model identifier (e.g., 'llama3:8b')

    Returns:
        Test result with prompt and model response
    """
    model = llm_model_service.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    # Select random medical prompt
    prompt = random.choice(MEDICAL_TEST_PROMPTS)

    try:
        if model.provider == LLMProvider.OLLAMA:
            response_text = await _test_ollama_model(model_id, prompt)
        elif model.provider == LLMProvider.OPENAI:
            response_text = await _test_openai_model(model_id, prompt)
        elif model.provider == LLMProvider.ANTHROPIC:
            response_text = await _test_anthropic_model(model_id, prompt)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Testing not supported for provider: {model.provider}",
            )

        return ModelTestResponse(
            success=True,
            model_id=model_id,
            prompt=prompt,
            response=response_text,
        )

    except HTTPException:
        raise
    except Exception as e:
        return ModelTestResponse(
            success=False,
            model_id=model_id,
            prompt=prompt,
            response="",
            error=str(e),
        )


async def _test_ollama_model(model_id: str, prompt: str) -> str:
    """Test a model via Ollama API.

    Handles both regular models and "thinking" models (like Qwen3)
    that use a separate thinking field.
    """
    import os

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    async with httpx.AsyncClient() as client:
        # Allow forcing thinking via env for debugging
        force_thinking = os.getenv("LLM_FORCE_THINKING", "false").lower() in {"1", "true", "yes"}
        is_qwen3 = model_id.lower().startswith("qwen3")

        response = await client.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model_id,
                "prompt": f"Eres un asistente médico. Responde de forma concisa y profesional.\n\n{prompt}",
                "stream": False,
                # For Qwen3 or when forcing, enable separate thinking to surface raw field
                "think": bool(is_qwen3 or force_thinking),
                "options": {
                    "num_predict": 512,  # Increased for thinking models that reason first
                    "temperature": 0.7,
                },
            },
            timeout=300.0,  # 5 min for local models (first load is slow)
        )
        response.raise_for_status()
        data = response.json()

        # Get response; if think mode active and response empty, return raw thinking
        result = data.get("response", "").strip()
        if is_qwen3 or force_thinking:
            t = (data.get("thinking") or "").strip()
            if t and not result:
                result = t

        return result


async def _test_openai_model(model_id: str, prompt: str) -> str:
    """Test a model via OpenAI API."""
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un asistente médico. Responde de forma concisa y profesional.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 256,
                "temperature": 0.7,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


async def _test_anthropic_model(model_id: str, prompt: str) -> str:
    """Test a model via Anthropic API."""
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model_id,
                "max_tokens": 256,
                "system": "Eres un asistente médico. Responde de forma concisa y profesional.",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"].strip()
