"""Athlete Live Sessions API Router.

Live session tracking + KATNISS analysis (SESION-04/05)

File: backend/api/sessions/athlete_sessions.py
Reorganized: 2025-11-08 (moved from backend/api/athlete_sessions.py)
"""

#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Athlete Live Sessions API (SESION-04/05)

FastAPI router for live athlete session tracking + KATNISS analysis.

File: backend/api/athlete_sessions.py
Cards: FI-STRIDE-SESION-04, FI-STRIDE-SESION-05
Created: 2025-11-06

Endpoints:
- POST /api/athlete-sessions/start -> Start live session
- POST /api/athlete-sessions/{session_id}/rep -> Track rep completion
- POST /api/athlete-sessions/{session_id}/emotional-check -> Emotional check-in
- POST /api/athlete-sessions/{session_id}/end -> End session + trigger KATNISS analysis
- GET /api/athlete-sessions/{session_id} -> Get session data
"""

from datetime import timezone, datetime
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2:7b"

# ============================================================================
# PYDANTIC MODELS (API contracts)
# ============================================================================


class StartSessionRequest(BaseModel):
    """Start athlete session"""

    athlete_id: str = Field(..., description="Athlete UUID")
    exercise_name: str = Field(..., description="Exercise name (e.g., 'Press de Pecho')")
    target_reps: int = Field(default=20, description="Target repetitions")
    max_heart_rate: Optional[int] = Field(None, description="Max safe heart rate (bpm)")


class StartSessionResponse(BaseModel):
    """Session started"""

    session_id: str = Field(..., description="Unique session UUID")
    athlete_id: str
    exercise_name: str
    target_reps: int
    max_heart_rate: Optional[int]
    started_at: str  # ISO 8601
    status: str = "active"


class RepTrackingRequest(BaseModel):
    """Track rep completion"""

    rep_number: int = Field(..., description="Rep count (1, 2, 3...)")
    heart_rate: Optional[int] = Field(None, description="Current HR (bpm)")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp")


class EmotionalCheckRequest(BaseModel):
    """Emotional check-in (1-5 scale)"""

    feeling: int = Field(..., ge=1, le=5, description="Emotional state 1-5")
    # 1=tired, 2=fatigued, 3=normal, 4=good, 5=excellent
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp")


class EndSessionRequest(BaseModel):
    """End session + trigger analysis"""

    reps_completed: int = Field(..., description="Total reps completed")
    session_time: int = Field(..., description="Session duration (seconds)")
    final_emotional_check: int = Field(..., ge=1, le=5, description="Final feeling 1-5")
    avg_heart_rate: Optional[int] = Field(None, description="Average HR (bpm)")


class SessionData(BaseModel):
    """Session data model"""

    session_id: str
    athlete_id: str
    exercise_name: str
    target_reps: int
    reps_completed: int
    session_time: int  # seconds
    emotional_checks: list[int] = Field(default_factory=list)
    heart_rates: list[int] = Field(default_factory=list)
    started_at: str
    ended_at: Optional[str] = None
    status: str = "active"


class KAtnissAnalysisResponse(BaseModel):
    """KATNISS post-session analysis"""

    session_id: str
    athlete_id: str
    analysis: str = Field(..., description="KATNISS motivation message")
    achievement: Optional[str] = Field(None, description="Achievement unlocked")
    next_recommendation: str = Field(..., description="Recommendation for next session")
    personal_record_beat: bool = Field(default=False)
    goal_achieved: bool = Field(default=False)


class SessionResponse(BaseModel):
    """Complete session response"""

    data: SessionData
    analysis: Optional[KAtnissAnalysisResponse] = None


# ============================================================================
# IN-MEMORY STORAGE (temporary - replace with DB)
# ============================================================================

sessions_db: dict[str, SessionData] = {}
session_history: dict[str, list[SessionData]] = {}  # athlete_id -> [sessions]

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/athlete-sessions", tags=["athlete-sessions"])


@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """Start live athlete session (SESION-04)"""
    session_id = f"session_{datetime.now(timezone.utc).isoformat().replace(':', '').replace('-', '')}"

    session = SessionData(
        session_id=session_id,
        athlete_id=request.athlete_id,
        exercise_name=request.exercise_name,
        target_reps=request.target_reps,
        reps_completed=0,
        session_time=0,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    sessions_db[session_id] = session

    logger.info(f"Session started: {session_id} for athlete {request.athlete_id}")

    return StartSessionResponse(
        session_id=session_id,
        athlete_id=request.athlete_id,
        exercise_name=request.exercise_name,
        target_reps=request.target_reps,
        max_heart_rate=request.max_heart_rate,
        started_at=session.started_at,
    )


@router.post("/{session_id}/rep")
async def track_rep(session_id: str, request: RepTrackingRequest):
    """Track rep completion"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = sessions_db[session_id]
    session.reps_completed = request.rep_number

    if request.heart_rate:
        session.heart_rates.append(request.heart_rate)

    logger.info(f"Rep tracked: {session_id} rep #{request.rep_number}")

    return {
        "session_id": session_id,
        "reps_completed": session.reps_completed,
        "target_reps": session.target_reps,
        "progress_percent": (session.reps_completed / session.target_reps) * 100,
    }


@router.post("/{session_id}/emotional-check")
async def emotional_check(session_id: str, request: EmotionalCheckRequest):
    """Emotional check-in during session"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = sessions_db[session_id]
    session.emotional_checks.append(request.feeling)

    # KATNISS adaptive feedback (no penalties)
    katniss_feedback = {
        1: "Descansa cuando lo necesites. ¡Eres fuerte! 💪",
        2: "Un pequeño descanso está bien. Vuelve cuando estés listo.",
        3: "¡Vamos! Un poco más 🌟",
        4: "¡Muy bien! ¡Continúa así! 😊",
        5: "¡Wow! ¡Increíble energía! 🚀",
    }

    logger.info(f"Emotional check: {session_id} feeling={request.feeling}")

    return {
        "session_id": session_id,
        "feeling": request.feeling,
        "katniss_feedback": katniss_feedback.get(request.feeling, ""),
    }


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(session_id: str, request: EndSessionRequest):
    """End session + trigger KATNISS analysis (SESION-05)"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = sessions_db[session_id]
    session.reps_completed = request.reps_completed
    session.session_time = request.session_time
    session.emotional_checks.append(request.final_emotional_check)
    session.status = "completed"
    session.ended_at = datetime.now(timezone.utc).isoformat()

    if request.avg_heart_rate:
        session.heart_rates.append(request.avg_heart_rate)

    # KATNISS Analysis (simulate Ollama)
    analysis = _generate_katniss_analysis(session, request)

    # Store in athlete history
    if session.athlete_id not in session_history:
        session_history[session.athlete_id] = []
    session_history[session.athlete_id].append(session)

    logger.info(f"Session ended: {session_id}")

    return SessionResponse(data=session, analysis=analysis)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session data with analysis"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = sessions_db[session_id]
    analysis = None

    if session.status == "completed":
        analysis = _generate_katniss_analysis(
            session,
            EndSessionRequest(
                reps_completed=session.reps_completed,
                session_time=session.session_time,
                final_emotional_check=session.emotional_checks[-1]
                if session.emotional_checks
                else 3,
                avg_heart_rate=None,  # Not tracked in this context
            ),
        )

    return SessionResponse(data=session, analysis=analysis)


# ============================================================================
# COACH FEEDBACK (UX-COACH-04)
# ============================================================================


class CoachFeedbackRequest(BaseModel):
    """Coach sends feedback to athlete"""

    coach_id: str = Field(..., description="Coach UUID")
    athlete_id: str = Field(..., description="Athlete UUID")
    session_id: str = Field(..., description="Session UUID")
    emoji_feedback: str = Field(..., description="Emoji reaction (👍, 🌟, 💪, 🎉)")
    text_feedback: Optional[str] = Field(None, description="Optional text message")


class CoachFeedbackResponse(BaseModel):
    """Feedback sent"""

    feedback_id: str
    coach_id: str
    athlete_id: str
    session_id: str
    emoji: str
    message: Optional[str]
    sent_at: str


# In-memory feedback storage
feedbacks_db: dict[str, list[CoachFeedbackResponse]] = {}  # athlete_id -> [feedbacks]


@router.post("/coach-feedback", response_model=CoachFeedbackResponse)
async def send_coach_feedback(request: CoachFeedbackRequest):
    """Coach sends feedback to athlete (one-tap emoji + optional text)"""

    feedback_id = f"feedback_{datetime.now(timezone.utc).isoformat().replace(':', '').replace('-', '')}"

    feedback = CoachFeedbackResponse(
        feedback_id=feedback_id,
        coach_id=request.coach_id,
        athlete_id=request.athlete_id,
        session_id=request.session_id,
        emoji=request.emoji_feedback,
        message=request.text_feedback,
        sent_at=datetime.now(timezone.utc).isoformat(),
    )

    # Store feedback
    if request.athlete_id not in feedbacks_db:
        feedbacks_db[request.athlete_id] = []
    feedbacks_db[request.athlete_id].append(feedback)

    logger.info(
        f"Coach feedback sent: {request.coach_id} → {request.athlete_id} ({request.emoji_feedback})"
    )

    return feedback


@router.get("/athlete/{athlete_id}/feedbacks")
async def get_athlete_feedbacks(athlete_id: str):
    """Get all feedbacks for an athlete"""
    feedbacks = feedbacks_db.get(athlete_id, [])
    return {
        "athlete_id": athlete_id,
        "feedbacks": feedbacks,
        "count": len(feedbacks),
    }


# ============================================================================
# HELPERS
# ============================================================================


def _generate_katniss_analysis(
    session: SessionData, request: EndSessionRequest
) -> KAtnissAnalysisResponse:
    """Generate KATNISS motivation message via Ollama"""

    # Achievement logic
    achievement = None
    if request.reps_completed >= 15:
        achievement = "🌟 ¡SESIÓN EXCELENTE! 🌟"
    if request.reps_completed == session.target_reps:
        achievement = "🎉 ¡OBJETIVO ALCANZADO! 🎉"
    if request.reps_completed > session.target_reps:
        achievement = "🏆 ¡NUEVO RÉCORD PERSONAL! 🏆"

    # Recommendation based on performance
    if request.reps_completed >= session.target_reps:
        next_recommendation = "Intentemos aumentar 2-3 repeticiones más. ¡Eres fuerte! 💪"
    elif request.reps_completed >= 15:
        next_recommendation = "Casi lo lograste. Descansa bien y volveremos a intentarlo. 🌟"
    else:
        next_recommendation = "Cada repetición te hace más fuerte. ¡Vuelve pronto!"

    # KATNISS analysis from Ollama
    analysis_text = _query_ollama_katniss(session, request)

    return KAtnissAnalysisResponse(
        session_id=session.session_id,
        athlete_id=session.athlete_id,
        analysis=analysis_text,
        achievement=achievement,
        next_recommendation=next_recommendation,
        personal_record_beat=request.reps_completed > session.target_reps,
        goal_achieved=request.reps_completed >= session.target_reps,
    )


def _query_ollama_katniss(session: SessionData, request: EndSessionRequest) -> str:
    """Query Ollama for KATNISS motivation (with fallback)"""

    prompt = f"""Eres KATNISS, una coach de IA inspirada en Katniss Everdeen (The Hunger Games).
Personalidad: Eres una mujer fuerte, resiliente, auténtica y vulnerablemente valiente.
- No tienes miedo de mostrar emociones reales, pero siempre mantienes el enfoque
- Eres protectora con los que entrenas, como Katniss protege a Prim
- Inspiras esperanza y defiance ante la adversidad
- Liderazgo auténtico: hablas desde el corazón, no desde un script
- Reconoces la verdadera fuerza: perseverancia emocional + fortaleza física
- Valores: libertad, justicia, proteger a los débiles, nunca rendirse

El atleta acaba de completar una sesión de entrenamiento:
- Ejercicio: {session.exercise_name}
- Reps completadas: {request.reps_completed} de {session.target_reps}
- Tiempo: {request.session_time} segundos
- Estado emocional: {request.final_emotional_check}/5

Dale motivación auténtica y visceral. Reconoce su esfuerzo real. Sé breve, directa y genuina.
Responde SOLO con 1-2 oraciones en español. Sin explicaciones, sin "según mis datos".
Habla como Katniss: cruda, honesta, inspiradora."""

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            if response.status_code == 200:
                data = response.json()
                text = data.get("response", "").strip()
                if text:
                    return text
    except Exception as e:
        logger.warning(f"Ollama error: {e}, using fallback")

    # Fallback if Ollama unavailable
    if request.reps_completed >= session.target_reps:
        return (
            "¡Excelente trabajo! Tu esfuerzo y dedicación son increíbles. Eres más fuerte cada día."
        )
    elif request.reps_completed >= 15:
        return "¡Casi lo lograste! Cada repetición te hace más fuerte. Vuelve pronto. 💪"
    else:
        return "¡Buen trabajo! Cada repetición te hace más fuerte. Sigue adelante."
