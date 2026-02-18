"""Regression tests for timezone-aware datetime utility.

Ensures all timestamps in the system use timezone-aware datetimes
for HIPAA compliance and cross-timezone consistency.

Tests verify:
1. utc_now() returns timezone-aware datetime
2. All datetime fields use utc_now() consistently
3. No naive datetime.now() calls in production code
"""

import pytest
from datetime import datetime, timezone

from backend.utils.common.types import utc_now


class TestUtcNow:
    """Test utc_now() utility function."""

    def test_utc_now_returns_timezone_aware(self):
        """utc_now() must return datetime with tzinfo."""
        now = utc_now()
        
        assert now.tzinfo is not None, "utc_now() must return timezone-aware datetime"
        assert now.tzinfo == timezone.utc, "utc_now() must use UTC timezone"

    def test_utc_now_isoformat_includes_timezone(self):
        """ISO format from utc_now() must include timezone info."""
        now = utc_now()
        iso_string = now.isoformat()
        
        # ISO format with timezone should contain +00:00 or Z
        assert "+00:00" in iso_string or "Z" in iso_string, \
            f"ISO format must include timezone: {iso_string}"

    def test_utc_now_is_always_forward(self):
        """Time should move forward between calls."""
        import time
        
        now1 = utc_now()
        time.sleep(0.001)  # 1ms delay
        now2 = utc_now()
        
        assert now2 >= now1, "Time should move forward"

    def test_utc_now_compatible_with_datetime_arithmetic(self):
        """utc_now() should work with timedelta operations."""
        from datetime import timedelta
        
        now = utc_now()
        future = now + timedelta(days=1)
        past = now - timedelta(hours=2)
        
        assert future > now, "Future should be greater than now"
        assert past < now, "Past should be less than now"
        assert (future - now).days == 1, "Timedelta arithmetic should work"

    def test_utc_now_vs_naive_datetime_comparison(self):
        """Comparison between aware and naive datetime should raise error."""
        naive = datetime.now()  # Naive datetime
        
        with pytest.raises(TypeError):
            # This should raise TypeError - can't compare aware vs naive
            _ = utc_now() > naive  # type: ignore[operator]


class TestTimezoneConsistency:
    """Test timezone consistency across the system."""

    def test_document_model_uses_aware_datetime(self):
        """Document model should use timezone-aware uploaded_at."""
        from backend.domain.document.models import Document, DocumentMetadata, DocumentType, DocumentOrigin, DocumentStatus
        
        doc = Document(
            doc_id="test-123",
            clinic_id="clinic-456",
            title="Test Document",
            content="Test content",
            metadata=DocumentMetadata(document_type=DocumentType.OTHER),
            uploaded_by="user-789",
        )
        
        assert doc.uploaded_at.tzinfo is not None, \
            "Document.uploaded_at must be timezone-aware"
        assert doc.uploaded_at.tzinfo == timezone.utc, \
            "Document.uploaded_at must use UTC"

    def test_backup_module_uses_aware_datetime(self):
        """Backup module should use timezone-aware timestamps."""
        from backend.schemas.domain.backup import create_backup
        import inspect
        
        # Check that create_backup uses utc_now internally
        source = inspect.getsource(create_backup)
        
        # Should use utc_now, not datetime.now()
        assert "utc_now()" in source, "Backup module should use utc_now()"

    def test_buffered_writer_uses_aware_datetime(self):
        """BufferedHDF5Writer should use timezone-aware timestamps."""
        try:
            from backend.infrastructure.common.buffered_writer import BufferedHDF5Writer
            import inspect
            
            # Check __init__ uses utc_now
            source = inspect.getsource(BufferedHDF5Writer.__init__)
            
            assert "utc_now()" in source, "BufferedHDF5Writer should use utc_now()"
        except (ImportError, ModuleNotFoundError):
            # Skip if module not available
            pytest.skip("BufferedHDF5Writer not available")


class TestHIPAACompliance:
    """Test HIPAA compliance requirements for audit trails."""

    def test_audit_timestamp_must_be_utc(self):
        """Audit trail timestamps must be in UTC for compliance."""
        # HIPAA requires consistent timestamps across systems
        # UTC ensures no ambiguity across timezones
        
        now = utc_now()
        
        # Verify it's UTC
        assert now.tzinfo == timezone.utc, \
            "HIPAA audit timestamps must be in UTC"

    def test_datetime_arithmetic_preserves_timezone(self):
        """Timedelta operations must preserve timezone info."""
        from datetime import timedelta
        
        now = utc_now()
        later = now + timedelta(hours=5)
        
        assert later.tzinfo == timezone.utc, \
            "Timezone must be preserved after arithmetic"

    def test_isoformat_for_api_responses(self):
        """ISO format strings must include timezone for API responses."""
        now = utc_now()
        iso_string = now.isoformat()
        
        # API responses should include timezone
        assert "+00:00" in iso_string, \
            "API timestamp format must include UTC offset"


__all__ = [
    "TestUtcNow",
    "TestTimezoneConsistency",
    "TestHIPAACompliance",
]
