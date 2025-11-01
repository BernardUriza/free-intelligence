"""
Tests for Artifact Verifier
Card: FI-GOV-TOOL-001
"""

from pathlib import Path

from tools.verify_artifact import ARTIFACT_REGISTRY, verify_all, verify_artifact


class TestVerifyArtifact:
    """Test artifact verification logic."""

    def test_verify_artifact_exists(self, tmp_path) -> None:
        """Test verification of existing artifact."""
        # Create test artifact
        artifact = tmp_path / "test.py"
        artifact.write_text("# Test artifact")

        result = verify_artifact("TEST-001", "test.py", tmp_path)

        assert result["status"] == "VALID"
        assert result["card_id"] == "TEST-001"
        assert result["artifact"] == "test.py"
        assert "size_kb" in result

    def test_verify_artifact_missing(self, tmp_path) -> None:
        """Test verification of missing artifact."""
        result = verify_artifact("TEST-002", "missing.py", tmp_path)

        assert result["status"] == "MISSING"
        assert result["card_id"] == "TEST-002"
        assert "not found" in result["message"].lower()

    def test_verify_artifact_large_md(self, tmp_path) -> None:
        """Test that large MD files are rejected."""
        # Create large MD file (>150 lines)
        artifact = tmp_path / "large.md"
        artifact.write_text("\n".join([f"Line {i}" for i in range(200)]))

        result = verify_artifact("TEST-003", "large.md", tmp_path)

        assert result["status"] == "INVALID"
        assert "large MD" in result["message"]

    def test_verify_artifact_small_md_allowed(self, tmp_path) -> None:
        """Test that small MD files are allowed."""
        # Create small MD file (<150 lines)
        artifact = tmp_path / "small.md"
        artifact.write_text("\n".join([f"Line {i}" for i in range(50)]))

        result = verify_artifact("TEST-004", "small.md", tmp_path)

        assert result["status"] == "VALID"

    def test_verify_artifact_valid_extensions(self, tmp_path) -> None:
        """Test that valid extensions are accepted."""
        valid_files = [
            "script.py",
            "config.yaml",
            "config.yml",
            "data.json",
            "metrics.prom",
            "data.csv",
            "setup.sh",
            "Makefile",
        ]

        for filename in valid_files:
            artifact = tmp_path / filename
            artifact.write_text("content")

            result = verify_artifact(f"TEST-{filename}", filename, tmp_path)

            assert result["status"] == "VALID", f"Failed for {filename}"

    def test_verify_artifact_invalid_extension(self, tmp_path) -> None:
        """Test that invalid extensions are rejected."""
        artifact = tmp_path / "doc.txt"
        artifact.write_text("content")

        result = verify_artifact("TEST-005", "doc.txt", tmp_path)

        assert result["status"] == "INVALID"
        assert "not executable" in result["message"].lower()


class TestVerifyAll:
    """Test verification of all registered artifacts."""

    def test_verify_all_returns_results(self) -> None:
        """Test that verify_all returns results for all registered artifacts."""
        results = verify_all()

        assert len(results) == len(ARTIFACT_REGISTRY)
        assert all("status" in r for r in results)
        assert all("card_id" in r for r in results)
        assert all("artifact" in r for r in results)

    def test_verify_all_with_custom_path(self, tmp_path) -> None:
        """Test verify_all with custom base path."""
        # Create a subset of required artifacts
        (tmp_path / "eval").mkdir()
        (tmp_path / "eval" / "prompts.csv").write_text("prompt,expected\n")

        results = verify_all(tmp_path)

        assert len(results) > 0
        # Should have at least one result
        assert any(r["artifact"] == "eval/prompts.csv" for r in results)


class TestArtifactRegistry:
    """Test the artifact registry structure."""

    def test_registry_not_empty(self) -> None:
        """Test that registry has entries."""
        assert len(ARTIFACT_REGISTRY) > 0

    def test_registry_has_required_cards(self) -> None:
        """Test that registry includes required governance cards."""
        required_cards = [
            "FI-GOV-TOOL-001",  # Self-reference
            "FI-POLICY-001",  # Policy config
            "FI-EVAL-001",  # Evaluation prompts
        ]

        for card_id in required_cards:
            assert card_id in ARTIFACT_REGISTRY, f"Missing {card_id}"

    def test_registry_paths_are_strings(self) -> None:
        """Test that all registry paths are strings."""
        for card_id, path in ARTIFACT_REGISTRY.items():
            assert isinstance(path, str), f"{card_id} path is not string"
            assert len(path) > 0, f"{card_id} has empty path"

    def test_registry_no_duplicate_paths(self) -> None:
        """Test that each artifact path is unique."""
        paths = list(ARTIFACT_REGISTRY.values())
        assert len(paths) == len(set(paths)), "Duplicate paths in registry"


class TestIntegration:
    """Integration tests with real filesystem."""

    def test_all_registered_artifacts_exist(self) -> None:
        """Test that all registered artifacts exist in the repo."""
        base_path = Path(__file__).parent.parent
        missing = []

        for card_id, artifact_path in ARTIFACT_REGISTRY.items():
            full_path = base_path / artifact_path
            if not full_path.exists():
                missing.append((card_id, artifact_path))

        assert len(missing) == 0, f"Missing artifacts: {missing}"

    def test_verify_artifact_script_executable(self) -> None:
        """Test that verify_artifact.py itself is executable."""
        script_path = Path(__file__).parent.parent / "tools" / "verify_artifact.py"

        assert script_path.exists(), "verify_artifact.py not found"
        assert script_path.stat().st_size > 0, "verify_artifact.py is empty"
        # Check it's executable (Unix permissions)
        import os

        assert os.access(script_path, os.X_OK), "verify_artifact.py not executable"
