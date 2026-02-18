"""Unit tests for CatalogModel and related Pydantic models.

Tests for model catalog functionality including search, install, and progress tracking.
"""

from __future__ import annotations

from datetime import datetime

import pytest

# ==============================================================================
# CATALOG SOURCE ENUM TESTS
# ==============================================================================


class TestCatalogSource:
    """Tests for CatalogSource enum."""

    def test_catalog_source_values(self) -> None:
        """Test CatalogSource enum values."""
        from backend.models.catalog_model import CatalogSource

        assert CatalogSource.GPT4ALL.value == "gpt4all"
        assert CatalogSource.HUGGINGFACE.value == "huggingface"
        assert CatalogSource.OLLAMA.value == "ollama"

    def test_catalog_source_from_string(self) -> None:
        """Test creating CatalogSource from string."""
        from backend.models.catalog_model import CatalogSource

        assert CatalogSource("gpt4all") == CatalogSource.GPT4ALL
        assert CatalogSource("huggingface") == CatalogSource.HUGGINGFACE
        assert CatalogSource("ollama") == CatalogSource.OLLAMA


# ==============================================================================
# QUANTIZATION TYPE ENUM TESTS
# ==============================================================================


class TestQuantizationType:
    """Tests for QuantizationType enum."""

    def test_quantization_type_values(self) -> None:
        """Test QuantizationType enum values."""
        from backend.models.catalog_model import QuantizationType

        assert QuantizationType.Q4_0.value == "Q4_0"
        assert QuantizationType.Q4_K_M.value == "Q4_K_M"
        assert QuantizationType.Q5_K_M.value == "Q5_K_M"
        assert QuantizationType.Q8_0.value == "Q8_0"
        assert QuantizationType.F16.value == "F16"
        assert QuantizationType.UNKNOWN.value == "unknown"


# ==============================================================================
# CATALOG MODEL TESTS
# ==============================================================================


class TestCatalogModel:
    """Tests for CatalogModel Pydantic model."""

    def test_catalog_model_minimal(self) -> None:
        """Test CatalogModel with minimal required fields."""
        from backend.models.catalog_model import CatalogModel, CatalogSource

        model = CatalogModel(
            id="llama3-8b",
            name="Llama 3 8B",
            filename="llama-3-8b.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=4_500_000_000,
        )

        assert model.id == "llama3-8b"
        assert model.name == "Llama 3 8B"
        assert model.filename == "llama-3-8b.gguf"
        assert model.source == CatalogSource.OLLAMA
        assert model.size_bytes == 4_500_000_000
        assert model.is_installed is False
        assert model.tags == []

    def test_catalog_model_full(self) -> None:
        """Test CatalogModel with all fields."""
        from backend.models.catalog_model import (
            CatalogModel,
            CatalogSource,
            QuantizationType,
        )
        from backend.utils.common.types import utc_now

        now = utc_now()
        model = CatalogModel(
            id="mistral-7b-instruct-q4",
            name="Mistral 7B Instruct",
            filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            source=CatalogSource.HUGGINGFACE,
            source_url="https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            repo_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            size_bytes=4_370_000_000,
            ram_required_gb=8.0,
            parameters="7B",
            quantization=QuantizationType.Q4_K_M,
            context_length=32768,
            description="Mistral 7B Instruct model with Q4_K_M quantization",
            license="apache-2.0",
            tags=["instruct", "chat", "coding"],
            is_installed=True,
            installed_at=now,
        )

        assert model.id == "mistral-7b-instruct-q4"
        assert model.source_url is not None
        assert model.repo_id == "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
        assert model.ram_required_gb == 8.0
        assert model.quantization == QuantizationType.Q4_K_M
        assert model.context_length == 32768
        assert model.is_installed is True
        assert model.installed_at == now
        assert len(model.tags) == 3

    def test_catalog_model_size_gb_property(self) -> None:
        """Test size_gb calculated property."""
        from backend.models.catalog_model import CatalogModel, CatalogSource

        # 4.5 GB model
        model = CatalogModel(
            id="test",
            name="Test",
            filename="test.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=4_500_000_000,
        )
        assert model.size_gb == 4.5

        # 10.25 GB model
        model2 = CatalogModel(
            id="test2",
            name="Test 2",
            filename="test2.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=10_250_000_000,
        )
        assert model2.size_gb == 10.25

    def test_catalog_model_size_category_properties(self) -> None:
        """Test is_small, is_medium, is_large properties."""
        from backend.models.catalog_model import CatalogModel, CatalogSource

        # Small model (< 8GB)
        small_model = CatalogModel(
            id="small",
            name="Small Model",
            filename="small.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=4_000_000_000,  # 4 GB
        )
        assert small_model.is_small is True
        assert small_model.is_medium is False
        assert small_model.is_large is False

        # Medium model (8-20 GB)
        medium_model = CatalogModel(
            id="medium",
            name="Medium Model",
            filename="medium.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=12_000_000_000,  # 12 GB
        )
        assert medium_model.is_small is False
        assert medium_model.is_medium is True
        assert medium_model.is_large is False

        # Large model (> 20GB)
        large_model = CatalogModel(
            id="large",
            name="Large Model",
            filename="large.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=35_000_000_000,  # 35 GB
        )
        assert large_model.is_small is False
        assert large_model.is_medium is False
        assert large_model.is_large is True

    def test_catalog_model_boundary_sizes(self) -> None:
        """Test size category boundaries."""
        from backend.models.catalog_model import CatalogModel, CatalogSource

        # Exactly 8GB - should be medium, not small
        model_8gb = CatalogModel(
            id="boundary8",
            name="8GB Model",
            filename="8gb.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=8_000_000_000,
        )
        assert model_8gb.is_small is False
        assert model_8gb.is_medium is True

        # Exactly 20GB - should be large, not medium
        model_20gb = CatalogModel(
            id="boundary20",
            name="20GB Model",
            filename="20gb.gguf",
            source=CatalogSource.OLLAMA,
            size_bytes=20_000_000_000,
        )
        assert model_20gb.is_medium is False
        assert model_20gb.is_large is True


# ==============================================================================
# CATALOG SEARCH PARAMS TESTS
# ==============================================================================


class TestCatalogSearchParams:
    """Tests for CatalogSearchParams model."""

    def test_search_params_defaults(self) -> None:
        """Test CatalogSearchParams default values."""
        from backend.models.catalog_model import CatalogSearchParams

        params = CatalogSearchParams()

        assert params.query is None
        assert params.source is None
        assert params.max_size_gb is None
        assert params.max_ram_gb is None
        assert params.tags is None
        assert params.installed_only is False
        assert params.limit == 50
        assert params.offset == 0

    def test_search_params_with_filters(self) -> None:
        """Test CatalogSearchParams with filters."""
        from backend.models.catalog_model import CatalogSearchParams, CatalogSource

        params = CatalogSearchParams(
            query="llama",
            source=CatalogSource.OLLAMA,
            max_size_gb=8.0,
            max_ram_gb=16.0,
            tags=["instruct", "chat"],
            installed_only=True,
            limit=20,
            offset=10,
        )

        assert params.query == "llama"
        assert params.source == CatalogSource.OLLAMA
        assert params.max_size_gb == 8.0
        assert params.max_ram_gb == 16.0
        assert params.tags == ["instruct", "chat"]
        assert params.installed_only is True
        assert params.limit == 20
        assert params.offset == 10

    def test_search_params_limit_validation(self) -> None:
        """Test limit field validation."""
        from backend.models.catalog_model import CatalogSearchParams
        from pydantic import ValidationError

        # Valid limits
        params = CatalogSearchParams(limit=1)
        assert params.limit == 1

        params = CatalogSearchParams(limit=200)
        assert params.limit == 200

        # Invalid limits
        with pytest.raises(ValidationError):
            CatalogSearchParams(limit=0)  # Below minimum

        with pytest.raises(ValidationError):
            CatalogSearchParams(limit=201)  # Above maximum

    def test_search_params_offset_validation(self) -> None:
        """Test offset field validation."""
        from backend.models.catalog_model import CatalogSearchParams
        from pydantic import ValidationError

        # Valid offset
        params = CatalogSearchParams(offset=0)
        assert params.offset == 0

        params = CatalogSearchParams(offset=1000)
        assert params.offset == 1000

        # Invalid offset
        with pytest.raises(ValidationError):
            CatalogSearchParams(offset=-1)


# ==============================================================================
# MODEL INSTALL REQUEST TESTS
# ==============================================================================


class TestModelInstallRequest:
    """Tests for ModelInstallRequest model."""

    def test_install_request_minimal(self) -> None:
        """Test ModelInstallRequest with minimal fields."""
        from backend.models.catalog_model import CatalogSource, ModelInstallRequest

        request = ModelInstallRequest(
            model_id="llama3-8b",
            source=CatalogSource.OLLAMA,
        )

        assert request.model_id == "llama3-8b"
        assert request.source == CatalogSource.OLLAMA
        assert request.filename is None

    def test_install_request_with_filename(self) -> None:
        """Test ModelInstallRequest with filename for HuggingFace."""
        from backend.models.catalog_model import CatalogSource, ModelInstallRequest

        request = ModelInstallRequest(
            model_id="mistral-7b",
            source=CatalogSource.HUGGINGFACE,
            filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        )

        assert request.model_id == "mistral-7b"
        assert request.source == CatalogSource.HUGGINGFACE
        assert request.filename == "mistral-7b-instruct-v0.2.Q4_K_M.gguf"


# ==============================================================================
# MODEL INSTALL PROGRESS TESTS
# ==============================================================================


class TestModelInstallProgress:
    """Tests for ModelInstallProgress model."""

    def test_install_progress_downloading(self) -> None:
        """Test install progress during download."""
        from backend.models.catalog_model import ModelInstallProgress

        progress = ModelInstallProgress(
            model_id="llama3-8b",
            status="downloading",
            progress_percent=45.5,
            downloaded_bytes=2_000_000_000,
            total_bytes=4_400_000_000,
            message="Downloading from HuggingFace...",
        )

        assert progress.model_id == "llama3-8b"
        assert progress.status == "downloading"
        assert progress.progress_percent == 45.5
        assert progress.downloaded_bytes == 2_000_000_000
        assert progress.total_bytes == 4_400_000_000
        assert progress.message == "Downloading from HuggingFace..."
        assert progress.error is None

    def test_install_progress_completed(self) -> None:
        """Test install progress when completed."""
        from backend.models.catalog_model import ModelInstallProgress

        progress = ModelInstallProgress(
            model_id="llama3-8b",
            status="completed",
            progress_percent=100.0,
            downloaded_bytes=4_400_000_000,
            total_bytes=4_400_000_000,
            message="Installation complete!",
        )

        assert progress.status == "completed"
        assert progress.progress_percent == 100.0

    def test_install_progress_error(self) -> None:
        """Test install progress with error."""
        from backend.models.catalog_model import ModelInstallProgress

        progress = ModelInstallProgress(
            model_id="llama3-8b",
            status="error",
            progress_percent=30.0,
            error="Network timeout while downloading",
        )

        assert progress.status == "error"
        assert progress.error == "Network timeout while downloading"

    def test_install_progress_defaults(self) -> None:
        """Test install progress default values."""
        from backend.models.catalog_model import ModelInstallProgress

        progress = ModelInstallProgress(
            model_id="test-model",
            status="downloading",
        )

        assert progress.progress_percent == 0
        assert progress.downloaded_bytes == 0
        assert progress.total_bytes == 0
        assert progress.message is None
        assert progress.error is None

    def test_install_progress_percent_bounds(self) -> None:
        """Test progress_percent validation bounds."""
        from backend.models.catalog_model import ModelInstallProgress
        from pydantic import ValidationError

        # Valid bounds
        ModelInstallProgress(model_id="test", status="downloading", progress_percent=0)
        ModelInstallProgress(model_id="test", status="downloading", progress_percent=100)
        ModelInstallProgress(model_id="test", status="downloading", progress_percent=50.5)

        # Invalid bounds
        with pytest.raises(ValidationError):
            ModelInstallProgress(model_id="test", status="downloading", progress_percent=-1)

        with pytest.raises(ValidationError):
            ModelInstallProgress(model_id="test", status="downloading", progress_percent=101)
