"""Unit tests for ExportService.

Tests the export service with deterministic content generation,
manifest creation, and file integrity verification.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.services.export_service import ExportService


@pytest.fixture
def temp_export_dir():
    """Create temporary export directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def export_service(temp_export_dir):
    """Create ExportService with temporary directory."""
    return ExportService(
        export_dir=temp_export_dir,
        signing_key="test_signing_key_12345",
        git_commit="abc1234",
    )


class TestExportServiceId:
    """Tests for export ID generation."""

    def test_generate_export_id_format(self, export_service):
        """Test export ID format."""
        export_id = export_service.generate_export_id()

        assert export_id.startswith("exp_")
        parts = export_id.split("_")
        assert len(parts) == 3
        assert parts[1].isdigit()
        assert parts[2].isdigit()

    def test_generate_export_id_unique(self, export_service):
        """Test that export IDs are unique."""
        id1 = export_service.generate_export_id()
        id2 = export_service.generate_export_id()

        assert id1 != id2

    def test_generate_export_id_timestamp(self, export_service):
        """Test export ID contains timestamp."""
        before = int(datetime.now(UTC).timestamp())
        export_id = export_service.generate_export_id()
        after = int(datetime.now(UTC).timestamp())

        parts = export_id.split("_")
        ts = int(parts[1])

        assert before <= ts <= after


class TestExportServiceHashing:
    """Tests for SHA256 hashing."""

    def test_compute_sha256_basic(self, export_service):
        """Test SHA256 computation."""
        content = "test content"
        sha256 = export_service.compute_sha256(content)

        assert isinstance(sha256, str)
        assert len(sha256) == 64  # SHA256 hex is 64 chars
        assert sha256.isalnum()

    def test_compute_sha256_deterministic(self, export_service):
        """Test SHA256 is deterministic."""
        content = "deterministic test"
        sha256_1 = export_service.compute_sha256(content)
        sha256_2 = export_service.compute_sha256(content)

        assert sha256_1 == sha256_2

    def test_compute_sha256_different_content(self, export_service):
        """Test different content produces different hash."""
        sha256_1 = export_service.compute_sha256("content 1")
        sha256_2 = export_service.compute_sha256("content 2")

        assert sha256_1 != sha256_2

    def test_compute_sha256_unicode(self, export_service):
        """Test SHA256 with unicode content."""
        content = "Тест 测试 テスト"
        sha256 = export_service.compute_sha256(content)

        assert len(sha256) == 64


class TestExportServiceManifestSigning:
    """Tests for manifest signing."""

    def test_sign_manifest_format(self, export_service):
        """Test manifest signature format."""
        manifest = {
            "exportId": "exp_123",
            "sessionId": "session_123",
            "files": [],
        }

        signature = export_service.sign_manifest(manifest, "test_key")

        assert signature.startswith("HS256.")
        assert len(signature) > 7  # "HS256." + hash

    def test_sign_manifest_deterministic(self, export_service):
        """Test manifest signing is deterministic."""
        manifest = {
            "exportId": "exp_123",
            "sessionId": "session_123",
            "files": [],
        }

        sig1 = export_service.sign_manifest(manifest, "test_key")
        sig2 = export_service.sign_manifest(manifest, "test_key")

        assert sig1 == sig2

    def test_sign_manifest_key_sensitive(self, export_service):
        """Test signature changes with different keys."""
        manifest = {
            "exportId": "exp_123",
            "sessionId": "session_123",
            "files": [],
        }

        sig1 = export_service.sign_manifest(manifest, "key1")
        sig2 = export_service.sign_manifest(manifest, "key2")

        assert sig1 != sig2

    def test_sign_manifest_order_insensitive(self, export_service):
        """Test signing is order-insensitive due to sort_keys=True."""
        manifest1 = {
            "exportId": "exp_123",
            "sessionId": "session_123",
            "files": [],
        }
        manifest2 = {
            "sessionId": "session_123",
            "files": [],
            "exportId": "exp_123",
        }

        sig1 = export_service.sign_manifest(manifest1, "test_key")
        sig2 = export_service.sign_manifest(manifest2, "test_key")

        assert sig1 == sig2


class TestExportServiceManifestCreation:
    """Tests for manifest creation."""

    def test_create_manifest_basic(self, export_service):
        """Test basic manifest creation."""
        files = [
            {"name": "session.json", "sha256": "abc123", "bytes": 100},
        ]

        manifest = export_service.create_manifest(
            export_id="exp_123",
            session_id="session_123",
            files=files,
        )

        assert manifest["exportId"] == "exp_123"
        assert manifest["sessionId"] == "session_123"
        assert manifest["version"] == "1.0"
        assert manifest["algorithm"] == "sha256"
        assert manifest["files"] == files

    def test_create_manifest_includes_metadata(self, export_service):
        """Test manifest includes metadata."""
        files = []

        manifest = export_service.create_manifest(
            export_id="exp_123",
            session_id="session_123",
            files=files,
        )

        assert "meta" in manifest
        assert manifest["meta"]["generator"] == "FI"
        assert manifest["meta"]["commit"] == "abc1234"
        assert manifest["meta"]["deterministic"] is True

    def test_create_manifest_with_signature(self, export_service):
        """Test manifest with signature."""
        files = []
        signature = "HS256.abc123def456"

        manifest = export_service.create_manifest(
            export_id="exp_123",
            session_id="session_123",
            files=files,
            signature=signature,
        )

        assert manifest["signature"] == signature

    def test_create_manifest_timestamp_format(self, export_service):
        """Test manifest timestamp is ISO 8601."""
        files = []

        manifest = export_service.create_manifest(
            export_id="exp_123",
            session_id="session_123",
            files=files,
        )

        assert manifest["createdAt"].endswith("Z")
        # Should be parseable as ISO 8601 (just remove Z since isoformat includes +00:00)
        ts_str = manifest["createdAt"][:-1]  # Remove Z
        datetime.fromisoformat(ts_str)


class TestExportServiceCreation:
    """Tests for export creation."""

    def test_create_export_basic(self, export_service):
        """Test basic export creation."""
        content_dict = {
            "json": '{"test": "data"}',
            "md": "# Test\n\nMarkdown content",
        }

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json", "md"],
        )

        assert "export_id" in result
        assert result["session_id"] == "session_123"
        assert "artifacts" in result
        assert len(result["artifacts"]) == 3  # json + md + manifest

    def test_create_export_validation_session_id(self, export_service):
        """Test export creation validates session_id."""
        with pytest.raises(ValueError, match="session_id required"):
            export_service.create_export(
                session_id="",
                content_dict={"json": "{}"},
                formats=["json"],
            )

    def test_create_export_validation_formats(self, export_service):
        """Test export creation validates formats."""
        with pytest.raises(ValueError, match="At least one format required"):
            export_service.create_export(
                session_id="session_123",
                content_dict={"json": "{}"},
                formats=[],
            )

    def test_create_export_missing_format_graceful(self, export_service):
        """Test export handles missing format gracefully (skips with warning)."""
        content_dict = {
            "json": '{"test": "data"}',
        }

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json", "md"],  # md not provided - should be skipped
        )

        # Should still succeed but only include json + manifest
        # json artifact + manifest = 2
        assert len(result["artifacts"]) == 2
        formats = [a["format"] for a in result["artifacts"]]
        assert "json" in formats
        assert "manifest" in formats
        assert "md" not in formats

    def test_create_export_files_created(self, export_service):
        """Test export creates files on disk."""
        content_dict = {
            "json": '{"test": "data"}',
        }

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]
        export_path = export_service.export_dir / export_id

        assert (export_path / "session.json").exists()
        assert (export_path / "manifest.json").exists()

    def test_create_export_artifacts_contain_hashes(self, export_service):
        """Test export artifacts contain SHA256 hashes."""
        content_dict = {
            "json": '{"test": "data"}',
        }

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        for artifact in result["artifacts"]:
            assert "sha256" in artifact
            assert "bytes" in artifact
            assert "format" in artifact

    def test_create_export_deterministic(self, export_service):
        """Test export creation is deterministic (same content = same hash)."""
        content_dict = {
            "json": '{"test": "data"}',
        }

        result1 = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        # Get hash of json artifact
        json_artifact = next(a for a in result1["artifacts"] if a["format"] == "json")
        hash1 = json_artifact["sha256"]

        # Create same export again with different service instance
        service2 = ExportService(
            export_dir=export_service.export_dir,
            signing_key="different_key",
        )
        result2 = service2.create_export(
            session_id="session_456",
            content_dict=content_dict,
            formats=["json"],
        )

        json_artifact2 = next(a for a in result2["artifacts"] if a["format"] == "json")
        hash2 = json_artifact2["sha256"]

        # Content hash should be same (different export_id/session shouldn't affect content hash)
        assert hash1 == hash2


class TestExportServiceMetadata:
    """Tests for export metadata retrieval."""

    def test_get_export_metadata_success(self, export_service):
        """Test successful metadata retrieval."""
        content_dict = {"json": '{"test": "data"}'}

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]
        metadata = export_service.get_export_metadata(export_id)

        assert metadata is not None
        assert metadata["export_id"] == export_id
        assert metadata["session_id"] == "session_123"
        assert "artifacts" in metadata

    def test_get_export_metadata_not_found(self, export_service):
        """Test metadata retrieval returns None for missing export."""
        # Service returns None for nonexistent export (graceful)
        metadata = export_service.get_export_metadata("nonexistent_id_should_not_exist")

        assert metadata is None

    def test_get_export_metadata_includes_artifacts(self, export_service):
        """Test metadata includes all artifacts."""
        content_dict = {
            "json": '{"test": "data"}',
            "md": "# Test",
        }

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json", "md"],
        )

        export_id = result["export_id"]
        metadata = export_service.get_export_metadata(export_id)

        assert len(metadata["artifacts"]) >= 2


class TestExportServiceVerification:
    """Tests for export verification."""

    def test_verify_export_success(self, export_service):
        """Test successful export verification."""
        content_dict = {"json": '{"test": "data"}'}

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]
        verify_result = export_service.verify_export(
            export_id=export_id,
            targets=["json", "manifest"],
        )

        assert verify_result["ok"] is True
        assert len(verify_result["results"]) == 2

    def test_verify_export_manifest_signature(self, export_service):
        """Test manifest signature verification."""
        content_dict = {"json": '{"test": "data"}'}

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]
        verify_result = export_service.verify_export(
            export_id=export_id,
            targets=["manifest"],
        )

        assert verify_result["ok"] is True
        manifest_result = verify_result["results"][0]
        assert manifest_result["target"] == "manifest"
        assert manifest_result["ok"] is True

    def test_verify_export_file_not_found(self, export_service):
        """Test verification raises IOError for missing export."""
        # Implementation raises IOError for nonexistent export
        with pytest.raises(IOError, match="not found"):
            export_service.verify_export(
                export_id="nonexistent_id_verify_test",
                targets=["json"],
            )

    def test_verify_export_hash_mismatch(self, export_service):
        """Test verification detects tampered files."""
        content_dict = {"json": '{"test": "data"}'}

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]

        # Tamper with the file
        export_path = export_service.export_dir / export_id
        json_file = export_path / "session.json"
        json_file.write_text('{"tampered": true}', encoding="utf-8")

        # Verification should fail
        verify_result = export_service.verify_export(
            export_id=export_id,
            targets=["json"],
        )

        assert verify_result["ok"] is False
        json_result = verify_result["results"][0]
        assert json_result["ok"] is False
        assert "Hash mismatch" in json_result["message"]

    def test_verify_export_multiple_targets(self, export_service):
        """Test verification of multiple targets."""
        content_dict = {
            "json": '{"test": "data"}',
            "md": "# Test",
        }

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json", "md"],
        )

        export_id = result["export_id"]
        verify_result = export_service.verify_export(
            export_id=export_id,
            targets=["json", "md", "manifest"],
        )

        assert len(verify_result["results"]) == 3
        assert all(r["ok"] for r in verify_result["results"])


class TestExportServiceDeletion:
    """Tests for export deletion."""

    def test_delete_export_success(self, export_service):
        """Test successful export deletion (soft delete)."""
        content_dict = {"json": '{"test": "data"}'}

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]
        delete_result = export_service.delete_export(export_id)

        assert delete_result is True

        # Verify .deleted marker exists
        export_path = export_service.export_dir / export_id
        assert (export_path / ".deleted").exists()

    def test_delete_export_not_found(self, export_service):
        """Test deletion returns False for missing export."""
        delete_result = export_service.delete_export("nonexistent_id")

        assert delete_result is False

    def test_delete_export_audit_trail(self, export_service):
        """Test deletion preserves files for audit trail."""
        content_dict = {"json": '{"test": "data"}'}

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]
        export_path = export_service.export_dir / export_id

        # Delete
        export_service.delete_export(export_id)

        # Files should still exist (soft delete)
        assert (export_path / "session.json").exists()
        assert (export_path / "manifest.json").exists()

    def test_delete_export_timestamp(self, export_service):
        """Test deletion records timestamp."""
        content_dict = {"json": '{"test": "data"}'}

        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json"],
        )

        export_id = result["export_id"]
        export_path = export_service.export_dir / export_id

        export_service.delete_export(export_id)

        # Read deletion timestamp
        delete_marker = export_path / ".deleted"
        delete_timestamp = delete_marker.read_text(encoding="utf-8")

        # Should be parseable as ISO 8601 (isoformat includes timezone offset)
        datetime.fromisoformat(delete_timestamp)


class TestExportServiceIntegration:
    """Integration tests for export operations."""

    def test_full_export_lifecycle(self, export_service):
        """Test complete export lifecycle: create -> verify -> delete."""
        content_dict = {
            "json": '{"test": "data", "count": 42}',
            "md": "# Test Session\n\nThis is a test",
        }

        # Create
        result = export_service.create_export(
            session_id="session_123",
            content_dict=content_dict,
            formats=["json", "md"],
        )

        export_id = result["export_id"]
        assert result["session_id"] == "session_123"

        # Get metadata
        metadata = export_service.get_export_metadata(export_id)
        assert metadata is not None
        assert len(metadata["artifacts"]) == 3

        # Verify
        verify_result = export_service.verify_export(
            export_id=export_id,
            targets=["json", "md", "manifest"],
        )
        assert verify_result["ok"] is True

        # Delete
        delete_result = export_service.delete_export(export_id)
        assert delete_result is True

    def test_multiple_exports_isolation(self, export_service):
        """Test multiple exports don't interfere with each other."""
        result1 = export_service.create_export(
            session_id="session_1",
            content_dict={"json": '{"session": 1}'},
            formats=["json"],
        )

        result2 = export_service.create_export(
            session_id="session_2",
            content_dict={"json": '{"session": 2}'},
            formats=["json"],
        )

        export_id1 = result1["export_id"]
        export_id2 = result2["export_id"]

        assert export_id1 != export_id2

        # Verify both are intact
        verify1 = export_service.verify_export(
            export_id=export_id1,
            targets=["json"],
        )
        verify2 = export_service.verify_export(
            export_id=export_id2,
            targets=["json"],
        )

        assert verify1["ok"] is True
        assert verify2["ok"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
