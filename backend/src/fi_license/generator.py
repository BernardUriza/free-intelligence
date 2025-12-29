"""
License Key Generator for Aurity Desktop

This module generates Ed25519-signed license keys that encode:
- Auth0 credentials (domain, client_id, audience)
- Clinic/organization ID
- Feature flags
- Expiration date

License Key Format:
    AURITY-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX

    Where XXXX... is base32-encoded: payload || signature

Security:
- Private key stored in ~/.aurity-admin/license.key (NEVER in repo)
- Public key embedded in desktop app binary
- Signatures use Ed25519 (256-bit security)
"""

import base64
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timezone
from typing import Optional
from uuid import uuid4

import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pathlib import Path

# Default paths for keypair storage
ADMIN_DIR = Path.home() / ".aurity-admin"
PRIVATE_KEY_PATH = ADMIN_DIR / "license.key"
PUBLIC_KEY_PATH = ADMIN_DIR / "license.pub"

# License key prefix and formatting
LICENSE_PREFIX = "AURITY"
CHUNK_SIZE = 4  # Characters per chunk in formatted key


@dataclass
class LicensePayload:
    """
    License payload that gets signed and encoded into the license key.

    All fields are stored in the license key and can be extracted
    by the desktop app after signature verification.
    """

    # Unique license identifier
    license_id: str = field(default_factory=lambda: str(uuid4()))

    # Auth0 configuration (required for desktop sidecar)
    auth0_domain: str = ""
    auth0_client_id: str = ""
    auth0_audience: str = ""

    # Organization/clinic identifier
    clinic_id: str = ""
    clinic_name: str = ""

    # Feature flags (what the license enables)
    features: list[str] = field(default_factory=list)

    # Validity period
    issued_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str = ""  # ISO 8601 format

    # License metadata
    version: str = "1.0"

    def to_json(self) -> str:
        """Serialize payload to compact JSON."""
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> "LicensePayload":
        """Deserialize payload from JSON."""
        data = json.loads(json_str)
        return cls(**data)

    def is_expired(self) -> bool:
        """Check if the license has expired."""
        if not self.expires_at:
            return False  # No expiration = never expires
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(UTC) > expires


def generate_keypair(force: bool = False) -> tuple[bytes, bytes]:
    """
    Generate a new Ed25519 keypair for license signing.

    The private key is stored in ~/.aurity-admin/license.key
    The public key is stored in ~/.aurity-admin/license.pub

    Args:
        force: If True, overwrite existing keypair

    Returns:
        Tuple of (private_key_pem, public_key_pem)

    Raises:
        FileExistsError: If keypair exists and force=False
    """
    # Create admin directory if it doesn't exist
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)

    # Check for existing keypair
    if PRIVATE_KEY_PATH.exists() and not force:
        raise FileExistsError(
            f"Keypair already exists at {PRIVATE_KEY_PATH}. "
            "Use force=True to overwrite (WARNING: invalidates all existing licenses!)"
        )

    # Generate new Ed25519 keypair
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Serialize keys to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Write keys to files with appropriate permissions
    PRIVATE_KEY_PATH.write_bytes(private_pem)
    os.chmod(PRIVATE_KEY_PATH, 0o600)  # Owner read/write only

    PUBLIC_KEY_PATH.write_bytes(public_pem)
    os.chmod(PUBLIC_KEY_PATH, 0o644)  # Owner read/write, others read

    return private_pem, public_pem


def load_private_key() -> Ed25519PrivateKey:
    """Load the private key from ~/.aurity-admin/license.key"""
    if not PRIVATE_KEY_PATH.exists():
        raise FileNotFoundError(
            f"Private key not found at {PRIVATE_KEY_PATH}. "
            "Run 'fi license init-keys' to generate a keypair."
        )

    private_pem = PRIVATE_KEY_PATH.read_bytes()
    return serialization.load_pem_private_key(private_pem, password=None)  # type: ignore


def load_public_key(pem_data: bytes | None = None) -> Ed25519PublicKey:
    """
    Load the public key from PEM data or ~/.aurity-admin/license.pub

    Args:
        pem_data: Optional PEM-encoded public key bytes. If None, loads from file.
    """
    if pem_data is None:
        if not PUBLIC_KEY_PATH.exists():
            raise FileNotFoundError(
                f"Public key not found at {PUBLIC_KEY_PATH}. "
                "Run 'fi license init-keys' to generate a keypair."
            )
        pem_data = PUBLIC_KEY_PATH.read_bytes()

    return serialization.load_pem_public_key(pem_data)  # type: ignore


def generate_license_key(payload: LicensePayload) -> str:
    """
    Generate a signed license key from a payload.

    The license key contains:
    1. The JSON-encoded payload
    2. An Ed25519 signature of the payload

    Format: AURITY-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX

    Args:
        payload: The LicensePayload to encode and sign

    Returns:
        Formatted license key string
    """
    # Load private key
    private_key = load_private_key()

    # Serialize payload to JSON
    payload_json = payload.to_json()
    payload_bytes = payload_json.encode("utf-8")

    # Sign the payload
    signature = private_key.sign(payload_bytes)

    # Combine payload + signature
    # Format: [4 bytes payload length][payload][64 bytes signature]
    payload_len = len(payload_bytes).to_bytes(4, "big")
    combined = payload_len + payload_bytes + signature

    # Encode to base32 (URL-safe, case-insensitive)
    encoded = base64.b32encode(combined).decode("ascii").rstrip("=")

    # Format as AURITY-XXXX-XXXX-...
    chunks = [encoded[i : i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]
    formatted = f"{LICENSE_PREFIX}-" + "-".join(chunks)

    return formatted


def decode_license_key(license_key: str) -> tuple[LicensePayload, bytes]:
    """
    Decode a license key into its payload and signature.

    This does NOT verify the signature - use verify_license_signature for that.

    Args:
        license_key: The formatted license key string

    Returns:
        Tuple of (payload, signature)

    Raises:
        ValueError: If the license key format is invalid
    """
    # Remove prefix and dashes
    key = license_key.upper().replace("-", "")
    if not key.startswith(LICENSE_PREFIX):
        raise ValueError(f"Invalid license key: must start with {LICENSE_PREFIX}")

    encoded = key[len(LICENSE_PREFIX) :]

    # Add padding for base32 decoding
    padding = (8 - len(encoded) % 8) % 8
    encoded += "=" * padding

    try:
        combined = base64.b32decode(encoded)
    except Exception as e:
        raise ValueError(f"Invalid license key encoding: {e}")

    # Extract payload length (first 4 bytes)
    if len(combined) < 4:
        raise ValueError("Invalid license key: too short")

    payload_len = int.from_bytes(combined[:4], "big")

    # Extract payload and signature
    if len(combined) < 4 + payload_len + 64:
        raise ValueError("Invalid license key: incomplete data")

    payload_bytes = combined[4 : 4 + payload_len]
    signature = combined[4 + payload_len : 4 + payload_len + 64]

    # Parse payload JSON
    try:
        payload_json = payload_bytes.decode("utf-8")
        payload = LicensePayload.from_json(payload_json)
    except Exception as e:
        raise ValueError(f"Invalid license key payload: {e}")

    return payload, signature


def verify_license_signature(
    license_key: str,
    public_key_pem: bytes | None = None,
) -> tuple[bool, LicensePayload | None, str | None]:
    """
    Verify a license key's signature and return the payload if valid.

    Args:
        license_key: The formatted license key string
        public_key_pem: Optional PEM-encoded public key. If None, loads from file.

    Returns:
        Tuple of (is_valid, payload, error_message)
        - is_valid: True if signature is valid
        - payload: The decoded payload if valid, None otherwise
        - error_message: Error description if invalid, None otherwise
    """
    try:
        # Decode the license key
        payload, signature = decode_license_key(license_key)

        # Load public key
        public_key = load_public_key(public_key_pem)

        # Verify signature
        payload_bytes = payload.to_json().encode("utf-8")

        try:
            public_key.verify(signature, payload_bytes)
            return True, payload, None
        except Exception:
            return False, None, "Invalid signature"

    except ValueError as e:
        return False, None, str(e)
    except FileNotFoundError as e:
        return False, None, str(e)


def get_public_key_for_embedding() -> str:
    """
    Get the public key in a format suitable for embedding in the desktop app.

    Returns the public key as a base64-encoded string that can be embedded
    directly in Rust code.
    """
    if not PUBLIC_KEY_PATH.exists():
        raise FileNotFoundError(
            f"Public key not found at {PUBLIC_KEY_PATH}. "
            "Run 'fi license init-keys' to generate a keypair."
        )

    public_pem = PUBLIC_KEY_PATH.read_bytes()
    return base64.b64encode(public_pem).decode("ascii")


def format_license_key_display(license_key: str, line_length: int = 40) -> str:
    """
    Format a license key for display (with line breaks for readability).

    Args:
        license_key: The license key to format
        line_length: Maximum characters per line

    Returns:
        Multi-line formatted string
    """
    parts = license_key.split("-")
    lines = []
    current_line = []
    current_length = 0

    for part in parts:
        if current_length + len(part) + 1 > line_length and current_line:
            lines.append("-".join(current_line))
            current_line = [part]
            current_length = len(part)
        else:
            current_line.append(part)
            current_length += len(part) + 1

    if current_line:
        lines.append("-".join(current_line))

    return "\n".join(lines)
