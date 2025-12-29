"""
FI License - Software Licensing System for Aurity Desktop

This module handles:
- License key generation (Ed25519 signed)
- License validation and verification
- License storage in H5 format

Security:
- Private key NEVER in git repo (stored in ~/.aurity-admin/)
- Public key embedded in desktop app binary
- Machine-bound licenses via hardware fingerprint
"""

from .generator import (
    LicensePayload,
    generate_keypair,
    generate_license_key,
    decode_license_key,
    verify_license_signature,
    get_public_key_for_embedding,
    format_license_key_display,
)
from .validator import (
    LicenseStatus,
    validate_license,
    is_license_expired,
)

__all__ = [
    "LicensePayload",
    "LicenseStatus",
    "generate_keypair",
    "generate_license_key",
    "decode_license_key",
    "verify_license_signature",
    "get_public_key_for_embedding",
    "format_license_key_display",
    "validate_license",
    "is_license_expired",
]
