from __future__ import annotations

from typing import Any

import yaml
from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from pathlib import Path

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows/aurity", tags=["personas"])

# Desktop mode: check ~/.aurity/config/personas first (same logic as PersonaManager)
_desktop_personas_dir = Path.home() / ".aurity" / "config" / "personas"
_default_personas_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "personas"
PERSONAS_DIR = _desktop_personas_dir if _desktop_personas_dir.exists() else _default_personas_dir


def _load_persona_file(path: Path, audit_service: DIAuditService) -> dict[str, Any]:
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
            user_id="system",
            resource=f"persona_file:{path.name}",
            result="failure",
            details={"error": str(err), "file": str(path)},
        )
        raise


@router.get("/personas")
async def list_personas(
    audit_service: DIAuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    if not PERSONAS_DIR.exists():
        audit_service.log_action(
            action="persona_delete_failed",
            user_id="system",
            resource="personas_directory",
            result="failure",
            details={"error": "Personas directory missing", "dir": str(PERSONAS_DIR)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Personas directory missing"
        )

    personas: list[dict[str, Any]] = []
    for p in PERSONAS_DIR.glob("*.yaml"):
        personas.append(_load_persona_file(p, audit_service))

    logger.info("personas_listed", count=len(personas))
    return {"personas": personas}
