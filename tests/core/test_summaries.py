"""Tests for cross-channel awareness: summaries module."""

import time

from personas.insult.core.summaries import build_server_pulse, filter_by_permissions


class TestBuildServerPulse:
    def test_empty_summaries_returns_empty(self):
        assert build_server_pulse([]) == ""

    def test_formats_multiple_summaries(self):
        now = time.time()
        summaries = [
            {
                "channel_id": "1",
                "channel_name": "tech",
                "summary": "Debugging React hooks",
                "message_count": 8,
                "last_message_ts": now - 1200,
                "is_private": False,
                "updated_at": now - 1200,
            },
            {
                "channel_id": "2",
                "channel_name": "general",
                "summary": "Planeando la peda del viernes",
                "message_count": 12,
                "last_message_ts": now - 3600,
                "is_private": False,
                "updated_at": now - 3600,
            },
        ]
        result = build_server_pulse(summaries)
        assert "## Server Pulse" in result
        assert "#tech" in result
        assert "#general" in result
        assert "Debugging React hooks" in result
        assert "Planeando la peda del viernes" in result

    def test_relevance_filtering_keywords_rank_higher(self):
        now = time.time()
        summaries = [
            {
                "channel_id": "1",
                "channel_name": "random",
                "summary": "People sharing cat memes and jokes",
                "message_count": 20,
                "last_message_ts": now - 600,
                "is_private": False,
                "updated_at": now - 600,
            },
            {
                "channel_id": "2",
                "channel_name": "python",
                "summary": "Discussion about async patterns and pytest fixtures",
                "message_count": 5,
                "last_message_ts": now - 1800,
                "is_private": False,
                "updated_at": now - 1800,
            },
        ]
        # When current message mentions "pytest", python channel should rank higher
        result = build_server_pulse(summaries, current_message="How do I write pytest fixtures?")
        lines = result.strip().split("\n")
        # Find channel lines (skip header)
        channel_lines = [line for line in lines if line.startswith("- #")]
        assert len(channel_lines) == 2
        # Python channel should come first due to keyword match
        assert "#python" in channel_lines[0]

    def test_old_summaries_filtered_out(self):
        now = time.time()
        summaries = [
            {
                "channel_id": "1",
                "channel_name": "old-channel",
                "summary": "Very old conversation",
                "message_count": 5,
                "last_message_ts": now - 100000,
                "is_private": False,
                "updated_at": now - 100000,  # >24h ago
            },
        ]
        result = build_server_pulse(summaries)
        assert result == ""

    def test_max_chars_respected(self):
        now = time.time()
        summaries = [
            {
                "channel_id": str(i),
                "channel_name": f"channel-{i}",
                "summary": "A" * 200,
                "message_count": 10,
                "last_message_ts": now - 60,
                "is_private": False,
                "updated_at": now - 60,
            }
            for i in range(10)
        ]
        result = build_server_pulse(summaries, max_chars=500)
        assert len(result) <= 500


class TestFilterByPermissions:
    def test_filters_inaccessible_channels(self):
        summaries = [
            {"channel_id": "1", "channel_name": "public", "summary": "Open"},
            {"channel_id": "2", "channel_name": "secret", "summary": "Hidden"},
            {"channel_id": "3", "channel_name": "also-public", "summary": "Also open"},
        ]
        accessible = {"1", "3"}
        result = filter_by_permissions(summaries, accessible)
        assert len(result) == 2
        assert result[0]["channel_id"] == "1"
        assert result[1]["channel_id"] == "3"

    def test_empty_accessible_returns_empty(self):
        summaries = [{"channel_id": "1", "channel_name": "ch", "summary": "s"}]
        result = filter_by_permissions(summaries, set())
        assert result == []

    def test_empty_summaries_returns_empty(self):
        result = filter_by_permissions([], {"1", "2"})
        assert result == []
