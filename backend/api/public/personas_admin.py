"""Personas Admin API - Manage AI Personas Configuration (Multi-Tenant).

PUBLIC endpoint for managing AI personas (SOAP Editor, Clinical Advisor, etc.).
Allows CRUD operations on persona configurations, testing, and version management.

Architecture (Template + Override Pattern):
  PUBLIC (this file) → SERVICES (PersonaManager) → {
      Templates: YAML files (/backend/config/personas/)
      Overrides: PostgreSQL (user_persona_configs table)
  }

Multi-tenancy:
  - Each user gets cloned personas from templates
  - Users can customize prompts, temperature, max_tokens
  - NULL overrides = use template default
  - Template updates don't affect user customizations

Author: Bernard Uriza Orozco
Created: 2025-11-20
Updated: 2025-11-20 (Multi-tenant support)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.compat import UTC
from backend.database import get_db_dependency
from backend.services.llm.persona_manager import PersonaManager

router = APIRouter(prefix="/admin/personas", tags=["Personas Admin"])

# Initialize PersonaManager
persona_manager = PersonaManager()


# Pydantic Models
class PersonaExample(BaseModel):
    """Few-shot example for persona."""

    input: str = Field(..., description="Example input")
    output: str | dict[str, Any] = Field(..., description="Example output")


class PersonaUsageStats(BaseModel):
    """Usage statistics for a persona."""

    total_invocations: int = Field(default=0, description="Total times invoked")
    avg_latency_ms: float = Field(default=0.0, description="Average latency in ms")
    avg_cost_usd: float = Field(default=0.0, description="Average cost per invocation")


class PersonaResponse(BaseModel):
    """Persona configuration response."""

    id: str = Field(..., description="Persona ID (e.g., 'soap_editor')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Persona description")
    system_prompt: str = Field(..., description="System prompt")
    model: str = Field(..., description="LLM model (e.g., 'gpt-4o-mini')")
    temperature: float = Field(..., description="Temperature (0.0-1.0)")
    max_tokens: int = Field(..., description="Max tokens")
    examples: list[dict[str, Any]] = Field(default_factory=list, description="Few-shot examples")
    usage_stats: PersonaUsageStats = Field(
        default_factory=PersonaUsageStats, description="Usage statistics"
    )
    version: int = Field(default=1, description="Version number")
    last_updated: str = Field(..., description="Last update timestamp")
    updated_by: str = Field(default="System", description="Last updated by")


class PersonaListResponse(BaseModel):
    """List of personas response."""

    personas: list[PersonaResponse] = Field(..., description="List of personas")


class PersonaUpdateRequest(BaseModel):
    """Request to update persona configuration."""

    name: str | None = Field(None, description="Display name")
    description: str | None = Field(None, description="Persona description")
    system_prompt: str | None = Field(None, description="System prompt")
    model: str | None = Field(None, description="LLM model")
    temperature: float | None = Field(None, ge=0.0, le=1.0, description="Temperature")
    max_tokens: int | None = Field(None, gt=0, description="Max tokens")
    examples: list[dict[str, Any]] | None = Field(None, description="Few-shot examples")


class PersonaTestRequest(BaseModel):
    """Request to test a persona."""

    input: str = Field(..., description="Test input")
    compare_with_version: int | None = Field(None, description="Compare with version number")


class PersonaTestResponse(BaseModel):
    """Response from persona test."""

    output: str | dict[str, Any] = Field(..., description="LLM output")
    latency_ms: float = Field(..., description="Latency in milliseconds")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    cost_usd: float = Field(default=0.0, description="Estimated cost")


# API Endpoints
@router.get("", response_model=PersonaListResponse)
async def list_personas(
    user_id: str | None = Query(None, description="User ID for personalized configs"),
    db: Session = Depends(get_db_dependency),
) -> PersonaListResponse:
    """Get list of all available personas with their configurations.

    Multi-tenant behavior:
    - If user_id provided: Returns personas with user-specific overrides merged
    - If no user_id: Returns base templates from YAML files

    Args:
        user_id: Optional user UUID for personalized configs
        db: Database session

    Returns:
        PersonaListResponse with all personas
    """

    personas_list = []

    for persona_id in persona_manager.list_personas():
        # Get config (with user overrides if user_id provided)
        if user_id:
            config = persona_manager.get_user_persona(persona_id, user_id, db)
        else:
            config = persona_manager.get_persona(persona_id)

        # Load full YAML to get examples and metadata
        yaml_path = persona_manager._config_dir / f"{persona_id}.yaml"
        if yaml_path.exists():
            with open(yaml_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            personas_list.append(
                PersonaResponse(
                    id=persona_id,
                    name=yaml_data.get("persona", persona_id).replace("_", " ").title(),
                    description=config.description,
                    system_prompt=config.system_prompt,
                    model=yaml_data.get("model", "gpt-4o-mini"),  # From template
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    examples=yaml_data.get("examples", []),
                    usage_stats=PersonaUsageStats(
                        total_invocations=0,  # TODO: Load from metrics
                        avg_latency_ms=0.0,
                        avg_cost_usd=0.0,
                    ),
                    version=yaml_data.get("version", 1),
                    last_updated=yaml_data.get("updated_at", datetime.now(UTC).isoformat()),
                    updated_by=yaml_data.get("updated_by", "System"),
                )
            )

    return PersonaListResponse(personas=personas_list)


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    user_id: str | None = Query(None, description="User ID for personalized config"),
    db: Session = Depends(get_db_dependency),
) -> PersonaResponse:
    """Get detailed configuration for a specific persona.

    Multi-tenant behavior:
    - If user_id provided: Returns persona with user-specific overrides merged
    - If no user_id: Returns base template from YAML

    Args:
        persona_id: Persona identifier (e.g., 'soap_editor')
        user_id: Optional user UUID for personalized config
        db: Database session

    Returns:
        PersonaResponse with full configuration

    Raises:
        HTTPException: 404 if persona not found
    """
    try:
        # Get config (with user overrides if user_id provided)
        if user_id:
            config = persona_manager.get_user_persona(persona_id, user_id, db)
        else:
            config = persona_manager.get_persona(persona_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Load full YAML for metadata and examples
    yaml_path = persona_manager._config_dir / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona config file not found: {persona_id}",
        )

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    return PersonaResponse(
        id=persona_id,
        name=yaml_data.get("persona", persona_id).replace("_", " ").title(),
        description=config.description,
        system_prompt=config.system_prompt,
        model=yaml_data.get("model", "gpt-4o-mini"),
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        examples=yaml_data.get("examples", []),
        usage_stats=PersonaUsageStats(),
        version=yaml_data.get("version", 1),
        last_updated=yaml_data.get("updated_at", datetime.now(UTC).isoformat()),
        updated_by=yaml_data.get("updated_by", "System"),
    )


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    update: PersonaUpdateRequest,
    user_id: str | None = Query(None, description="User ID for personalized update"),
    db: Session = Depends(get_db_dependency),
) -> PersonaResponse:
    """Update persona configuration.

    Multi-tenant behavior:
    - If user_id provided: Updates user-specific overrides (saves to DB)
    - If no user_id: Updates global template (saves to YAML) - ADMIN ONLY

    Args:
        persona_id: Persona identifier
        update: Fields to update
        user_id: Optional user UUID (updates user override, not template)
        db: Database session

    Returns:
        Updated PersonaResponse

    Raises:
        HTTPException: 404 if persona not found
    """
    # USER-SPECIFIC UPDATE (to database)
    if user_id:
        try:
            updated_config = persona_manager.update_user_persona(
                user_id=user_id,
                persona_id=persona_id,
                db=db,
                custom_prompt=update.system_prompt,
                temperature=update.temperature,
                max_tokens=update.max_tokens,
            )
            return await get_persona(persona_id, user_id=user_id, db=db)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e

    # TEMPLATE UPDATE (to YAML) - ADMIN ONLY
    # Verify persona exists
    try:
        persona_manager.get_persona(persona_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Load current YAML
    yaml_path = persona_manager._config_dir / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona config file not found: {persona_id}",
        )

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    # Update fields
    if update.name is not None:
        yaml_data["persona"] = update.name.lower().replace(" ", "_")
    if update.description is not None:
        yaml_data["description"] = update.description
    if update.system_prompt is not None:
        yaml_data["system_prompt"] = update.system_prompt
    if update.model is not None:
        yaml_data["model"] = update.model
    if update.temperature is not None:
        yaml_data["temperature"] = update.temperature
    if update.max_tokens is not None:
        yaml_data["max_tokens"] = update.max_tokens
    if update.examples is not None:
        yaml_data["examples"] = update.examples

    # Increment version
    yaml_data["version"] = yaml_data.get("version", 1) + 1
    yaml_data["updated_at"] = datetime.now(UTC).isoformat()
    yaml_data["updated_by"] = "Dr. Uriza"  # TODO: Get from auth context

    # Save updated YAML
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Reload PersonaManager to pick up changes
    persona_manager._load_personas()

    # Return updated persona
    return await get_persona(persona_id, user_id=None, db=db)


@router.post("/{persona_id}/test", response_model=PersonaTestResponse)
async def test_persona(persona_id: str, test_request: PersonaTestRequest) -> PersonaTestResponse:
    """Test a persona with sample input.

    Args:
        persona_id: Persona identifier
        test_request: Test input and options

    Returns:
        PersonaTestResponse with output and metrics

    Raises:
        HTTPException: 404 if persona not found
    """
    import time

    # Verify persona exists
    try:
        config = persona_manager.get_persona(persona_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # TODO: Implement actual LLM call
    # For now, return mock response
    start_time = time.time()

    # Simulate LLM processing
    time.sleep(0.5)

    latency_ms = (time.time() - start_time) * 1000

    return PersonaTestResponse(
        output={
            "status": "success",
            "message": f"Test completed for {persona_id}",
            "config_used": {
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            },
        },
        latency_ms=latency_ms,
        tokens_used=150,  # Mock
        cost_usd=0.0023,  # Mock
    )
