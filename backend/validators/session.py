"""Session ID validation - Single source of truth.

P0 FIX: Eliminates DRY violation where validate_session_id was duplicated 3x:
  - backend/api/public/workflows/sessions.py:554
  - backend/api/public/workflows/soap.py:95
  - backend/api/public/workflows/transcription.py:65

All three implementations were identical - now consolidated here.

Created: 2025-12-03
Pattern: Input Validation Layer
"""

from __future__ import annotations

import re

from fastapi import HTTPException, status


def validate_session_id(session_id: str) -> None:
    """Validate session_id format and raise HTTPException if invalid.

    Rules:
    - Length: 10-128 characters
    - Allowed characters: alphanumeric, hyphens, underscores
    - No special characters or whitespace

    Args:
        session_id: Session identifier to validate

    Raises:
        HTTPException: 400 Bad Request if validation fails

    Examples:
        >>> validate_session_id("abc-123-def-456")  # OK
        >>> validate_session_id("abc")  # Raises HTTPException (too short)
        >>> validate_session_id("abc@123")  # Raises HTTPException (invalid chars)
    """
    # Length validation
    if not session_id or len(session_id) < 10 or len(session_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session_id format: must be 10-128 characters long, got {len(session_id)}",
        )

    # Character whitelist validation (alphanumeric + hyphens + underscores only)
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format: only alphanumeric, hyphens, and underscores allowed",
        )
