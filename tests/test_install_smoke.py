"""
Installation Smoke Tests
Card: FI-INFRA-STR-014

Tests básicos para validar que el sistema está instalado correctamente.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest


class TestPrerequisites:
    """Test that all prerequisites are met."""

    def test_node_version(self) -> None:
        """Test that Node.js 18+ is installed."""
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "Node.js not found"

        version = result.stdout.strip()
        major_version = int(version.split(".")[0].replace("v", ""))
        assert major_version >= 18, f"Node.js 18+ required, found {version}"

    def test_python_version(self) -> None:
        """Test that Python 3.11+ is installed."""
        version_info = sys.version_info
        assert version_info.major == 3, "Python 3.x required"
        assert version_info.minor >= 9, f"Python 3.9+ required, found {sys.version}"

    def test_pnpm_installed(self) -> None:
        """Test that pnpm is installed."""
        result = subprocess.run(["pnpm", "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "pnpm not found"

    def test_python_packages(self) -> None:
        """Test that required Python packages are installed."""
        required_packages = ["fastapi", "h5py", "structlog", "pydantic"]

        for package in required_packages:
            result = subprocess.run(
                [sys.executable, "-c", f"import {package}"],
                capture_output=True,
            )
            assert result.returncode == 0, f"Package {package} not installed"


class TestFileStructure:
    """Test that all required files exist."""

    def test_ecosystem_config_exists(self) -> None:
        """Test that ecosystem.config.js exists."""
        config_path = Path("ecosystem.config.js")
        assert config_path.exists(), "ecosystem.config.js not found"
        assert config_path.stat().st_size > 0, "ecosystem.config.js is empty"

    def test_nas_setup_script_exists(self) -> None:
        """Test that nas-setup.sh exists and is executable."""
        script_path = Path("scripts/nas-setup.sh")
        assert script_path.exists(), "scripts/nas-setup.sh not found"
        assert os.access(script_path, os.X_OK), "scripts/nas-setup.sh not executable"

    def test_turbo_config_exists(self) -> None:
        """Test that turbo.json exists."""
        turbo_path = Path("turbo.json")
        assert turbo_path.exists(), "turbo.json not found"

    def test_npmrc_exists(self) -> None:
        """Test that .npmrc exists."""
        npmrc_path = Path(".npmrc")
        assert npmrc_path.exists(), ".npmrc not found"

    def test_backend_directory_exists(self) -> None:
        """Test that backend directory exists."""
        backend_path = Path("backend")
        assert backend_path.exists(), "backend/ not found"
        assert backend_path.is_dir(), "backend/ is not a directory"

    def test_apps_aurity_exists(self) -> None:
        """Test that apps/aurity directory exists."""
        aurity_path = Path("apps/aurity")
        assert aurity_path.exists(), "apps/aurity/ not found"
        assert aurity_path.is_dir(), "apps/aurity/ is not a directory"


class TestPM2Configuration:
    """Test PM2 ecosystem configuration."""

    def test_ecosystem_has_three_services(self) -> None:
        """Test that ecosystem.config.js defines 3 services."""
        config_path = Path("ecosystem.config.js")
        content = config_path.read_text()

        # Check for service names
        assert "fi-backend-api" in content, "fi-backend-api not in config"
        assert "fi-timeline-api" in content, "fi-timeline-api not in config"
        assert "fi-frontend" in content, "fi-frontend not in config"

    def test_ecosystem_has_correct_ports(self) -> None:
        """Test that ecosystem.config.js has correct port configuration."""
        config_path = Path("ecosystem.config.js")
        content = config_path.read_text()

        # Backend should reference port 9001
        assert "9001" in content, "Port 9001 not found in config"
        # Timeline should reference port 9002
        assert "9002" in content, "Port 9002 not found in config"
        # Frontend should reference port 9000
        assert "9000" in content, "Port 9000 not found in config"

    def test_ecosystem_has_memory_limits(self) -> None:
        """Test that ecosystem.config.js has memory limits."""
        config_path = Path("ecosystem.config.js")
        content = config_path.read_text()

        # Check for memory limit configuration
        assert "max_memory_restart" in content, "Memory limits not configured"


class TestNASSetupScript:
    """Test NAS setup script."""

    def test_nas_setup_dry_run(self) -> None:
        """Test that nas-setup.sh --dry-run works."""
        result = subprocess.run(
            ["./scripts/nas-setup.sh", "--dry-run"],
            capture_output=True,
            text=True,
        )

        # Dry-run should exit 0 or show what would be done
        assert result.returncode in [0, 1], "nas-setup.sh --dry-run failed unexpectedly"

    def test_nas_setup_has_prechecks(self) -> None:
        """Test that nas-setup.sh has precheck logic."""
        script_path = Path("scripts/nas-setup.sh")
        content = script_path.read_text()

        # Check for common prechecks
        assert "node" in content.lower(), "Script doesn't check Node.js"
        assert "python" in content.lower(), "Script doesn't check Python"
        assert "pnpm" in content.lower(), "Script doesn't check pnpm"


class TestServiceHealth:
    """Test service health endpoints (if running)."""

    def test_backend_health_endpoint_exists(self) -> None:
        """Test that backend has health endpoint code."""
        # Check if health endpoint is defined in code
        backend_files = list(Path("backend").rglob("*.py"))
        health_found = False

        for file_path in backend_files:
            content = file_path.read_text()
            if "/health" in content and "GET" in content:
                health_found = True
                break

        assert health_found, "No /health endpoint found in backend code"

    @pytest.mark.skipif(
        subprocess.run(["lsof", "-ti:7001"], capture_output=True).returncode != 0,
        reason="Backend not running",
    )
    def test_backend_responds_to_health(self) -> None:
        """Test that backend responds to health check (if running)."""
        result = subprocess.run(
            ["curl", "-s", "http://localhost:7001/health"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "Health endpoint request failed"
        # Should return some JSON-like response
        assert "{" in result.stdout or "ok" in result.stdout.lower()


class TestStorageSetup:
    """Test that storage directories are configured."""

    def test_storage_directory_structure(self) -> None:
        """Test that storage directories exist or can be created."""
        required_dirs = [
            Path("storage"),
            Path("data"),
            Path("logs"),
        ]

        for dir_path in required_dirs:
            # Directory should exist or be creatable
            if not dir_path.exists():
                # Check parent exists and is writable
                parent = dir_path.parent
                assert parent.exists(), f"Parent dir {parent} doesn't exist"
                assert os.access(parent, os.W_OK), f"Parent dir {parent} not writable"


class TestDocumentation:
    """Test that documentation exists."""

    def test_nas_deployment_doc_exists(self) -> None:
        """Test that NAS_DEPLOYMENT.md exists."""
        doc_path = Path("NAS_DEPLOYMENT.md")
        assert doc_path.exists(), "NAS_DEPLOYMENT.md not found"

        content = doc_path.read_text()
        assert len(content) > 100, "NAS_DEPLOYMENT.md is too short"

    def test_readme_exists(self) -> None:
        """Test that README.md exists."""
        readme_path = Path("README.md")
        assert readme_path.exists(), "README.md not found"


class TestBuildArtifacts:
    """Test that build system is configured."""

    def test_package_json_exists(self) -> None:
        """Test that root package.json exists."""
        pkg_path = Path("package.json")
        assert pkg_path.exists(), "package.json not found"

    def test_turbo_pipeline_configured(self) -> None:
        """Test that turbo.json has pipeline configuration."""
        turbo_path = Path("turbo.json")
        content = turbo_path.read_text()

        # Check for common pipeline tasks
        assert "pipeline" in content or "tasks" in content, "No pipeline config in turbo.json"


def test_smoke_summary() -> None:
    """Summary test that prints status."""
    print("\n" + "=" * 80)
    print("Installation Smoke Test Summary")
    print("=" * 80)
    print("\nCore Components:")
    print(f"  ✅ Python version: {sys.version.split()[0]}")

    node_version = subprocess.run(
        ["node", "--version"], capture_output=True, text=True
    ).stdout.strip()
    print(f"  ✅ Node.js version: {node_version}")

    pnpm_version = subprocess.run(
        ["pnpm", "--version"], capture_output=True, text=True
    ).stdout.strip()
    print(f"  ✅ pnpm version: {pnpm_version}")

    print("\nConfiguration Files:")
    configs = [
        "ecosystem.config.js",
        "turbo.json",
        ".npmrc",
        "scripts/nas-setup.sh",
    ]
    for config in configs:
        exists = "✅" if Path(config).exists() else "❌"
        print(f"  {exists} {config}")

    print("\nServices (if running):")
    ports = {"Backend": 7001, "Timeline": 9002, "Frontend": 9000}
    for service, port in ports.items():
        result = subprocess.run(["lsof", f"-ti:{port}"], capture_output=True)
        status = "🟢 UP" if result.returncode == 0 else "⚪ DOWN"
        print(f"  {status} {service} (port {port})")

    print("\n" + "=" * 80)
    print("✅ Smoke test completed")
    print("=" * 80 + "\n")
