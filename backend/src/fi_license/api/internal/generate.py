"""
License Generation API - Superadmin Only

POST /internal/admin/licenses/generate

This endpoint allows superadmins to generate license keys for Aurity Desktop
directly from the web interface (no CLI required).

Security:
- Internal route (blocked by InternalOnlyMiddleware in production)
- Requires FI-superadmin role via JWT
- Private key loaded from ~/.aurity-admin/license.key

Author: Bernard Uriza
Created: 2025-12-28
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Optional

import structlog
from backend.src.fi_auth import User, UserRole, require_roles
from backend.src.fi_license.generator import LicensePayload, generate_license_key
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/licenses", tags=["licenses"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class LicenseGenerationRequest(BaseModel):
    """Request to generate a new license key."""

    clinic_id: str = Field(..., min_length=1, description="Unique clinic identifier")
    clinic_name: str = Field(default="", description="Human-readable clinic name")
    auth0_domain: str = Field(..., min_length=1, description="Auth0 tenant domain")
    auth0_client_id: str = Field(..., min_length=1, description="Auth0 application client ID")
    auth0_audience: str = Field(default="https://app.aurity.io", description="Auth0 API audience")
    features: list[str] = Field(
        default=["soap", "timeline", "prescriptions"],
        description="Enabled feature flags",
    )
    expires_days: int = Field(
        default=365, ge=1, le=3650, description="Days until expiration (1-3650)"
    )


class LicenseGenerationResponse(BaseModel):
    """Response with generated license key."""

    license_id: str
    license_key: str
    clinic_id: str
    clinic_name: str
    auth0_domain: str
    expires_at: str
    features: list[str]
    issued_at: str


# ============================================================================
# RBAC DEPENDENCY
# ============================================================================

superadmin_dependency = Depends(require_roles([UserRole.SUPERADMIN]))


async def require_superadmin(
    current_user: User = superadmin_dependency,
) -> User:
    """FastAPI dependency ensuring FI-superadmin role."""
    return current_user


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/generate", response_model=LicenseGenerationResponse)
async def admin_generate_license(
    request: LicenseGenerationRequest,
    current_user: User = Depends(require_superadmin),
) -> LicenseGenerationResponse:
    """
    Generate a new license key for Aurity Desktop.

    Requires FI-superadmin role.

    The license key is cryptographically signed with Ed25519 and contains:
    - Auth0 configuration (domain, client_id, audience)
    - Clinic identification (id, name)
    - Feature flags
    - Expiration date

    Returns:
        LicenseGenerationResponse with the generated license key
    """
    logger.info(
        "LICENSE_GENERATION_REQUESTED",
        clinic_id=request.clinic_id,
        clinic_name=request.clinic_name,
        features=request.features,
        expires_days=request.expires_days,
        requested_by=current_user.email,
    )

    try:
        # Calculate expiration
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=request.expires_days)

        # Create license payload
        payload = LicensePayload(
            auth0_domain=request.auth0_domain,
            auth0_client_id=request.auth0_client_id,
            auth0_audience=request.auth0_audience,
            clinic_id=request.clinic_id,
            clinic_name=request.clinic_name,
            features=request.features,
            expires_at=expires_at.isoformat(),
        )

        # Generate signed license key
        license_key = generate_license_key(payload)

        logger.info(
            "LICENSE_GENERATED_SUCCESSFULLY",
            license_id=payload.license_id,
            clinic_id=request.clinic_id,
            expires_at=expires_at.isoformat(),
            generated_by=current_user.email,
        )

        return LicenseGenerationResponse(
            license_id=payload.license_id,
            license_key=license_key,
            clinic_id=payload.clinic_id,
            clinic_name=payload.clinic_name,
            auth0_domain=payload.auth0_domain,
            expires_at=payload.expires_at,
            features=payload.features,
            issued_at=payload.issued_at,
        )

    except FileNotFoundError as e:
        logger.error(
            "LICENSE_GENERATION_FAILED",
            error="Private key not found",
            detail=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="License signing key not configured. Contact system administrator.",
        )

    except Exception as e:
        logger.error(
            "LICENSE_GENERATION_FAILED",
            error=str(e),
            clinic_id=request.clinic_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate license: {e!s}",
        )


@router.get("/features")
async def get_available_features(
    current_user: User = Depends(require_superadmin),
) -> dict:
    """
    Get list of available feature flags for licenses.

    Returns a list of feature IDs and their descriptions.
    """
    return {
        "features": [
            {"id": "soap", "name": "SOAP Notes", "description": "Medical SOAP documentation"},
            {"id": "timeline", "name": "Timeline", "description": "Patient visit timeline"},
            {
                "id": "prescriptions",
                "name": "Prescriptions",
                "description": "Prescription generation",
            },
            {"id": "analytics", "name": "Analytics", "description": "Usage analytics dashboard"},
            {
                "id": "multi_clinic",
                "name": "Multi-Clinic",
                "description": "Support for multiple clinics",
            },
            {
                "id": "voice_assistant",
                "name": "Voice Assistant",
                "description": "Real-time voice transcription",
            },
        ]
    }
