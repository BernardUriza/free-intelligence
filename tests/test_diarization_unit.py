"""
Unit tests for diarization service
Card: FI-BACKEND-FEAT-004
"""

from backend.diarization_service import DiarizationSegment, merge_consecutive_segments


def test_merge_consecutive_same_speaker() -> None:
    """Test merging consecutive segments from same speaker."""
    segments = [
        DiarizationSegment(0.0, 5.0, "PACIENTE", "Hola doctor"),
        DiarizationSegment(5.1, 10.0, "PACIENTE", "Me duele la cabeza"),
        DiarizationSegment(10.5, 15.0, "MEDICO", "Desde cuándo?"),
    ]

    merged = merge_consecutive_segments(segments)

    assert len(merged) == 2
    assert merged[0].speaker == "PACIENTE"
    assert merged[0].text == "Hola doctor Me duele la cabeza"
    assert merged[0].end_time == 10.0
    assert merged[1].speaker == "MEDICO"


def test_merge_no_merge_different_speakers() -> None:
    """Test no merge when speakers different."""
    segments = [
        DiarizationSegment(0.0, 5.0, "PACIENTE", "Text 1"),
        DiarizationSegment(5.5, 10.0, "MEDICO", "Text 2"),
    ]

    merged = merge_consecutive_segments(segments)

    assert len(merged) == 2


def test_merge_empty_list() -> None:
    """Test merge with empty list."""
    merged = merge_consecutive_segments([])
    assert len(merged) == 0


def test_merge_single_segment() -> None:
    """Test merge with single segment."""
    segments = [DiarizationSegment(0.0, 5.0, "PACIENTE", "Text")]
    merged = merge_consecutive_segments(segments)
    assert len(merged) == 1


def test_merge_large_gap_no_merge() -> None:
    """Test no merge when gap > 1 second."""
    segments = [
        DiarizationSegment(0.0, 5.0, "PACIENTE", "Text 1"),
        DiarizationSegment(7.0, 10.0, "PACIENTE", "Text 2"),  # 2s gap
    ]

    merged = merge_consecutive_segments(segments)

    assert len(merged) == 2  # Should NOT merge


def test_segment_dataclass() -> None:
    """Test DiarizationSegment dataclass."""
    seg = DiarizationSegment(
        start_time=0.0, end_time=5.5, speaker="MEDICO", text="Test text", confidence=0.95
    )

    assert seg.start_time == 0.0
    assert seg.end_time == 5.5
    assert seg.speaker == "MEDICO"
    assert seg.text == "Test text"
    assert seg.confidence == 0.95
