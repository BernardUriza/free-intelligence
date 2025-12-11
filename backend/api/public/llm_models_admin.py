"""LLM Models Admin API - Manage AI Model Configurations.

PUBLIC endpoint for managing LLM models available for persona assignment.
Superadmin only - CRUD operations on model configurations.

Author: Bernard Uriza Orozco
Created: 2025-12-11
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from backend.models.llm_model import (
    CostTier,
    LLMModelCreate,
    LLMModelResponse,
    LLMModelUpdate,
    LLMProvider,
)
from backend.services.llm_model_service import llm_model_service

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
