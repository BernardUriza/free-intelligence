from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.auth0_dependencies import get_current_user_auth0
from backend.auth.models import User
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows/aurity", tags=["personas"])

PERSONAS_DIR = Path("config/personas")


def _load_persona_file(path: Path) -> dict[str, Any]:
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
        logger.error("persona_load_failed", file=str(path), error=str(err))
        raise


@router.get("/personas")
async def list_personas(user: User = Depends(get_current_user_auth0)) -> dict[str, Any]:
    if not PERSONAS_DIR.exists():
        logger.error("personas_dir_missing", dir=str(PERSONAS_DIR))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Personas directory missing"
        )

    personas: list[dict[str, Any]] = []
    for p in PERSONAS_DIR.glob("*.yaml"):
        personas.append(_load_persona_file(p))

    logger.info("personas_listed", count=len(personas))
    return {"personas": personas}
