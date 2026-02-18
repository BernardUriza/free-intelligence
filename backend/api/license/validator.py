"""
License Validator for Aurity Desktop

This module validates license keys and checks their status:
- Signature verification (Ed25519)
- Expiration checking
- Feature validation
- Status enumeration

Used by both the admin CLI (for verification) and the desktop app
(for runtime validation).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .generator import (
    LicensePayload,
    decode_license_key,
    verify_license_signature,
)


class LicenseStatus(str, Enum):
    """Status codes for license validation."""

    VALID = "valid"
    EXPIRED = "expired"
    INVALID_SIGNATURE = "invalid_signature"
    INVALID_FORMAT = "invalid_format"
    NOT_YET_VALID = "not_yet_valid"
    REVOKED = "revoked"


@dataclass
class LicenseValidationResult:
    """Result of license validation."""

    status: LicenseStatus
    payload: LicensePayload | None = None
    message: str = ""
    days_remaining: int | None = None
    features: list[str] = None  # type: ignore

    def __post_init__(self):
        if self.features is None:
            self.features = []

    @property
    def is_valid(self) -> bool:
        """Check if the license is valid (not expired, valid signature)."""
        return self.status == LicenseStatus.VALID

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "message": self.message,
            "days_remaining": self.days_remaining,
            "features": self.features,
            "payload": {
                "license_id": self.payload.license_id,
                "clinic_id": self.payload.clinic_id,
                "clinic_name": self.payload.clinic_name,
                "expires_at": self.payload.expires_at,
            }
            if self.payload
            else None,
        }


def validate_license(
    license_key: str,
    public_key_pem: bytes | None = None,
    check_expiration: bool = True,
) -> LicenseValidationResult:
    """
    Validate a license key completely.

    Performs:
    1. Format validation
    2. Signature verification
    3. Expiration check (optional)

    Args:
        license_key: The formatted license key string
        public_key_pem: Optional PEM-encoded public key for verification
        check_expiration: Whether to check if the license has expired

    Returns:
        LicenseValidationResult with status and details
    """
    # Step 1: Verify signature
    is_valid, payload, error = verify_license_signature(license_key, public_key_pem)

    if not is_valid:
        # Determine if it's a format error or signature error
        if error and ("Invalid license key" in error or "encoding" in error.lower()):
            return LicenseValidationResult(
                status=LicenseStatus.INVALID_FORMAT,
                message=error or "Invalid license key format",
            )
        return LicenseValidationResult(
            status=LicenseStatus.INVALID_SIGNATURE,
            message=error or "Invalid license signature",
        )

    # Step 2: Check expiration (if enabled)
    if check_expiration and payload:
        if payload.expires_at:
            try:
                expires = datetime.fromisoformat(payload.expires_at.replace("Z", "+00:00"))
                now = datetime.now(UTC)

                if now > expires:
                    days_expired = (now - expires).days
                    return LicenseValidationResult(
                        status=LicenseStatus.EXPIRED,
                        payload=payload,
                        message=f"License expired {days_expired} days ago",
                        days_remaining=-days_expired,
                        features=payload.features,
                    )

                days_remaining = (expires - now).days
            except ValueError:
                days_remaining = None
        else:
            # No expiration = perpetual license
            days_remaining = None

    else:
        days_remaining = None

    # License is valid!
    return LicenseValidationResult(
        status=LicenseStatus.VALID,
        payload=payload,
        message="License is valid",
        days_remaining=days_remaining,
        features=payload.features if payload else [],
    )


def is_license_expired(license_key: str) -> tuple[bool, int | None]:
    """
    Quick check if a license has expired.

    Args:
        license_key: The formatted license key string

    Returns:
        Tuple of (is_expired, days_remaining)
        - is_expired: True if expired or invalid
        - days_remaining: Days until expiration (negative if expired), None if perpetual/invalid
    """
    try:
        payload, _ = decode_license_key(license_key)

        if not payload.expires_at:
            return False, None  # Perpetual license

        expires = datetime.fromisoformat(payload.expires_at.replace("Z", "+00:00"))
        now = datetime.now(UTC)

        days = (expires - now).days

        return days < 0, days

    except Exception:
        return True, None  # Invalid license = treat as expired


def get_license_info(license_key: str) -> dict | None:
    """
    Extract license information without full validation.

    Useful for displaying license details to the user.

    Args:
        license_key: The formatted license key string

    Returns:
        Dictionary with license info, or None if invalid
    """
    try:
        payload, _ = decode_license_key(license_key)

        # Calculate days remaining
        days_remaining = None
        if payload.expires_at:
            try:
                expires = datetime.fromisoformat(payload.expires_at.replace("Z", "+00:00"))
                now = datetime.now(UTC)
                days_remaining = (expires - now).days
            except ValueError:
                pass

        return {
            "license_id": payload.license_id,
            "clinic_id": payload.clinic_id,
            "clinic_name": payload.clinic_name,
            "features": payload.features,
            "issued_at": payload.issued_at,
            "expires_at": payload.expires_at,
            "days_remaining": days_remaining,
            "version": payload.version,
        }

    except Exception:
        return None


def _mask_string(s: str, visible_chars: int = 4) -> str:
    """Mask a string for display (show first N chars only)."""
    if len(s) <= visible_chars:
        return s
    return s[:visible_chars] + "*" * (len(s) - visible_chars)


def check_feature_access(license_key: str, feature: str) -> bool:
    """
    Check if a license grants access to a specific feature.

    Args:
        license_key: The formatted license key string
        feature: The feature name to check (e.g., "soap", "timeline")

    Returns:
        True if the license grants access to the feature
    """
    try:
        payload, _ = decode_license_key(license_key)
        return feature in payload.features
    except Exception:
        return False


def list_features(license_key: str) -> list[str]:
    """
    List all features enabled by a license.

    Args:
        license_key: The formatted license key string

    Returns:
        List of feature names, empty list if invalid
    """
    try:
        payload, _ = decode_license_key(license_key)
        return payload.features
    except Exception:
        return []
