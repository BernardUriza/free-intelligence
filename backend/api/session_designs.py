"""
Session Designs API endpoints - Endpoints para diseños/templates de sesiones
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.config.mock_loader import MockDataLoader
from backend.schemas.schemas import APIResponse

router = APIRouter(tags=["sessions"])


@router.get("/", response_model=APIResponse)
async def list_session_designs(
    coach_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    """Lista diseños de sesiones, opcionalmente por coach"""
    if coach_id:
        sessions = MockDataLoader.get_sessions_by_coach(coach_id)
    else:
        sessions = MockDataLoader.get_sessions()

    return APIResponse(
        status="success",
        code=200,
        data={
            "designs": sessions[skip : skip + limit],
            "total": len(sessions),
        },
    )


@router.get("/{session_id}", response_model=APIResponse)
async def get_session_design(session_id: str) -> dict:
    """Obtiene un diseño de sesión por ID"""
    session = MockDataLoader.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session design {session_id} not found",
        )
    return APIResponse(
        status="success",
        code=200,
        data={"session": session},
    )


@router.post("/", response_model=APIResponse)
async def create_session_design(
    name: str,
    coach_id: str,
    blocks: list,
) -> dict:
    """Crea un nuevo diseño de sesión"""
    # En mock, solo validamos que los datos sean válidos
    if not name or not coach_id or not blocks:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: name, coachId, blocks",
        )

    coach = MockDataLoader.get_coach(coach_id)
    if not coach:
        raise HTTPException(
            status_code=404,
            detail=f"Coach {coach_id} not found",
        )

    # En producción, esto guardaría en BD
    return APIResponse(
        status="success",
        code=201,
        data={
            "message": "Session design created successfully",
            "sessionId": f"session_{coach_id}_{int(__import__('time').time())}",
        },
    )


@router.post("/{session_id}/publish", response_model=APIResponse)
async def publish_session(
    session_id: str,
    athlete_id: str,
) -> dict:
    """Publica un diseño de sesión a un athlete"""
    session = MockDataLoader.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session design {session_id} not found",
        )

    athlete = MockDataLoader.get_athlete(athlete_id)
    if not athlete:
        raise HTTPException(
            status_code=404,
            detail=f"Athlete {athlete_id} not found",
        )

    # En producción, esto guardaría en BD
    return APIResponse(
        status="success",
        code=200,
        data={
            "message": f"Session published to {athlete.get('name')}",
            "sessionId": session_id,
            "athleteId": athlete_id,
            "publishedAt": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
        },
    )


@router.get("/{session_id}/blocks", response_model=APIResponse)
async def get_session_blocks(session_id: str) -> dict:
    """Obtiene los bloques de una sesión"""
    session = MockDataLoader.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session design {session_id} not found",
        )

    return APIResponse(
        status="success",
        code=200,
        data={
            "sessionId": session_id,
            "blocks": session.get("blocks", []),
            "totalDuration": sum(b.get("duration", 0) for b in session.get("blocks", [])),
        },
    )


@router.get("/{session_id}/safety-tips", response_model=APIResponse)
async def get_safety_tips(session_id: str) -> dict:
    """Obtiene los consejos de seguridad de una sesión"""
    session = MockDataLoader.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session design {session_id} not found",
        )

    return APIResponse(
        status="success",
        code=200,
        data={
            "sessionId": session_id,
            "safetyTips": session.get("safetyTips", []),
        },
    )
