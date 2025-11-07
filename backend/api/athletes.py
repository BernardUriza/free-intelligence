"""
Athletes API endpoints - Mock data endpoints for development
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.schemas import APIResponse
from backend.config.mock_loader import MockDataLoader

router = APIRouter(prefix="/athletes", tags=["athletes"])


@router.get("/", response_model=APIResponse)
async def list_athletes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    coach_id: Optional[str] = Query(None),
) -> dict:
    """Lista athletes, opcionalmente filtrados por coach"""
    if coach_id:
        athletes = MockDataLoader.get_athletes_by_coach(coach_id)
    else:
        athletes = MockDataLoader.get_athletes()

    return APIResponse(
        status="success",
        data={
            "athletes": athletes[skip : skip + limit],
            "total": len(athletes),
        },
    )


@router.get("/{athlete_id}", response_model=APIResponse)
async def get_athlete(athlete_id: str) -> dict:
    """Obtiene un athlete por ID"""
    athlete = MockDataLoader.get_athlete(athlete_id)
    if not athlete:
        raise HTTPException(
            status_code=404,
            detail=f"Athlete {athlete_id} not found",
        )
    return APIResponse(
        status="success",
        data={"athlete": athlete},
    )


@router.get("/{athlete_id}/sessions", response_model=APIResponse)
async def get_athlete_sessions(
    athlete_id: str,
    status: Optional[str] = Query(None),
) -> dict:
    """Obtiene sessions asignadas a un athlete"""
    athlete = MockDataLoader.get_athlete(athlete_id)
    if not athlete:
        raise HTTPException(
            status_code=404,
            detail=f"Athlete {athlete_id} not found",
        )

    sessions = MockDataLoader.get_sessions_by_athlete(athlete_id)

    if status:
        sessions = [s for s in sessions if s.get("status") == status]

    return APIResponse(
        status="success",
        data={
            "athleteId": athlete_id,
            "sessions": sessions,
            "total": len(sessions),
        },
    )


@router.get("/{athlete_id}/progress", response_model=APIResponse)
async def get_athlete_progress(athlete_id: str) -> dict:
    """Obtiene progreso de un athlete"""
    athlete = MockDataLoader.get_athlete(athlete_id)
    if not athlete:
        raise HTTPException(
            status_code=404,
            detail=f"Athlete {athlete_id} not found",
        )

    sessions = MockDataLoader.get_sessions_by_athlete(athlete_id)
    completed = len([s for s in sessions if s.get("status") == "completed"])
    total = len(sessions)

    return APIResponse(
        status="success",
        data={
            "athleteId": athlete_id,
            "name": athlete.get("name"),
            "sessionsCompleted": athlete.get("sessionsCompleted", completed),
            "sessionsTotal": athlete.get("sessionsTotal", total),
            "completionRate": athlete.get("completionRate", 0),
            "goal": athlete.get("goal"),
            "fitnessLevel": athlete.get("fitnessLevel"),
            "injuries": athlete.get("injuries", []),
        },
    )
