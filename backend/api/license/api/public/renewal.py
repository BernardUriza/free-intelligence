"""
License Renewal API Endpoint

POST /api/licenses/renew

This endpoint handles license renewal requests from the desktop app.
It checks if the license is eligible for renewal and returns a new
license key if the subscription is active.

Flow:
1. Desktop app sends renewal request with license_id + machine_fingerprint
2. Server verifies the license exists and is renewable
3. Server checks payment status (Stripe/payment provider)
4. If valid, generates new license key with extended expiration
5. Returns new license key or renewal URL for payment

Security:
- Requires valid license_id
- Machine fingerprint must match (optional, for anti-piracy)
- Rate limited to prevent abuse
"""

from datetime import UTC, datetime, timedelta, timezone
from typing import Optional

# Import license generator (relative import within fi_license package)
from backend.api.license import LicensePayload, decode_license_key, generate_license_key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/licenses", tags=["licenses"])


class RenewalRequest(BaseModel):
    """License renewal request from desktop app."""

    license_id: str
    machine_fingerprint: str | None = None
    current_expires_at: str | None = None


class RenewalResponse(BaseModel):
    """License renewal response."""

    renewed: bool
    reason: str | None = None
    new_expires_at: str | None = None
    new_license_key: str | None = None
    renewal_url: str | None = None
    message: str


# In-memory license registry (replace with database in production)
# Format: { license_id: { expires_at, clinic_id, payment_status, ... } }
LICENSE_REGISTRY: dict = {}


@router.post("/renew", response_model=RenewalResponse)
async def renew_license(request: RenewalRequest) -> RenewalResponse:
    """
    Renew a license if eligible.

    Returns:
    - renewed=True + new_license_key if successful
    - renewed=False + renewal_url if payment required
    - renewed=False + reason if not eligible
    """
    license_id = request.license_id

    # Check if license exists in registry
    license_info = LICENSE_REGISTRY.get(license_id)

    if not license_info:
        # License not in registry - could be a valid license we haven't seen
        # In production, check database here
        return RenewalResponse(
            renewed=False,
            reason="license_not_found",
            message="License not found in registry. Please contact support.",
        )

    # Check payment status
    payment_status = license_info.get("payment_status", "unknown")

    if payment_status == "active":
        # Payment is active - generate new license key
        try:
            # Calculate new expiration (extend by subscription period)
            current_expires = datetime.fromisoformat(
                license_info.get("expires_at", "").replace("Z", "+00:00")
            )
            new_expires = max(current_expires, datetime.now(UTC)) + timedelta(days=365)

            # Generate new license key
            payload = LicensePayload(
                license_id=license_id,
                auth0_domain=license_info.get("auth0_domain", ""),
                auth0_client_id=license_info.get("auth0_client_id", ""),
                auth0_audience=license_info.get("auth0_audience", "https://app.aurity.io"),
                clinic_id=license_info.get("clinic_id", ""),
                clinic_name=license_info.get("clinic_name", ""),
                features=license_info.get("features", []),
                expires_at=new_expires.isoformat(),
            )

            new_license_key = generate_license_key(payload)

            # Update registry
            LICENSE_REGISTRY[license_id]["expires_at"] = new_expires.isoformat()

            return RenewalResponse(
                renewed=True,
                new_expires_at=new_expires.isoformat(),
                new_license_key=new_license_key,
                message="License renewed successfully.",
            )

        except Exception as e:
            return RenewalResponse(
                renewed=False,
                reason="generation_error",
                message=f"Failed to generate new license: {e!s}",
            )

    elif payment_status in ("expired", "cancelled"):
        # Payment expired - redirect to renewal page
        renewal_url = f"https://app.aurity.io/renew?license={license_id}"

        return RenewalResponse(
            renewed=False,
            reason="payment_required",
            renewal_url=renewal_url,
            message="Your subscription has expired. Please renew to continue.",
        )

    elif payment_status == "past_due":
        # Payment past due - show warning but allow grace period
        return RenewalResponse(
            renewed=False,
            reason="payment_past_due",
            renewal_url=f"https://app.aurity.io/billing?license={license_id}",
            message="Payment is past due. Please update your payment method.",
        )

    else:
        return RenewalResponse(
            renewed=False,
            reason="unknown_status",
            message="Unable to verify license status. Please contact support.",
        )


@router.get("/status/{license_id}")
async def get_license_status(license_id: str) -> dict:
    """
    Get the status of a license.

    Returns license info without generating a new key.
    """
    license_info = LICENSE_REGISTRY.get(license_id)

    if not license_info:
        raise HTTPException(status_code=404, detail="License not found")

    # Calculate days remaining
    expires_at = license_info.get("expires_at", "")
    days_remaining = None

    if expires_at:
        try:
            expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            days_remaining = (expires - datetime.now(UTC)).days
        except ValueError:
            pass

    return {
        "license_id": license_id,
        "clinic_name": license_info.get("clinic_name"),
        "expires_at": expires_at,
        "days_remaining": days_remaining,
        "payment_status": license_info.get("payment_status"),
        "features": license_info.get("features", []),
    }


@router.post("/register")
async def register_license(license_key: str) -> dict:
    """
    Register a license key in the renewal registry.

    Called when a license is first activated to enable future renewals.
    """
    try:
        payload, _ = decode_license_key(license_key)

        # Store in registry
        LICENSE_REGISTRY[payload.license_id] = {
            "license_id": payload.license_id,
            "auth0_domain": payload.auth0_domain,
            "auth0_client_id": payload.auth0_client_id,
            "auth0_audience": payload.auth0_audience,
            "clinic_id": payload.clinic_id,
            "clinic_name": payload.clinic_name,
            "features": payload.features,
            "expires_at": payload.expires_at,
            "payment_status": "active",  # Default to active on registration
            "registered_at": datetime.now(UTC).isoformat(),
        }

        return {
            "registered": True,
            "license_id": payload.license_id,
            "message": "License registered for renewal service.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
