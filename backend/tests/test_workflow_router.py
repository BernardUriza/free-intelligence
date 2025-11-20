"""Tests for Workflow Router - Two-Model Strategy.

Verifies intelligent workflow orchestration and cost tracking.
"""

from __future__ import annotations

import pytest

from backend.models.task_type import TaskType
from backend.services.workflow_router import (
    WorkflowRouter,
    calculate_routing_cost,
    calculate_savings,
    get_workflow_router,
)


class TestCostCalculations:
    """Test suite for cost calculation utilities"""

    def test_calculate_routing_cost(self):
        """Test routing cost calculation (Haiku pricing)"""
        # Example: 100 input tokens, 50 output tokens
        cost = calculate_routing_cost(input_tokens=100, output_tokens=50)

        # Expected: (100/1M * $0.25) + (50/1M * $1.25)
        # = 0.000025 + 0.0000625 = 0.0000875
        assert cost > 0
        assert cost < 0.001  # Should be very cheap

    def test_calculate_savings_from_skipped_tasks(self):
        """Test savings calculation from skipped tasks"""
        # Skip 2 tasks, each ~1500 tokens
        savings = calculate_savings(tasks_skipped=2, avg_tokens_per_task=1500)

        # Expected: (2 * 1500 / 1M) * $3.00 = 0.009
        assert savings > 0
        assert savings == pytest.approx(0.009, rel=0.01)

    def test_zero_skipped_tasks(self):
        """Test savings with no skipped tasks"""
        savings = calculate_savings(tasks_skipped=0)
        assert savings == 0.0


class TestWorkflowRouter:
    """Test suite for WorkflowRouter"""

    def test_router_singleton(self):
        """Test that get_workflow_router returns the same instance"""
        router1 = get_workflow_router()
        router2 = get_workflow_router()
        assert router1 is router2

    def test_route_short_audio_skips_diarization(self):
        """Test that short audio (<30s) skips diarization"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_001",
            audio_duration_seconds=15.0,  # Short audio
            existing_tasks=[],
        )

        # Should skip diarization (audio < 30s)
        assert TaskType.DIARIZATION.value not in decision["workflows"]
        assert "skipped" in decision["reasoning"].lower()
        assert decision["cost"].execution_tokens_saved > 0

    def test_route_long_audio_includes_diarization(self):
        """Test that long audio (>30s) includes diarization"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_002",
            audio_duration_seconds=120.0,  # Long audio
            existing_tasks=[],
        )

        # Should include diarization (audio > 30s)
        assert TaskType.DIARIZATION.value in decision["workflows"]
        assert TaskType.SOAP_GENERATION.value in decision["workflows"]
        assert TaskType.EMOTION_ANALYSIS.value in decision["workflows"]

    def test_skip_already_completed_tasks(self):
        """Test that already completed tasks are skipped"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_003",
            audio_duration_seconds=60.0,
            existing_tasks=[TaskType.TRANSCRIPTION.value, TaskType.DIARIZATION.value],
        )

        # Should skip transcription and diarization (already done)
        assert TaskType.TRANSCRIPTION.value not in decision["workflows"]
        assert TaskType.DIARIZATION.value not in decision["workflows"]

        # Should include SOAP and EMOTION (depends on diarization, which exists)
        assert TaskType.SOAP_GENERATION.value in decision["workflows"]
        assert TaskType.EMOTION_ANALYSIS.value in decision["workflows"]

    def test_transcription_always_first_if_needed(self):
        """Test that transcription is prioritized if not completed"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_004",
            audio_duration_seconds=60.0,
            existing_tasks=[],
        )

        # Transcription should be first workflow
        assert decision["workflows"][0] == TaskType.TRANSCRIPTION.value

    def test_cost_tracking_in_decision(self):
        """Test that routing decision includes cost metrics"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_005",
            audio_duration_seconds=60.0,
            existing_tasks=[],
        )

        # Cost object should be present
        assert "cost" in decision
        cost = decision["cost"]

        # Cost fields should be populated
        assert cost.routing_tokens > 0
        assert cost.routing_cost_usd > 0
        assert cost.routing_cost_usd < 0.01  # Should be very cheap

    def test_reasoning_explanation_provided(self):
        """Test that routing decision includes reasoning"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_006",
            audio_duration_seconds=60.0,
            existing_tasks=[],
        )

        # Reasoning should explain each decision
        assert "reasoning" in decision
        assert len(decision["reasoning"]) > 0
        assert "|" in decision["reasoning"]  # Multiple reasoning parts

    def test_parallel_execution_flag(self):
        """Test that parallel execution flag is set correctly"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_007",
            audio_duration_seconds=60.0,
            existing_tasks=[],
        )

        # Should indicate if parallel execution possible
        assert "parallel" in decision
        assert isinstance(decision["parallel"], bool)

    def test_skip_soap_when_no_diarization_context(self):
        """Test that SOAP is skipped if no diarization (short audio)"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_008",
            audio_duration_seconds=20.0,  # Short, no diarization
            existing_tasks=[],
        )

        # Should skip SOAP (needs diarization context)
        assert TaskType.SOAP_GENERATION.value not in decision["workflows"]
        assert "SOAP skipped" in decision["reasoning"]

    def test_skip_emotion_when_no_diarization_context(self):
        """Test that emotion analysis is skipped if no diarization"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_009",
            audio_duration_seconds=25.0,  # Short, no diarization
            existing_tasks=[],
        )

        # Should skip emotion (needs patient segments from diarization)
        assert TaskType.EMOTION_ANALYSIS.value not in decision["workflows"]
        assert "Emotion analysis skipped" in decision["reasoning"]

    def test_workflow_decision_structure(self):
        """Test that routing decision has expected structure"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="test_session_010",
            audio_duration_seconds=60.0,
            existing_tasks=[],
        )

        # Verify expected fields
        assert "workflows" in decision
        assert "reasoning" in decision
        assert "parallel" in decision
        assert "cost" in decision
        assert "session_id" in decision

        # Verify types
        assert isinstance(decision["workflows"], list)
        assert isinstance(decision["reasoning"], str)
        assert isinstance(decision["parallel"], bool)


class TestWorkflowDependencies:
    """Test suite for workflow dependency resolution"""

    def test_soap_requires_diarization(self):
        """Test SOAP generation requires diarization"""
        router = WorkflowRouter()

        # Long audio, but diarization already done
        decision = router.route_workflows(
            session_id="test_dep_001",
            audio_duration_seconds=120.0,
            existing_tasks=[TaskType.DIARIZATION.value],
        )

        # SOAP should be included (diarization exists)
        assert TaskType.SOAP_GENERATION.value in decision["workflows"]

    def test_emotion_requires_diarization(self):
        """Test emotion analysis requires diarization"""
        router = WorkflowRouter()

        # Long audio, but diarization already done
        decision = router.route_workflows(
            session_id="test_dep_002",
            audio_duration_seconds=120.0,
            existing_tasks=[TaskType.DIARIZATION.value],
        )

        # Emotion should be included (diarization exists)
        assert TaskType.EMOTION_ANALYSIS.value in decision["workflows"]


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""

    def test_new_session_full_workflow(self):
        """Test routing for new session (no existing tasks)"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="integration_001",
            audio_duration_seconds=180.0,
            existing_tasks=[],
        )

        # Should include all workflows
        expected_workflows = [
            TaskType.TRANSCRIPTION.value,
            TaskType.DIARIZATION.value,
            TaskType.SOAP_GENERATION.value,
            TaskType.EMOTION_ANALYSIS.value,
        ]

        for workflow in expected_workflows:
            assert workflow in decision["workflows"]

    def test_resume_session_partial_completion(self):
        """Test routing for session with some tasks completed"""
        router = WorkflowRouter()

        decision = router.route_workflows(
            session_id="integration_002",
            audio_duration_seconds=180.0,
            existing_tasks=[
                TaskType.TRANSCRIPTION.value,
                TaskType.DIARIZATION.value,
            ],
        )

        # Should skip completed tasks
        assert TaskType.TRANSCRIPTION.value not in decision["workflows"]
        assert TaskType.DIARIZATION.value not in decision["workflows"]

        # Should include remaining tasks
        assert TaskType.SOAP_GENERATION.value in decision["workflows"]
        assert TaskType.EMOTION_ANALYSIS.value in decision["workflows"]

        # Should show cost savings
        assert decision["cost"].execution_tokens_saved > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
