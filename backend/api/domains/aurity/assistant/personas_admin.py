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

Endpoints (6 total):
- GET    /admin/personas          - List all personas
- GET    /admin/personas/{id}     - Get persona by ID
- PUT    /admin/personas/{id}     - Update persona
- POST   /admin/personas/{id}/test - Test persona with LLM
- POST   /admin/personas          - Create new persona (superadmin)
- DELETE /admin/personas/{id}     - Delete persona (superadmin)

Author: Bernard Uriza Orozco
Created: 2025-11-20
Updated: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.database import get_db_dependency
from backend.infrastructure.auth import User, UserRole, get_current_user
from backend.providers import llm_generate
from backend.services.kpi.services.persona_metrics_service import get_persona_metrics_service
from backend.services.llm.dependencies import get_persona_manager
from backend.utils.common.logging.logger import get_logger

from .personas_models import (
    PersonaCreateRequest,
    PersonaListResponse,
    PersonaResponse,
    PersonaTestRequest,
    PersonaTestResponse,
    PersonaUpdateRequest,
    PersonaUsageStats,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/personas", tags=["Personas Admin"])
logger = get_logger(__name__)

# Centralized singletons from DI providers
persona_manager = get_persona_manager()
metrics_service = get_persona_metrics_service()

# Protected personas that cannot be deleted
PROTECTED_PERSONAS = {"general_assistant", "soap_editor"}


# ============================================================================
# Helper Functions
# ============================================================================


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
    return None


def _build_persona_response(
    persona_id: str,
    config: object,
    yaml_data: dict,
) -> PersonaResponse:
    """Build PersonaResponse from config and YAML data.

    Args:
        persona_id: Persona identifier
        config: PersonaConfig from PersonaManager
        yaml_data: Raw YAML data dict

    Returns:
        PersonaResponse with all fields populated
    """
    metrics = metrics_service.get_persona_stats(persona_id)

    return PersonaResponse(
        id=persona_id,
        name=yaml_data.get("persona", persona_id).replace("_", " ").title(),
        description=config.description,
        system_prompt=config.system_prompt,
        model=config.model,
        voice=config.voice,
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


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=PersonaListResponse)
async def list_personas(
    user_id: str | None = Query(None, description="User ID for personalized configs"),
    db: "Session" = Depends(get_db_dependency),
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
            config = persona_manager.get_effective_persona(persona_id, user_id, db)
        else:
            config = persona_manager.get_persona(persona_id)

        # Load full YAML for examples and metadata
        yaml_path = persona_manager._config_dir / f"{persona_id}.yaml"
        if yaml_path.exists():
            with open(yaml_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            personas_list.append(
                _build_persona_response(persona_id, config, yaml_data)
            )

    return PersonaListResponse(personas=personas_list)


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    user_id: str | None = Query(None, description="User ID for personalized config"),
    db: "Session" = Depends(get_db_dependency),
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
        if user_id:
            config = persona_manager.get_effective_persona(persona_id, user_id, db)
        else:
            config = persona_manager.get_persona(persona_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    yaml_path = persona_manager._config_dir / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona config file not found: {persona_id}",
        )

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    return _build_persona_response(persona_id, config, yaml_data)


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    update: PersonaUpdateRequest,
    user_id: str | None = Query(None, description="User ID for personalized update"),
    db: "Session" = Depends(get_db_dependency),
    current_user: User = Depends(get_current_user),
    audit_service: DIAuditService = Depends(get_audit_service),
) -> PersonaResponse:
    """Update persona configuration.

    Multi-tenant behavior with RBAC:
    - If user_id provided: Updates user-specific overrides (saves to DB)
    - If no user_id: Updates global template (saves to YAML) - FI-superadmin ONLY

    Args:
        persona_id: Persona identifier
        update: Fields to update
        user_id: Optional user UUID (updates user override, not template)
        db: Database session
        current_user: Authenticated user from JWT
        audit_service: Audit logging service

    Returns:
        Updated PersonaResponse

    Raises:
        HTTPException: 403 if unauthorized for template updates
        HTTPException: 404 if persona not found
    """
    # USER-SPECIFIC UPDATE (to database)
    if user_id:
        try:
            persona_manager.update_user_persona(
                user_id=user_id,
                persona_id=persona_id,
                db=db,
                model=update.model,
                custom_prompt=update.system_prompt,
                temperature=update.temperature,
                max_tokens=update.max_tokens,
                voice=update.voice,
            )
            return await get_persona(persona_id, user_id=user_id, db=db)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e

    # TEMPLATE UPDATE (to YAML) - FI-superadmin ONLY
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

    # Reload PersonaManager
    persona_manager._load_personas()

    return await get_persona(persona_id, user_id=None, db=db)


@router.post("/{persona_id}/test", response_model=PersonaTestResponse)
async def test_persona(
    persona_id: str,
    test_request: PersonaTestRequest,
    user_id: str | None = Query(None, description="User ID for personalized config"),
    db: "Session" = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> PersonaTestResponse:
    """Test a persona with sample input using actual LLM.

    Calls the configured LLM model with the persona's system prompt
    and returns real output with metrics.

    Args:
        persona_id: Persona identifier
        test_request: Test input and options
        user_id: Optional user UUID for personalized config
        db: Database session
        audit_service: Audit logging service
        current_user: Authenticated user

    Returns:
        PersonaTestResponse with real LLM output and metrics

    Raises:
        HTTPException: 404 if persona not found
        HTTPException: 500 if LLM call fails
    """
    try:
        if user_id:
            config = persona_manager.get_effective_persona(persona_id, user_id, db)
        else:
            config = persona_manager.get_persona(persona_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Build prompt
    system_prompt = config.system_prompt
    full_prompt = f"{system_prompt}\n\nUser: {test_request.input}\n\nAssistant:"
    provider = _infer_provider_from_model(config.model)

    start_time = time.time()

    try:
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
        audit_service.log_action(
            action="personas_test_failed",
            user_id=current_user.id,
            resource=f"persona:{persona_id}",
            result="failure",
            details={
                "error": str(e)[:200],
                "model": config.model,
                "provider": provider,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM test failed for model '{config.model}': {str(e)[:100]}",
        ) from e


@router.post("", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    create_request: PersonaCreateRequest,
    db: "Session" = Depends(get_db_dependency),
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
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating personas requires FI-superadmin role",
        )

    yaml_path = persona_manager._config_dir / f"{create_request.id}.yaml"
    if yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Persona '{create_request.id}' already exists",
        )

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

    # Write atomically
    temp_path = yaml_path.with_suffix(".yaml.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        temp_path.rename(yaml_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create persona file: {e!s}",
        ) from e

    persona_manager._load_personas()

    logger.info(
        "PERSONA_CREATED",
        persona_id=create_request.id,
        created_by=current_user.email or current_user.user_id,
    )

    return await get_persona(create_request.id, user_id=None, db=db)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: str,
    db: "Session" = Depends(get_db_dependency),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a persona (FI-superadmin only).

    Deletes the YAML file and cascades to delete all user overrides from DB.
    Some core personas (general_assistant, soap_editor) are protected.

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

    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deleting personas requires FI-superadmin role",
        )

    if persona_id in PROTECTED_PERSONAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete protected persona: {persona_id}. "
            f"Protected personas: {', '.join(PROTECTED_PERSONAS)}",
        )

    yaml_path = persona_manager._config_dir / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )

    # Cascade delete user overrides
    try:
        deleted_count = (
            db.query(UserPersonaConfig)
            .filter(UserPersonaConfig.persona_id == persona_id)
            .delete(synchronize_session=False)
        )
        db.commit()

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

    persona_manager._load_personas()

    logger.info(
        "PERSONA_DELETED",
        persona_id=persona_id,
        deleted_by=current_user.email or current_user.user_id,
        user_configs_deleted=deleted_count,
    )
