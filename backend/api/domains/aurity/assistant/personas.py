"""Assistant Personas - List available personas.

Endpoint:
- GET /personas - List all available personas

Re-exported from: backend/api/routers/assistant/public/aurity_personas.py
Note: Legacy router has prefix="/workflows/aurity", we extract just the handler.
"""

from __future__ import annotations

from typing import Any

import yaml
from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from pathlib import Path

logger = get_logger(__name__)

router = APIRouter()

# Desktop mode: check ~/.aurity/config/personas first
_desktop_personas_dir = Path.home() / ".aurity" / "config" / "personas"
_default_personas_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "personas"
PERSONAS_DIR = _desktop_personas_dir if _desktop_personas_dir.exists() else _default_personas_dir


def _load_persona_file(path: Path, audit_service: DIAuditService, user_id: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return {
            "id": data.get("persona"),
            "name": data.get("persona").replace("_", " ").title()
            if data.get("persona")
            else "unknown",
            "description": data.get("description", ""),
            "model": data.get("model"),
            "temperature": data.get("temperature"),
            "max_tokens": data.get("max_tokens"),
            "voice": data.get("voice"),
        }
    except Exception as err:
        audit_service.log_action(
            action="persona_save_failed",
            user_id=user_id,
            resource=f"persona_file:{path.name}",
            result="failure",
            details={"error": str(err), "file": str(path)},
        )
        raise


@router.get("/personas")
async def list_personas(
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all available chat personas.

    Returns persona configurations from ~/.aurity/config/personas/ or default location.
    """
    try:
        personas = []
        if PERSONAS_DIR.exists():
            for yaml_file in sorted(PERSONAS_DIR.glob("*.yaml")):
                try:
                    personas.append(_load_persona_file(yaml_file, audit_service, current_user.id))
                except Exception as e:
                    logger.warning(f"Failed to load persona {yaml_file.name}: {e}")
                    continue

        audit_service.log_action(
            action="personas_listed",
            user_id=current_user.id,
            resource="personas",
            result="success",
            details={"count": len(personas), "dir": str(PERSONAS_DIR)},
        )
        return personas
    except Exception as e:
        audit_service.log_action(
            action="personas_list_failed",
            user_id=current_user.id,
            resource="personas",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list personas: {e}",
        )


__all__ = ["router"]
