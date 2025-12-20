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

from datetime import UTC, datetime
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.src.fi_llm.services.persona_manager import PersonaManager
from backend.src.fi_llm.services.persona_metrics_service import get_persona_metrics_service
from backend.src.fi_auth import User, UserRole, get_current_user

router = APIRouter(prefix="/admin/personas", tags=["Personas Admin"])

# Initialize PersonaManager and MetricsService
persona_manager = PersonaManager()
metrics_service = get_persona_metrics_service()


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
    voice: str | None = Field(None, description="TTS voice (e.g., 'nova', 'shimmer')")
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
    voice: str | None = Field(
        None, description="TTS voice (nova, shimmer, alloy, echo, fable, onyx)"
    )
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


class PersonaCreateRequest(BaseModel):
    """Request to create a new persona (FI-superadmin only)."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Unique persona ID (lowercase, underscores allowed, e.g., 'my_persona')",
    )
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    description: str = Field(..., min_length=10, description="Persona description (min 10 chars)")
    system_prompt: str = Field(..., min_length=20, description="System prompt (min 20 chars)")
    model: str = Field(default="qwen3:1.7b", description="LLM model ID")
    voice: str | None = Field(default="nova", description="TTS voice")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperature (0.0-1.0)")
    max_tokens: int = Field(default=2048, gt=0, le=8192, description="Max tokens (1-8192)")
    examples: list[dict[str, Any]] = Field(default_factory=list, description="Few-shot examples")


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

            # Get real metrics from audit logs
            metrics = metrics_service.get_persona_stats(persona_id)

            personas_list.append(
                PersonaResponse(
                    id=persona_id,
                    name=yaml_data.get("persona", persona_id).replace("_", " ").title(),
                    description=config.description,
                    system_prompt=config.system_prompt,
                    model=config.model,  # From config (with user override support)
                    voice=config.voice,  # TTS voice (with user override support)
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    examples=yaml_data.get("examples", []),
                    usage_stats=PersonaUsageStats(
                        total_invocations=metrics["total_invocations"],
                        avg_latency_ms=metrics["avg_latency_ms"],
                        avg_cost_usd=metrics["avg_cost_usd"],
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

    # Get real metrics from audit logs
    metrics = metrics_service.get_persona_stats(persona_id)

    return PersonaResponse(
        id=persona_id,
        name=yaml_data.get("persona", persona_id).replace("_", " ").title(),
        description=config.description,
        system_prompt=config.system_prompt,
        model=config.model,  # From config (with user override support)
        voice=config.voice,  # TTS voice (with user override support)
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        examples=yaml_data.get("examples", []),
        usage_stats=PersonaUsageStats(
            total_invocations=metrics["total_invocations"],
            avg_latency_ms=metrics["avg_latency_ms"],
            avg_cost_usd=metrics["avg_cost_usd"],
        ),
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
    current_user: User = Depends(get_current_user),
) -> PersonaResponse:
    """Update persona configuration.

    Multi-tenant behavior with RBAC:
    - If user_id provided: Updates user-specific overrides (saves to DB) - authenticated user only
    - If no user_id: Updates global template (saves to YAML) - FI-superadmin ONLY

    Args:
        persona_id: Persona identifier
        update: Fields to update
        user_id: Optional user UUID (updates user override, not template)
        db: Database session
        current_user: Authenticated user from Auth0

    Returns:
        Updated PersonaResponse

    Raises:
        HTTPException: 403 if unauthorized for template updates
        HTTPException: 404 if persona not found
    """
    # USER-SPECIFIC UPDATE (to database) - any authenticated user can update their own
    if user_id:
        try:
            persona_manager.update_user_persona(
                user_id=user_id,
                persona_id=persona_id,
                db=db,
                model=update.model,  # LLM model override
                custom_prompt=update.system_prompt,
                temperature=update.temperature,
                max_tokens=update.max_tokens,
                voice=update.voice,  # TTS voice override
            )
            return await get_persona(persona_id, user_id=user_id, db=db)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e

    # TEMPLATE UPDATE (to YAML) - FI-superadmin ONLY
    # RBAC check: only superadmin can modify global templates
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Template updates require FI-superadmin role. "
            "To update your personal config, provide user_id parameter.",
        )

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
    if update.voice is not None:
        yaml_data["voice"] = update.voice
    if update.temperature is not None:
        yaml_data["temperature"] = update.temperature
    if update.max_tokens is not None:
        yaml_data["max_tokens"] = update.max_tokens
    if update.examples is not None:
        yaml_data["examples"] = update.examples

    # Increment version
    yaml_data["version"] = yaml_data.get("version", 1) + 1
    yaml_data["updated_at"] = datetime.now(UTC).isoformat()
    yaml_data["updated_by"] = current_user.email or current_user.sub

    # Save updated YAML
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Reload PersonaManager to pick up changes
    persona_manager._load_personas()

    # Return updated persona
    return await get_persona(persona_id, user_id=None, db=db)


def _infer_provider_from_model(model: str) -> str | None:
    """Infer LLM provider from model name.

    Args:
        model: Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet', 'qwen3:1.7b')

    Returns:
        Provider name ('azure', 'claude', 'ollama') or None for policy default
    """
    model_lower = model.lower()
    if model_lower.startswith("gpt-") or "openai" in model_lower:
        return "azure"
    elif model_lower.startswith("claude"):
        return "claude"
    elif ":" in model_lower or model_lower.startswith("qwen"):
        return "ollama"
    return None  # Use policy default


@router.post("/{persona_id}/test", response_model=PersonaTestResponse)
async def test_persona(
    persona_id: str,
    test_request: PersonaTestRequest,
    user_id: str | None = Query(None, description="User ID for personalized config"),
    db: Session = Depends(get_db_dependency),
) -> PersonaTestResponse:
    """Test a persona with sample input using actual LLM.

    Calls the configured LLM model with the persona's system prompt
    and returns real output with metrics.

    Args:
        persona_id: Persona identifier
        test_request: Test input and options
        user_id: Optional user UUID for personalized config
        db: Database session

    Returns:
        PersonaTestResponse with real LLM output and metrics

    Raises:
        HTTPException: 404 if persona not found
        HTTPException: 500 if LLM call fails
    """
    import time

    from backend.providers.llm import llm_generate

    # Get effective persona config (with user overrides if user_id provided)
    try:
        if user_id:
            config = persona_manager.get_user_persona(persona_id, user_id, db)
        else:
            config = persona_manager.get_persona(persona_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Build the full prompt with system context
    system_prompt = config.system_prompt
    full_prompt = f"{system_prompt}\n\nUser: {test_request.input}\n\nAssistant:"

    # Infer provider from model name
    provider = _infer_provider_from_model(config.model)

    start_time = time.time()

    try:
        # Call actual LLM with persona configuration
        llm_response = llm_generate(
            prompt=full_prompt,
            provider=provider,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        latency_ms = (time.time() - start_time) * 1000

        return PersonaTestResponse(
            output=llm_response.content,
            latency_ms=latency_ms,
            tokens_used=llm_response.tokens_used,
            cost_usd=llm_response.cost_usd or 0.0,
        )

    except Exception as e:
        # Log error and return helpful message
        import structlog

        logger = structlog.get_logger(__name__)
        logger.error(
            "PERSONA_TEST_FAILED",
            persona_id=persona_id,
            model=config.model,
            provider=provider,
            error=str(e)[:200],
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM test failed for model '{config.model}': {str(e)[:100]}",
        ) from e


# Protected personas that cannot be deleted
PROTECTED_PERSONAS = {"general_assistant", "soap_editor"}


@router.post("", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    create_request: PersonaCreateRequest,
    db: Session = Depends(get_db_dependency),
    current_user: User = Depends(get_current_user),
) -> PersonaResponse:
    """Create a new persona (FI-superadmin only).

    Creates a new YAML file in /backend/config/personas/ directory.
    The persona will be immediately available for use.

    Args:
        create_request: New persona configuration
        db: Database session
        current_user: Authenticated user

    Returns:
        Created PersonaResponse

    Raises:
        HTTPException: 403 if not FI-superadmin
        HTTPException: 409 if persona ID already exists
        HTTPException: 500 if file creation fails
    """
    # RBAC: Require FI-superadmin
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating personas requires FI-superadmin role",
        )

    # Check if persona ID already exists
    yaml_path = persona_manager._config_dir / f"{create_request.id}.yaml"
    if yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Persona '{create_request.id}' already exists",
        )

    # Build YAML content
    yaml_data = {
        "persona": create_request.id,
        "description": create_request.description,
        "system_prompt": create_request.system_prompt,
        "model": create_request.model,
        "voice": create_request.voice,
        "temperature": create_request.temperature,
        "max_tokens": create_request.max_tokens,
        "examples": create_request.examples,
        "version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "updated_by": current_user.email or current_user.user_id,
    }

    # Write YAML file atomically (write to .tmp then rename)
    temp_path = yaml_path.with_suffix(".yaml.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        temp_path.rename(yaml_path)  # Atomic rename
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create persona file: {e!s}",
        ) from e

    # Reload PersonaManager to pick up new persona
    persona_manager._load_personas()

    import structlog

    logger = structlog.get_logger(__name__)
    logger.info(
        "PERSONA_CREATED",
        persona_id=create_request.id,
        created_by=current_user.email or current_user.user_id,
    )

    # Return created persona
    return await get_persona(create_request.id, user_id=None, db=db)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: str,
    db: Session = Depends(get_db_dependency),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a persona (FI-superadmin only).

    Deletes the YAML file and cascades to delete all user overrides from DB.
    Some core personas (general_assistant, soap_editor) are protected and cannot be deleted.

    Args:
        persona_id: Persona identifier
        db: Database session
        current_user: Authenticated user

    Raises:
        HTTPException: 400 if trying to delete protected persona
        HTTPException: 403 if not FI-superadmin
        HTTPException: 404 if persona not found
        HTTPException: 500 if deletion fails
    """
    from backend.models.db_models import UserPersonaConfig

    # RBAC: Require FI-superadmin
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deleting personas requires FI-superadmin role",
        )

    # Check if persona is protected
    if persona_id in PROTECTED_PERSONAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete protected persona: {persona_id}. "
            f"Protected personas: {', '.join(PROTECTED_PERSONAS)}",
        )

    # Check if persona exists
    yaml_path = persona_manager._config_dir / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )

    # Cascade delete: remove all user overrides from database
    try:
        deleted_count = (
            db.query(UserPersonaConfig)
            .filter(UserPersonaConfig.persona_id == persona_id)
            .delete(synchronize_session=False)
        )
        db.commit()

        import structlog

        logger = structlog.get_logger(__name__)
        logger.info(
            "PERSONA_USER_CONFIGS_DELETED",
            persona_id=persona_id,
            deleted_count=deleted_count,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user configs: {e!s}",
        ) from e

    # Delete YAML file
    try:
        yaml_path.unlink()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete persona file: {e!s}",
        ) from e

    # Reload PersonaManager
    persona_manager._load_personas()

    import structlog

    logger = structlog.get_logger(__name__)
    logger.info(
        "PERSONA_DELETED",
        persona_id=persona_id,
        deleted_by=current_user.email or current_user.user_id,
        user_configs_deleted=deleted_count,
    )

    # Return 204 No Content (implicit via status_code)
