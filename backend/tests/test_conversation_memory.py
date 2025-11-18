"""
Tests for Conversation Memory Manager

Verifies:
- Memory index initialization
- Interaction storage with embeddings
- Cross-session semantic search
- Context retrieval (recent + relevant)
- Hierarchical prompt building

Run: pytest backend/tests/test_conversation_memory.py -v
"""

import tempfile
from pathlib import Path

import pytest

from backend.services.llm.conversation_memory import ConversationMemoryManager


@pytest.fixture
def temp_memory_path(monkeypatch):
    """Use temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(
            "backend.services.llm.conversation_memory.MEMORY_INDEX_PATH",
            Path(tmpdir),
        )
        yield Path(tmpdir)


def test_memory_initialization(temp_memory_path):
    """Test that memory index initializes correctly."""
    doctor_id = "test-doctor-001"
    memory = ConversationMemoryManager(doctor_id=doctor_id)

    # Verify H5 file created
    expected_path = temp_memory_path / doctor_id / "conversation_memory.h5"
    assert expected_path.exists()

    # Verify empty stats
    stats = memory.get_stats()
    assert stats["total_interactions"] == 0
    assert stats["unique_sessions"] == 0
    assert stats["doctor_id"] == doctor_id


def test_store_and_retrieve_interactions(temp_memory_path):
    """Test storing interactions and retrieving context."""
    doctor_id = "test-doctor-002"
    memory = ConversationMemoryManager(doctor_id=doctor_id)

    # Store some interactions in session 1
    memory.store_interaction(
        session_id="session-001",
        role="user",
        content="Patient complains of chest pain",
        persona="clinical_advisor",
    )

    memory.store_interaction(
        session_id="session-001",
        role="assistant",
        content="Let's evaluate cardiovascular symptoms. Any history of heart disease?",
        persona="clinical_advisor",
    )

    memory.store_interaction(
        session_id="session-001",
        role="user",
        content="No previous cardiac history",
        persona="clinical_advisor",
    )

    # Verify stats
    stats = memory.get_stats()
    assert stats["total_interactions"] == 3
    assert stats["unique_sessions"] == 1

    # Get context for related query
    context = memory.get_context(
        current_message="What are the risk factors for heart attack?",
        session_id="session-001",
    )

    # Should retrieve recent interactions from session
    assert len(context.recent) == 3
    assert context.recent[0].role == "user"
    assert "chest pain" in context.recent[0].content


def test_cross_session_semantic_search(temp_memory_path):
    """Test semantic search across multiple sessions."""
    doctor_id = "test-doctor-003"
    memory = ConversationMemoryManager(doctor_id=doctor_id)

    # Session 1: Cardiovascular case
    memory.store_interaction(
        session_id="session-001",
        role="user",
        content="Patient has high blood pressure and chest pain",
        persona="clinical_advisor",
    )

    memory.store_interaction(
        session_id="session-001",
        role="assistant",
        content="These are concerning cardiovascular symptoms",
        persona="clinical_advisor",
    )

    # Session 2: Diabetes case
    memory.store_interaction(
        session_id="session-002",
        role="user",
        content="Patient has elevated blood sugar levels",
        persona="clinical_advisor",
    )

    memory.store_interaction(
        session_id="session-002",
        role="assistant",
        content="We should check for diabetes",
        persona="clinical_advisor",
    )

    # Session 3: New cardiovascular case
    memory.store_interaction(
        session_id="session-003",
        role="user",
        content="Patient reports shortness of breath",
        persona="clinical_advisor",
    )

    # Query related to cardiovascular symptoms
    context = memory.get_context(
        current_message="What was the previous case with heart-related symptoms?",
        session_id="session-003",
    )

    # Recent should be from session-003
    assert len(context.recent) > 0
    assert context.recent[0].session_id == "session-003"

    # Relevant should include session-001 (high similarity)
    # but NOT session-002 (diabetes, not cardiovascular)
    assert len(context.relevant) > 0
    relevant_sessions = [i.session_id for i in context.relevant]
    assert "session-001" in relevant_sessions

    # Verify similarity scores
    for interaction in context.relevant:
        assert interaction.similarity > 0.0
        assert interaction.similarity <= 1.0


def test_prompt_building(temp_memory_path):
    """Test enriched prompt building with context."""
    doctor_id = "test-doctor-004"
    memory = ConversationMemoryManager(doctor_id=doctor_id)

    # Store interaction
    memory.store_interaction(
        session_id="session-001",
        role="user",
        content="Patient has fever and cough",
        persona="clinical_advisor",
    )

    memory.store_interaction(
        session_id="session-001",
        role="assistant",
        content="These could be respiratory symptoms",
        persona="clinical_advisor",
    )

    # Get context and build prompt
    context = memory.get_context(
        current_message="Should we test for COVID?",
        session_id="session-001",
    )

    system_prompt = "You are a clinical advisor."
    prompt = memory.build_prompt(
        context=context,
        system_prompt=system_prompt,
        current_message="Should we test for COVID?",
    )

    # Verify prompt structure
    assert "You are a clinical advisor" in prompt
    assert "Recent conversation:" in prompt
    assert "fever and cough" in prompt
    assert "Should we test for COVID?" in prompt
    assert prompt.endswith("Assistant:")


def test_memory_persistence_across_instances(temp_memory_path):
    """Test that memory persists across manager instances."""
    doctor_id = "test-doctor-005"

    # First instance: store data
    memory1 = ConversationMemoryManager(doctor_id=doctor_id)
    memory1.store_interaction(
        session_id="session-001",
        role="user",
        content="Test message",
        persona="general_assistant",
    )

    stats1 = memory1.get_stats()
    assert stats1["total_interactions"] == 1

    # Second instance: verify data persists
    memory2 = ConversationMemoryManager(doctor_id=doctor_id)
    stats2 = memory2.get_stats()
    assert stats2["total_interactions"] == 1

    # Retrieve context from second instance
    context = memory2.get_context(
        current_message="Another test message",
        session_id="session-001",
    )

    assert len(context.recent) == 1
    assert context.recent[0].content == "Test message"


def test_large_context_handling(temp_memory_path):
    """Test handling of many interactions (>buffer_size)."""
    doctor_id = "test-doctor-006"
    memory = ConversationMemoryManager(
        doctor_id=doctor_id,
        recent_buffer_size=3,  # Small buffer
        retrieval_top_k=2,
    )

    # Store 10 interactions
    for i in range(10):
        memory.store_interaction(
            session_id="session-001",
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message number {i}",
            persona="general_assistant",
        )

    # Get context
    context = memory.get_context(
        current_message="What was message number 0?",
        session_id="session-001",
    )

    # Recent should only have last 3
    assert len(context.recent) == 3
    assert "Message number 9" in context.recent[-1].content

    # Relevant should find old message semantically
    assert len(context.relevant) <= 2  # top_k=2


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
