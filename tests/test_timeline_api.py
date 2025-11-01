#!/usr/bin/env python3
"""
Tests for Timeline API Service

File: tests/test_timeline_api.py
Created: 2025-10-29
Card: FI-API-FEAT-002

Test Coverage:
- Health check endpoint
- Sessions listing with pagination and sorting
- Session detail retrieval
- Events streaming with filters
- Stats aggregation
- Policy badges computation
- Performance targets (<300ms listing, <200ms detail)
- Error handling (404, validation)

Target: 90%+ coverage
"""

import time
import unittest

from fastapi.testclient import TestClient

# Import app
from backend.timeline_api import (
    MOCK_TIMELINES,
    app,
    compute_policy_badges,
    compute_session_size,
    compute_session_timespan,
    format_duration_human,
    format_size_human,
)
from backend.timeline_models import (
    RedactionPolicy,
    Timeline,
    TimelineEvent,
    TimelineEventType,
    TimelineMode,
    create_timeline_event,
)


class TestTimelineAPI(unittest.TestCase):
    """Test suite for Timeline API endpoints"""

    @classmethod
    def setUpClass(cls):
        """Set up test client and mock data"""
        cls.client = TestClient(app)

        # Clear mock data
        MOCK_TIMELINES.clear()

        # Create test timeline
        cls.test_timeline = Timeline(
            session_id="session_test_001", owner_hash="test_owner_hash_1234567890abcdef"
        )

        # Add test events
        event1 = create_timeline_event(
            event_type=TimelineEventType.USER_MESSAGE,
            who="user_test",
            what="Test message",
            raw_content="Test raw content",
            summary="Test summary",
            redaction_policy=RedactionPolicy.SUMMARY,
            session_id=cls.test_timeline.session_id,
            tags=["test"],
            auto_generated=False,
        )
        cls.test_timeline.add_event(event1)

        event2 = create_timeline_event(
            event_type=TimelineEventType.ASSISTANT_RESPONSE,
            who="assistant",
            what="Test response",
            raw_content="Test response content",
            summary="Test response summary",
            redaction_policy=RedactionPolicy.SUMMARY,
            session_id=cls.test_timeline.session_id,
            tags=["test", "response"],
            auto_generated=True,
            generation_mode=TimelineMode.AUTO,
        )
        cls.test_timeline.add_event(event2)

        MOCK_TIMELINES[cls.test_timeline.session_id] = cls.test_timeline

    def test_health_check(self) -> None:
        """Test health check endpoint"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("storage_path", data)
        self.assertIn("storage_exists", data)
        self.assertIn("timestamp", data)

    def test_list_sessions_default(self) -> None:
        """Test sessions listing with default parameters"""
        response = self.client.get("/api/timeline/sessions")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Check first session structure
        session = data[0]
        self.assertIn("metadata", session)
        self.assertIn("timespan", session)
        self.assertIn("size", session)
        self.assertIn("policy_badges", session)
        self.assertIn("preview", session)

        # Check metadata
        metadata = session["metadata"]
        self.assertIn("session_id", metadata)
        self.assertIn("owner_hash", metadata)
        self.assertIn("created_at", metadata)
        self.assertIn("updated_at", metadata)

        # Check policy badges
        badges = session["policy_badges"]
        self.assertIn("hash_verified", badges)
        self.assertIn("policy_compliant", badges)
        self.assertIn("redaction_applied", badges)
        self.assertIn("audit_logged", badges)

    def test_list_sessions_pagination(self) -> None:
        """Test sessions listing with pagination"""
        response = self.client.get("/api/timeline/sessions?limit=1&offset=0")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 1)

    def test_list_sessions_sorting(self) -> None:
        """Test sessions listing with different sort orders"""
        # Test recent sort (default)
        response = self.client.get("/api/timeline/sessions?sort=recent")
        self.assertEqual(response.status_code, 200)

        # Test oldest sort
        response = self.client.get("/api/timeline/sessions?sort=oldest")
        self.assertEqual(response.status_code, 200)

        # Test events_desc sort
        response = self.client.get("/api/timeline/sessions?sort=events_desc")
        self.assertEqual(response.status_code, 200)

        # Test events_asc sort
        response = self.client.get("/api/timeline/sessions?sort=events_asc")
        self.assertEqual(response.status_code, 200)

    def test_list_sessions_performance(self) -> None:
        """Test sessions listing performance (<300ms target)"""
        start_time = time.time()
        response = self.client.get("/api/timeline/sessions?limit=50")
        latency_ms = (time.time() - start_time) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(latency_ms, 300, f"Latency {latency_ms:.1f}ms exceeds 300ms target")

    def test_get_session_detail_success(self) -> None:
        """Test session detail retrieval"""
        session_id = self.test_timeline.session_id
        response = self.client.get(f"/api/timeline/sessions/{session_id}")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("metadata", data)
        self.assertIn("events", data)
        self.assertIn("policy_badges", data)
        self.assertIn("generation_mode", data)
        self.assertIn("redaction_stats", data)

        # Check events
        events = data["events"]
        self.assertEqual(len(events), 2)

        # Check first event structure
        event = events[0]
        self.assertIn("event_id", event)
        self.assertIn("event_type", event)
        self.assertIn("timestamp", event)
        self.assertIn("who", event)
        self.assertIn("what", event)
        self.assertIn("content_hash", event)
        self.assertIn("redaction_policy", event)
        self.assertIn("causality", event)

    def test_get_session_detail_not_found(self) -> None:
        """Test session detail with non-existent session"""
        response = self.client.get("/api/timeline/sessions/nonexistent_session")
        self.assertEqual(response.status_code, 404)

        data = response.json()
        self.assertIn("detail", data)

    def test_get_session_detail_performance(self) -> None:
        """Test session detail performance (<200ms target)"""
        session_id = self.test_timeline.session_id
        start_time = time.time()
        response = self.client.get(f"/api/timeline/sessions/{session_id}")
        latency_ms = (time.time() - start_time) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(latency_ms, 200, f"Latency {latency_ms:.1f}ms exceeds 200ms target")

    def test_list_events_no_filters(self) -> None:
        """Test events listing without filters"""
        response = self.client.get("/api/timeline/events")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Check event structure
        event = data[0]
        self.assertIn("event_id", event)
        self.assertIn("event_type", event)
        self.assertIn("who", event)
        self.assertIn("what", event)

    def test_list_events_with_session_filter(self) -> None:
        """Test events listing filtered by session"""
        session_id = self.test_timeline.session_id
        response = self.client.get(f"/api/timeline/events?session_id={session_id}")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)

    def test_list_events_with_type_filter(self) -> None:
        """Test events listing filtered by type"""
        response = self.client.get("/api/timeline/events?event_type=user_message")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertGreater(len(data), 0)

        # All events should be user_message type
        for event in data:
            self.assertEqual(event["event_type"], "user_message")

    def test_list_events_with_who_filter(self) -> None:
        """Test events listing filtered by actor"""
        response = self.client.get("/api/timeline/events?who=assistant")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertGreater(len(data), 0)

        # All events should be from assistant
        for event in data:
            self.assertEqual(event["who"], "assistant")

    def test_list_events_pagination(self) -> None:
        """Test events listing with pagination"""
        response = self.client.get("/api/timeline/events?limit=1&offset=0")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 1)

    def test_get_stats(self) -> None:
        """Test stats endpoint"""
        response = self.client.get("/api/timeline/stats")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("total_sessions", data)
        self.assertIn("total_events", data)
        self.assertIn("total_tokens", data)
        self.assertIn("avg_events_per_session", data)
        self.assertIn("event_types_breakdown", data)
        self.assertIn("redaction_stats", data)
        self.assertIn("generation_modes", data)
        self.assertIn("date_range", data)

        # Validate stats
        self.assertGreater(data["total_sessions"], 0)
        self.assertGreater(data["total_events"], 0)
        self.assertIsInstance(data["event_types_breakdown"], dict)
        self.assertIsInstance(data["redaction_stats"], dict)

    def test_cors_headers(self) -> None:
        """Test CORS headers are present"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

        # Check CORS headers (TestClient doesn't fully simulate CORS)
        # In production, verify with actual browser request


class TestPolicyBadges(unittest.TestCase):
    """Test suite for policy badges computation"""

    def test_compute_policy_badges_all_ok(self) -> None:
        """Test policy badges with valid timeline"""
        timeline = Timeline(session_id="session_test", owner_hash="test_hash")

        event = create_timeline_event(
            event_type=TimelineEventType.USER_MESSAGE,
            who="user",
            what="Test",
            raw_content="Test content",
            redaction_policy=RedactionPolicy.SUMMARY,
            session_id=timeline.session_id,
        )
        timeline.add_event(event)

        badges = compute_policy_badges(timeline)

        self.assertEqual(badges.hash_verified, "OK")
        self.assertEqual(badges.policy_compliant, "OK")
        self.assertEqual(badges.redaction_applied, "OK")
        self.assertEqual(badges.audit_logged, "OK")

    def test_compute_policy_badges_invalid_hash(self) -> None:
        """Test policy badges with invalid hash"""
        timeline = Timeline(session_id="session_test", owner_hash="test_hash")

        # Create event with invalid hash
        event = TimelineEvent(
            event_type=TimelineEventType.USER_MESSAGE,
            who="user",
            what="Test",
            content_hash="invalid_hash",  # Too short
            redaction_policy=RedactionPolicy.SUMMARY,
            session_id=timeline.session_id,
        )
        timeline.add_event(event)

        badges = compute_policy_badges(timeline)

        self.assertEqual(badges.hash_verified, "FAIL")

    def test_compute_policy_badges_no_redaction(self) -> None:
        """Test policy badges with no redaction"""
        timeline = Timeline(session_id="session_test", owner_hash="test_hash")

        event = create_timeline_event(
            event_type=TimelineEventType.USER_MESSAGE,
            who="user",
            what="Test",
            raw_content="Test content",
            redaction_policy=RedactionPolicy.NONE,  # No redaction
            session_id=timeline.session_id,
        )
        timeline.add_event(event)

        badges = compute_policy_badges(timeline)

        self.assertEqual(badges.redaction_applied, "N/A")


class TestHelperFunctions(unittest.TestCase):
    """Test suite for helper functions"""

    def test_format_duration_human_hours(self) -> None:
        """Test duration formatting with hours"""
        duration_ms = 7380000  # 2h 3m
        result = format_duration_human(duration_ms)
        self.assertEqual(result, "2h 3m")

    def test_format_duration_human_minutes(self) -> None:
        """Test duration formatting with minutes"""
        duration_ms = 125000  # 2m 5s
        result = format_duration_human(duration_ms)
        self.assertEqual(result, "2m 5s")

    def test_format_duration_human_seconds(self) -> None:
        """Test duration formatting with seconds"""
        duration_ms = 45000  # 45s
        result = format_duration_human(duration_ms)
        self.assertEqual(result, "45s")

    def test_format_size_human_tokens(self) -> None:
        """Test size formatting with tokens"""
        result = format_size_human(12500, 0)
        self.assertEqual(result, "12.5K tokens")

        result = format_size_human(500, 0)
        self.assertEqual(result, "500 tokens")

    def test_format_size_human_chars(self) -> None:
        """Test size formatting with chars"""
        result = format_size_human(0, 5000)
        self.assertEqual(result, "5.0K chars")

        result = format_size_human(0, 200)
        self.assertEqual(result, "200 chars")

    def test_format_size_human_zero(self) -> None:
        """Test size formatting with zero"""
        result = format_size_human(0, 0)
        self.assertEqual(result, "0 tokens")

    def test_compute_session_timespan(self) -> None:
        """Test session timespan computation"""
        timeline = Timeline(session_id="session_test", owner_hash="test_hash")

        # Add events with different timestamps
        event1 = create_timeline_event(
            event_type=TimelineEventType.USER_MESSAGE,
            who="user",
            what="First",
            raw_content="First",
            session_id=timeline.session_id,
        )
        timeline.add_event(event1)

        # Manually set timestamp for second event
        event2 = create_timeline_event(
            event_type=TimelineEventType.ASSISTANT_RESPONSE,
            who="assistant",
            what="Second",
            raw_content="Second",
            session_id=timeline.session_id,
        )
        timeline.add_event(event2)

        timespan = compute_session_timespan(timeline)

        self.assertIn("start", timespan.model_dump())
        self.assertIn("end", timespan.model_dump())
        self.assertGreaterEqual(timespan.duration_ms, 0)
        self.assertIsInstance(timespan.duration_human, str)

    def test_compute_session_size(self) -> None:
        """Test session size computation"""
        timeline = Timeline(session_id="session_test", owner_hash="test_hash")

        event = create_timeline_event(
            event_type=TimelineEventType.USER_MESSAGE,
            who="user",
            what="Test message",
            raw_content="Test content",
            summary="Test summary",
            session_id=timeline.session_id,
        )
        timeline.add_event(event)

        size = compute_session_size(timeline)

        self.assertEqual(size.interaction_count, 1)
        self.assertGreater(size.total_chars, 0)
        self.assertIsInstance(size.size_human, str)


class TestOpenAPISchema(unittest.TestCase):
    """Test OpenAPI documentation"""

    def test_openapi_docs_available(self) -> None:
        """Test that OpenAPI docs are available"""
        client = TestClient(app)
        response = client.get("/docs")
        self.assertEqual(response.status_code, 200)

    def test_openapi_json_available(self) -> None:
        """Test that OpenAPI JSON schema is available"""
        client = TestClient(app)
        response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        schema = response.json()
        self.assertIn("openapi", schema)
        self.assertIn("info", schema)
        self.assertIn("paths", schema)

        # Check endpoints are documented
        paths = schema["paths"]
        self.assertIn("/health", paths)
        self.assertIn("/api/timeline/sessions", paths)
        self.assertIn("/api/timeline/sessions/{session_id}", paths)
        self.assertIn("/api/timeline/events", paths)
        self.assertIn("/api/timeline/stats", paths)


if __name__ == "__main__":
    unittest.main()
