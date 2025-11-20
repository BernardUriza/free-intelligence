"""
Free-Intelligence Conversation History API

Allows users to search and retrieve their conversation history
using semantic search over stored embeddings.

Author: Bernard Uriza Orozco
Created: 2025-11-20
Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.services.llm.conversation_memory import get_memory_manager

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================


class HistorySearchRequest(BaseModel):
    """Request for semantic search over conversation history."""

    query: str = Field(..., min_length=1, description="Search query (semantic)")
    doctor_id: str = Field(..., description="Doctor ID (Auth0 user.sub)")
    limit: int = Field(default=10, ge=1, le=50, description="Max results")
    session_id: str | None = Field(None, description="Filter by session")


class InteractionResult(BaseModel):
    """Single interaction from history."""

    session_id: str
    timestamp: int
    role: str  # "user" or "assistant"
    content: str
    persona: str | None = None
    similarity: float = Field(description="Semantic similarity score (0-1)")


class HistorySearchResponse(BaseModel):
    """Search results with metadata."""

    results: list[InteractionResult]
    total_interactions: int = Field(description="Total interactions in memory")
    query: str


class SessionSummary(BaseModel):
    """Summary of a conversation session."""

    session_id: str
    start_timestamp: int
    end_timestamp: int
    interaction_count: int
    preview: str = Field(description="First user message as preview")


class TimelineResponse(BaseModel):
    """Timeline of conversation sessions."""

    sessions: list[SessionSummary]
    total_sessions: int
    total_interactions: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/assistant/history/search", response_model=HistorySearchResponse)
async def search_history(request: HistorySearchRequest) -> HistorySearchResponse:
    """Search conversation history using semantic search.

    Leverages existing embedding infrastructure to find relevant
    past interactions similar to the query.

    Example:
        Query: "hipertensión tratamiento"
        Returns: All past conversations about hypertension treatment,
                 ranked by semantic similarity.

    Args:
        request: Search query with doctor_id and filters

    Returns:
        List of relevant interactions with similarity scores

    Raises:
        404: If doctor has no conversation history
        500: If search fails
    """
    try:
        logger.info(
            "HISTORY_SEARCH_START",
            doctor_id=request.doctor_id,
            query=request.query,
            limit=request.limit,
            session_filter=request.session_id,
        )

        # Get memory manager for doctor
        memory = get_memory_manager(request.doctor_id)

        # Get context (which does semantic search internally)
        context = memory.get_context(
            current_message=request.query,
            session_id=request.session_id,
        )

        # Combine recent + relevant, sorted by similarity
        all_results = context.relevant + context.recent
        all_results.sort(key=lambda x: x.similarity, reverse=True)

        # Limit results
        results = all_results[: request.limit]

        # Convert to response format
        interaction_results = [
            InteractionResult(
                session_id=interaction.session_id,
                timestamp=interaction.timestamp,
                role=interaction.role,
                content=interaction.content,
                persona=interaction.persona,
                similarity=interaction.similarity,
            )
            for interaction in results
        ]

        logger.info(
            "HISTORY_SEARCH_SUCCESS",
            doctor_id=request.doctor_id,
            results_count=len(interaction_results),
            total_interactions=context.total_interactions,
        )

        return HistorySearchResponse(
            results=interaction_results,
            total_interactions=context.total_interactions,
            query=request.query,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No conversation history found for doctor {request.doctor_id}",
        ) from None
    except Exception as e:
        logger.error(
            "HISTORY_SEARCH_FAILED",
            doctor_id=request.doctor_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"History search failed: {e!s}",
        ) from e


@router.get("/assistant/history/timeline", response_model=TimelineResponse)
async def get_timeline(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
) -> TimelineResponse:
    """Get timeline of all conversation sessions.

    Returns chronological list of sessions with metadata.
    Useful for "conversation history" UI view.

    Args:
        doctor_id: Doctor identifier

    Returns:
        Timeline with session summaries

    Raises:
        404: If doctor has no conversation history
        500: If timeline retrieval fails
    """
    try:
        logger.info("HISTORY_TIMELINE_START", doctor_id=doctor_id)

        memory = get_memory_manager(doctor_id)
        stats = memory.get_stats()

        if stats["total_interactions"] == 0:
            return TimelineResponse(
                sessions=[],
                total_sessions=0,
                total_interactions=0,
            )

        # ⚠️ NOT IMPLEMENTED: Session grouping feature
        # This endpoint is a placeholder for future implementation.
        # Currently returns empty sessions array.
        # To implement: Add memory.get_sessions() method that groups interactions
        # by session boundaries (time gaps, explicit session markers, etc.)

        logger.warning(
            "HISTORY_TIMELINE_NOT_IMPLEMENTED",
            doctor_id=doctor_id,
            total_interactions=stats["total_interactions"],
            message="Timeline endpoint called but session grouping not implemented",
        )

        return TimelineResponse(
            sessions=[],  # Empty - session grouping not implemented
            total_sessions=0,  # Would be stats.get("unique_sessions", 0) when implemented
            total_interactions=stats["total_interactions"],
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No conversation history found for doctor {doctor_id}",
        ) from None
    except Exception as e:
        logger.error(
            "HISTORY_TIMELINE_FAILED",
            doctor_id=doctor_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Timeline retrieval failed: {e!s}",
        ) from e


@router.get("/assistant/history/stats")
async def get_history_stats(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
) -> dict:
    """Get conversation history statistics.

    Returns metadata about doctor's conversation memory:
    - Total interactions
    - Unique sessions
    - Date range (oldest/newest)

    Args:
        doctor_id: Doctor identifier

    Returns:
        Statistics dictionary
    """
    try:
        memory = get_memory_manager(doctor_id)
        stats = memory.get_stats()

        logger.info("HISTORY_STATS_RETRIEVED", doctor_id=doctor_id, **stats)

        return stats

    except FileNotFoundError:
        return {
            "total_interactions": 0,
            "unique_sessions": 0,
            "memory_index_exists": False,
            "doctor_id": doctor_id,
        }
    except Exception as e:
        logger.error(
            "HISTORY_STATS_FAILED",
            doctor_id=doctor_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stats retrieval failed: {e!s}",
        ) from e


@router.get("/assistant/history/paginated")
async def get_paginated_history(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=100, description="Messages per page"),
    session_id: str | None = Query(None, description="Filter by session"),
) -> dict:
    """Get paginated conversation history (for infinite scroll).

    Returns messages in chronological order (newest first).
    Used for infinite scroll implementation in chat UI.

    Example:
        GET /assistant/history/paginated?doctor_id=auth0|123&offset=0&limit=50
        → Returns latest 50 messages

        GET /assistant/history/paginated?doctor_id=auth0|123&offset=50&limit=50
        → Returns next 50 (older messages)

    Args:
        doctor_id: Doctor identifier
        offset: Skip this many messages (0 = latest)
        limit: Max messages to return
        session_id: Optional session filter

    Returns:
        Dict with interactions, total, has_more
    """
    try:
        logger.info(
            "HISTORY_PAGINATED_START",
            doctor_id=doctor_id,
            offset=offset,
            limit=limit,
            session_filter=session_id,
        )

        memory = get_memory_manager(doctor_id)
        result = memory.get_paginated_history(
            offset=offset,
            limit=limit,
            session_id=session_id,
        )

        # Convert Interaction objects to serializable dicts
        interactions_dict = [
            {
                "session_id": interaction.session_id,
                "timestamp": interaction.timestamp,
                "role": interaction.role,
                "content": interaction.content,
                "persona": interaction.persona,
            }
            for interaction in result["interactions"]
        ]

        logger.info(
            "HISTORY_PAGINATED_SUCCESS",
            doctor_id=doctor_id,
            returned=len(interactions_dict),
            total=result["total"],
            has_more=result["has_more"],
        )

        return {
            "interactions": interactions_dict,
            "total": result["total"],
            "has_more": result["has_more"],
            "offset": offset,
            "limit": limit,
        }

    except FileNotFoundError:
        return {
            "interactions": [],
            "total": 0,
            "has_more": False,
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        logger.error(
            "HISTORY_PAGINATED_FAILED",
            doctor_id=doctor_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paginated history retrieval failed: {e!s}",
        ) from e
