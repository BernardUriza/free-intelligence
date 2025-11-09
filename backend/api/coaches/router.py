"""Coaches API endpoints - Mock data endpoints for development."""

from __future__ import annotations

from typing import Any, Optional

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
    """Obtiene estadísticas de un coach"""
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
            "coachId": coach_id,
            "activeAthletes": len(athletes),
            "sessionsThisWeek": len([s for s in sessions if s.get("status") != "completed"]),
            "avgCompletionRate": coach.get("avgCompletionRate", 0),
            "recentSessions": MockDataLoader.get_recent_sessions(coach_id, limit=5),
        },
    )


@router.get("/{coach_id}/athletes", response_model=APIResponse)
async def get_coach_athletes(coach_id: str) -> APIResponse[dict[str, Any]]:
    """Obtiene athletes asignados a un coach"""
    coach = MockDataLoader.get_coach(coach_id)
    if not coach:
        raise HTTPException(
            status_code=404,
            detail=f"Coach {coach_id} not found",
        )

    athletes = MockDataLoader.get_athletes_by_coach(coach_id)
    return APIResponse(
        status="success",
        code=200,
        data={
            "coachId": coach_id,
            "athletes": athletes,
            "total": len(athletes),
        },
    )


@router.get("/{coach_id}/sessions", response_model=APIResponse)
async def get_coach_sessions(
    coach_id: str,
    status: Optional[str] = Query(None),
) -> APIResponse[dict[str, Any]]:
    """Obtiene sessions de un coach, opcionalmente filtradas por estado"""
    coach = MockDataLoader.get_coach(coach_id)
    if not coach:
        raise HTTPException(
            status_code=404,
            detail=f"Coach {coach_id} not found",
        )

    sessions = MockDataLoader.get_sessions_by_coach(coach_id)

    if status:
        sessions = [s for s in sessions if s.get("status") == status]

    return APIResponse(
        status="success",
        code=200,
        data={
            "coachId": coach_id,
            "sessions": sessions,
            "total": len(sessions),
        },
    )
