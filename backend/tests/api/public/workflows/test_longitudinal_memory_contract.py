"""Smoke tests for Longitudinal Memory API contract.

Ensures that the rename from "unified_timeline" to "longitudinal_memory"
doesn't break the API contract for external clients.

Card: FI-PHIL-DOC-014
Created: 2025-12-07
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_memory_route_registration_check() -> None:
    """Verify longitudinal memory routes are properly registered in router."""
    from backend.core.services.workflow.api.public.workflows_router import router

    routes = [r.path for r in router.routes if hasattr(r, "path")]

    # Check stable routes exist
    assert "/workflows/aurity/timeline/memory" in routes, (
        "Main longitudinal memory endpoint not registered"
    )

    assert "/workflows/aurity/timeline/memory/stats" in routes, "Stats endpoint not registered"

    assert "/workflows/aurity/timeline/memory/search" in routes, "Search endpoint not registered"


def test_memory_response_schema_structure() -> None:
    """Verify LongitudinalMemoryResponse has correct structure."""
    from backend.core.services.memory.api.public.longitudinal_memory import (
        LongitudinalMemoryResponse,
    )

    # Check schema has required fields
    schema = LongitudinalMemoryResponse.model_json_schema()
    props = schema.get("properties", {})

    assert "events" in props, "Missing 'events' field in schema"
    assert "total" in props, "Missing 'total' field in schema"
    assert "has_more" in props, "Missing 'has_more' field in schema"
    assert "offset" in props, "Missing 'offset' field in schema"
    assert "limit" in props, "Missing 'limit' field in schema"
    assert "chat_count" in props, "Missing 'chat_count' field in schema"
    assert "audio_count" in props, "Missing 'audio_count' field in schema"


def test_memory_event_schema_structure() -> None:
    """Verify MemoryEvent has correct structure."""
    from backend.core.services.memory.api.public.longitudinal_memory import MemoryEvent

    schema = MemoryEvent.model_json_schema()
    props = schema.get("properties", {})
    required = schema.get("required", [])

    # Required fields
    assert "id" in required, "Event 'id' should be required"
    assert "timestamp" in required, "Event 'timestamp' should be required"
    assert "event_type" in required, "Event 'event_type' should be required"
    assert "content" in required, "Event 'content' should be required"
    assert "source" in required, "Event 'source' should be required"

    # Check enums
    event_type_enum = props.get("event_type", {}).get("enum", [])
    assert "chat_user" in event_type_enum
    assert "chat_assistant" in event_type_enum
    assert "transcription" in event_type_enum

    source_enum = props.get("source", {}).get("enum", [])
    assert "chat" in source_enum
    assert "audio" in source_enum


def test_memory_stats_response_schema_structure() -> None:
    """Verify MemoryStatsResponse has correct structure."""
    from backend.core.services.memory.api.public.longitudinal_memory import MemoryStatsResponse

    schema = MemoryStatsResponse.model_json_schema()
    props = schema.get("properties", {})

    assert "total_events" in props
    assert "chat_messages" in props
    assert "audio_transcriptions" in props
    assert "unique_sessions" in props
    assert "oldest_timestamp" in props
    assert "newest_timestamp" in props


def test_stable_routes_not_deprecated() -> None:
    """Verify stable routes are NOT marked as deprecated."""
    from backend.core.services.workflow.api.public.workflows_router import router

    routes_with_status = [
        (r.path, getattr(r, "deprecated", False)) for r in router.routes if hasattr(r, "path")
    ]

    # Find stable memory routes
    stable_routes = [
        (path, deprecated) for path, deprecated in routes_with_status if "/timeline/memory" in path
    ]

    assert len(stable_routes) >= 2, "Expected at least 2 stable memory routes"

    # None of the stable routes should be deprecated (None or False is acceptable)
    for path, deprecated in stable_routes:
        assert deprecated is not True, f"Stable route {path} incorrectly marked as deprecated"
    """Verify stable memory routes are NOT marked as deprecated."""
    from backend.core.services.workflow.api.public.workflows_router import router

    routes_with_status = [
        (r.path, getattr(r, "deprecated", False)) for r in router.routes if hasattr(r, "path")
    ]

    # Find stable memory routes
    stable_routes = [
        (path, deprecated) for path, deprecated in routes_with_status if "/memory" in path
    ]

    assert len(stable_routes) >= 2, "Expected at least 2 stable routes"

    # Stable routes should NOT be deprecated (False or None)
    for path, deprecated in stable_routes:
        assert deprecated is not True, (
            f"Stable route {path} should not be deprecated (got {deprecated})"
        )
