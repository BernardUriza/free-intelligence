"""
Free Intelligence - Corpus API Service (FastAPI)

RESTful API for corpus analytics and session management.

File: backend/fi_corpus_api.py
Created: 2025-10-28
Port: 9001 (as per PORTS.md)

Endpoints:
  GET    /api/corpus/stats           - Get corpus statistics
  GET    /api/sessions/summary       - Get sessions summary with previews
  GET    /api/sessions/{id}          - Get single session details
  GET    /health                     - Health check

Usage:
  uvicorn backend.fi_corpus_api:app --reload --port 9001 --host 0.0.0.0
"""

import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import h5py
from fastapi import FastAPI, HTTPException
from fastapi import Path as PathParam
from fastapi import Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class CorpusStats(BaseModel):
    """Corpus statistics response model"""

    total_interactions: int = Field(..., description="Total number of interactions")
    total_sessions: int = Field(..., description="Total number of unique sessions")
    total_tokens: int = Field(..., description="Total tokens processed")
    corpus_size_bytes: int = Field(..., description="Size of corpus file in bytes")
    date_range: dict[str, str] = Field(..., description="Earliest and latest timestamps")
    models_used: dict[str, int] = Field(..., description="Count of interactions per model")


class SessionSummary(BaseModel):
    """Session summary response model"""

    session_id: str = Field(..., description="Unique session identifier")
    interaction_count: int = Field(..., description="Number of interactions in session")
    total_tokens: int = Field(..., description="Total tokens in session")
    first_timestamp: str = Field(..., description="First interaction timestamp")
    last_timestamp: str = Field(..., description="Last interaction timestamp")
    preview: str = Field(..., description="Preview of first prompt (max 200 chars)")


class SessionDetail(BaseModel):
    """Detailed session response model"""

    session_id: str
    interactions: list[dict[str, Any]]
    total_tokens: int
    first_timestamp: str
    last_timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    corpus_path: str
    corpus_exists: bool
    timestamp: str


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Free Intelligence - Corpus API",
    description="Local-first corpus analytics and session management",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (allow Aurity frontend on port 9000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9000",
        "http://127.0.0.1:9000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Corpus path (default to storage/corpus.h5)
CORPUS_PATH = Path(__file__).parent.parent / "storage" / "corpus.h5"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_corpus_path() -> Path:
    """Get corpus path from environment or default"""
    env_path = os.getenv("FI_CORPUS_PATH")
    if env_path:
        return Path(env_path)
    return CORPUS_PATH


def verify_corpus_exists() -> bool:
    """Verify corpus file exists"""
    corpus_path = get_corpus_path()
    return corpus_path.exists() and corpus_path.is_file()


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    corpus_path = get_corpus_path()
    return HealthResponse(
        status="healthy",
        corpus_path=str(corpus_path),
        corpus_exists=verify_corpus_exists(),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@app.get("/api/corpus/stats", response_model=CorpusStats, tags=["corpus"])
async def get_corpus_stats():
    """
    Get corpus statistics

    Returns:
        - Total interactions
        - Total sessions
        - Total tokens
        - Corpus size
        - Date range
        - Models used
    """
    corpus_path = get_corpus_path()

    if not verify_corpus_exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus not found at {corpus_path}",
        )

    try:
        with h5py.File(str(corpus_path), "r") as f:
            interactions = f["interactions"]

            # Get total interactions
            total_interactions = interactions["session_id"].shape[0]

            # Get unique sessions
            session_ids_raw = interactions["session_id"][:]
            session_ids = [
                s.decode("utf-8") if isinstance(s, bytes) else str(s) for s in session_ids_raw
            ]
            unique_sessions = set(session_ids)
            total_sessions = len(unique_sessions)

            # Get total tokens
            tokens = interactions["tokens"][:]
            total_tokens = int(tokens.sum())

            # Get date range
            timestamps_raw = interactions["timestamp"][:]
            timestamps = [
                t.decode("utf-8") if isinstance(t, bytes) else str(t) for t in timestamps_raw
            ]
            earliest = min(timestamps) if len(timestamps) > 0 else ""
            latest = max(timestamps) if len(timestamps) > 0 else ""

            # Get models used
            models_raw = interactions["model"][:]
            models = [m.decode("utf-8") if isinstance(m, bytes) else str(m) for m in models_raw]
            models_count: dict[str, int] = defaultdict(int)
            for model in models:
                models_count[model] += 1

            # Get corpus file size
            corpus_size = corpus_path.stat().st_size

            return CorpusStats(
                total_interactions=total_interactions,
                total_sessions=total_sessions,
                total_tokens=total_tokens,
                corpus_size_bytes=corpus_size,
                date_range={"earliest": earliest, "latest": latest},
                models_used=dict(models_count),
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read corpus: {str(e)}",
        )


@app.get("/api/sessions/summary", response_model=list[SessionSummary], tags=["sessions"])
async def get_sessions_summary(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
):
    """
    Get sessions summary with previews

    Returns list of sessions sorted by most recent first.
    Each session includes:
    - Session ID
    - Interaction count
    - Total tokens
    - First/last timestamps
    - Preview of first prompt
    """
    corpus_path = get_corpus_path()

    if not verify_corpus_exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus not found at {corpus_path}",
        )

    try:
        with h5py.File(str(corpus_path), "r") as f:
            interactions = f["interactions"]

            # Read all data
            session_ids_raw = interactions["session_id"][:]
            timestamps_raw = interactions["timestamp"][:]
            prompts_raw = interactions["prompt"][:]
            tokens = interactions["tokens"][:]

            # Decode bytes to strings
            session_ids = [
                s.decode("utf-8") if isinstance(s, bytes) else str(s) for s in session_ids_raw
            ]
            timestamps = [
                t.decode("utf-8") if isinstance(t, bytes) else str(t) for t in timestamps_raw
            ]
            prompts = [p.decode("utf-8") if isinstance(p, bytes) else str(p) for p in prompts_raw]

            # Group by session
            sessions_data: dict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "interaction_count": 0,
                    "total_tokens": 0,
                    "first_timestamp": "",
                    "last_timestamp": "",
                    "preview": "",
                    "timestamps": [],
                }
            )

            for i in range(len(session_ids)):
                session_id = session_ids[i]
                session_data = sessions_data[session_id]

                session_data["interaction_count"] += 1
                session_data["total_tokens"] += int(tokens[i])
                session_data["timestamps"].append(timestamps[i])

                # Store first prompt as preview
                if not session_data["preview"]:
                    session_data["preview"] = prompts[i][:200]

            # Create session summaries
            summaries = []
            for session_id, data in sessions_data.items():
                # Sort timestamps to get first/last
                sorted_timestamps = sorted(data["timestamps"])

                summaries.append(
                    SessionSummary(
                        session_id=session_id,
                        interaction_count=data["interaction_count"],
                        total_tokens=data["total_tokens"],
                        first_timestamp=sorted_timestamps[0],
                        last_timestamp=sorted_timestamps[-1],
                        preview=data["preview"],
                    )
                )

            # Sort by last timestamp (most recent first)
            summaries.sort(key=lambda x: x.last_timestamp, reverse=True)

            # Apply pagination
            return summaries[offset : offset + limit]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read sessions: {str(e)}",
        )


@app.get("/api/sessions/{session_id}", response_model=SessionDetail, tags=["sessions"])
async def get_session_detail(
    session_id: str = PathParam(..., description="Session ID to retrieve"),
):
    """
    Get detailed session information

    Returns all interactions for a specific session.
    """
    corpus_path = get_corpus_path()

    if not verify_corpus_exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus not found at {corpus_path}",
        )

    try:
        with h5py.File(str(corpus_path), "r") as f:
            interactions = f["interactions"]

            # Read all data
            session_ids_raw = interactions["session_id"][:]
            interaction_ids_raw = interactions["interaction_id"][:]
            timestamps_raw = interactions["timestamp"][:]
            prompts_raw = interactions["prompt"][:]
            responses_raw = interactions["response"][:]
            models_raw = interactions["model"][:]
            tokens = interactions["tokens"][:]

            # Decode bytes to strings
            session_ids = [
                s.decode("utf-8") if isinstance(s, bytes) else str(s) for s in session_ids_raw
            ]
            interaction_ids = [
                i.decode("utf-8") if isinstance(i, bytes) else str(i) for i in interaction_ids_raw
            ]
            timestamps = [
                t.decode("utf-8") if isinstance(t, bytes) else str(t) for t in timestamps_raw
            ]
            prompts = [p.decode("utf-8") if isinstance(p, bytes) else str(p) for p in prompts_raw]
            responses = [
                r.decode("utf-8") if isinstance(r, bytes) else str(r) for r in responses_raw
            ]
            models = [m.decode("utf-8") if isinstance(m, bytes) else str(m) for m in models_raw]

            # Filter by session_id
            session_interactions = []
            session_timestamps = []
            total_tokens = 0

            for i in range(len(session_ids)):
                if session_ids[i] == session_id:
                    session_interactions.append(
                        {
                            "interaction_id": interaction_ids[i],
                            "timestamp": timestamps[i],
                            "prompt": prompts[i],
                            "response": responses[i],
                            "model": models[i],
                            "tokens": int(tokens[i]),
                        }
                    )
                    session_timestamps.append(timestamps[i])
                    total_tokens += int(tokens[i])

            if not session_interactions:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )

            # Sort by timestamp
            sorted_timestamps = sorted(session_timestamps)

            return SessionDetail(
                session_id=session_id,
                interactions=session_interactions,
                total_tokens=total_tokens,
                first_timestamp=sorted_timestamps[0],
                last_timestamp=sorted_timestamps[-1],
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read session: {str(e)}",
        )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Log startup info"""
    corpus_path = get_corpus_path()
    print("🚀 FI Corpus API starting on port 9001")
    print(f"📁 Corpus path: {corpus_path}")
    print(f"✅ Corpus exists: {verify_corpus_exists()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown"""
    print("🛑 FI Corpus API shutting down")


# ============================================================================
# MAIN (for direct execution)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.fi_corpus_api:app",
        host="0.0.0.0",
        port=9001,
        reload=True,
        log_level="info",
    )
