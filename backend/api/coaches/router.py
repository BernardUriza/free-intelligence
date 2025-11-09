"""Coaches API Router.

Coach management endpoints (mock data for development).

File: backend/api/coaches/router.py
Reorganized: 2025-11-08 (moved from backend/api/coaches.py)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.config.mock_loader import MockDataLoader
from backend.schemas.schemas import APIResponse

router = APIRouter(tags=["coaches"])


@router.get("/", response_model=APIResponse)
async def list_coaches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> APIResponse[dict[str, Any]]:
    """Lista todos los coaches"""
    coaches = MockDataLoader.get_coaches()
    return APIResponse(
        status="success",
        code=200,
        data={
            "coaches": coaches[skip : skip + limit],
            "total": len(coaches),
        },
    )


@router.get("/{coach_id}", response_model=APIResponse)
async def get_coach(coach_id: str) -> APIResponse[dict[str, Any]]:
    """Obtiene un coach por ID"""
    coach = MockDataLoader.get_coach(coach_id)
    if not coach:
        raise HTTPException(
            status_code=404,
            detail=f"Coach {coach_id} not found",
        )
    return APIResponse(
        status="success",
        code=200,
        data={"coach": coach},
    )


@router.get("/{coach_id}/stats", response_model=APIResponse)
async def get_coach_stats(coach_id: str) -> APIResponse[dict[str, Any]]:
    """Obtiene estadisticas de un coach"""
    coach = MockDataLoader.get_coach(coach_id)
    if not coach:
        raise HTTPException(
            status_code=404,
            detail=f"Coach {coach_id} not found",
        )

    athletes = MockDataLoader.get_athletes_by_coach(coach_id)
    sessions = MockDataLoader.get_sessions_by_coach(coach_id)

    return APIResponse(
        status="success",
        code=200,
        data={
            "coach_id": coach_id,
            "total_athletes": len(athletes),
            "total_sessions": len(sessions),
            "recent_sessions": sessions[:5],
        },
    )
