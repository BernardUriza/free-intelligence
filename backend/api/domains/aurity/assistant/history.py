"""Assistant History API - Conversation search and retrieval.

Semantic search over conversation history for doctors.

Endpoints:
- POST /history/search - Search conversation history
- GET  /history/timeline - Get timeline of sessions
- GET  /history/stats - Get history statistics
- GET  /history/paginated - Get paginated history (infinite scroll)

Migrated from: backend/api/routers/assistant/public/assistant_history.py
"""

from __future__ import annotations

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.services.llm.services.conversation_memory import get_memory_manager
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .schemas import (
    HistorySearchRequest,
    HistorySearchResponse,
    InteractionResult,
    TimelineResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/history/search", response_model=HistorySearchResponse)
async def search_history(
    request: HistorySearchRequest,
    audit_service: DIAuditService = Depends(get_audit_service),
) -> HistorySearchResponse:
    """Search conversation history using semantic search.

    Leverages existing embedding infrastructure to find relevant
    past interactions similar to the query.

    Example:
        Query: "hipertensión tratamiento"
        Returns: All past conversations about hypertension treatment,
                 ranked by semantic similarity.
    """
    try:
        logger.info(
            "HISTORY_SEARCH_START",
            doctor_id=request.doctor_id,
            query=request.query,
            limit=request.limit,
            session_filter=request.session_id,
        )

        memory = get_memory_manager(request.doctor_id)

        context = memory.get_context(
            current_message=request.query,
            session_id=request.session_id,
        )

        all_results = context.relevant + context.recent
        all_results.sort(key=lambda x: x.similarity, reverse=True)

        results = all_results[: request.limit]

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
        audit_service.log_action(
            action="history_search_failed",
            user_id=request.doctor_id,
            resource="conversation_history",
            result="failure",
            details={"error": str(e), "query": request.query, "session_id": request.session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"History search failed: {e!s}",
        ) from e


@router.get("/history/timeline", response_model=TimelineResponse)
async def get_timeline(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
    audit_service: DIAuditService = Depends(get_audit_service),
) -> TimelineResponse:
    """Get timeline of all conversation sessions.

    Returns chronological list of sessions with metadata.
    Useful for "conversation history" UI view.

    Note: Session grouping feature is NOT IMPLEMENTED yet.
    Currently returns empty sessions array.
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

        logger.warning(
            "HISTORY_TIMELINE_NOT_IMPLEMENTED",
            doctor_id=doctor_id,
            total_interactions=stats["total_interactions"],
            message="Timeline endpoint called but session grouping not implemented",
        )

        return TimelineResponse(
            sessions=[],
            total_sessions=0,
            total_interactions=stats["total_interactions"],
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No conversation history found for doctor {doctor_id}",
        ) from None
    except Exception as e:
        audit_service.log_action(
            action="history_timeline_failed",
            user_id=doctor_id,
            resource="conversation_timeline",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Timeline retrieval failed: {e!s}",
        ) from e


@router.get("/history/stats")
async def get_history_stats(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
    audit_service: DIAuditService = Depends(get_audit_service),
) -> dict:
    """Get conversation history statistics.

    Returns metadata about doctor's conversation memory:
    - Total interactions
    - Unique sessions
    - Date range (oldest/newest)
    """
    try:
        memory = get_memory_manager(doctor_id)
        stats = memory.get_stats()

        stats_log = {k: v for k, v in stats.items() if k != "doctor_id"}
        logger.info("HISTORY_STATS_RETRIEVED", doctor_id=doctor_id, **stats_log)

        return stats

    except FileNotFoundError:
        return {
            "total_interactions": 0,
            "unique_sessions": 0,
            "memory_index_exists": False,
            "doctor_id": doctor_id,
        }
    except Exception as e:
        audit_service.log_action(
            action="history_stats_failed",
            user_id=doctor_id,
            resource="conversation_stats",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stats retrieval failed: {e!s}",
        ) from e


@router.get("/history/paginated")
async def get_paginated_history(
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=100, description="Messages per page"),
    session_id: str | None = Query(None, description="Filter by session"),
    audit_service: DIAuditService = Depends(get_audit_service),
) -> dict:
    """Get paginated conversation history (for infinite scroll).

    Returns messages in chronological order (newest first).
    Used for infinite scroll implementation in chat UI.

    Example:
        GET /history/paginated?doctor_id=auth0|123&offset=0&limit=50
        → Returns latest 50 messages

        GET /history/paginated?doctor_id=auth0|123&offset=50&limit=50
        → Returns next 50 (older messages)
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

        interactions_dict = [
            {
                "session_id": interaction.session_id,
                "timestamp": interaction.timestamp,
                "role": interaction.role,
                "content": interaction.content,
                "persona": interaction.persona,
                "model": interaction.model,
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
        audit_service.log_action(
            action="history_paginated_failed",
            user_id=doctor_id,
            resource="conversation_history",
            result="failure",
            details={"error": str(e), "offset": offset, "limit": limit, "session_id": session_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paginated history retrieval failed: {e!s}",
        ) from e
