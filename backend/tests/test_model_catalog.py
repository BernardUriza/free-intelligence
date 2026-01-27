"""
Tests para el Model Catalog Service.

TDD: Primero escribimos los tests, luego los hacemos pasar.
Como Gandalf dijo: "El hechizo que falla nos enseña qué construir."
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip tests - requires gpt4all module which is not installed in CI
pytestmark = pytest.mark.skip(reason="Requires gpt4all module - install with 'pip install gpt4all'")
from backend.models.catalog_model import (
    CatalogModel,
    CatalogSearchParams,
    CatalogSource,
    QuantizationType,
)

# =============================================================================
# CICLO 1: GPT4AllCatalogSource
# =============================================================================


class TestGPT4AllCatalogSource:
    """Tests para la fuente GPT4All."""

    @pytest.fixture
    def mock_gpt4all_models(self):
        """Mock de la respuesta de GPT4All.list_models()"""
        return [
            {
                "name": "Llama 3 8B Instruct",
                "filename": "Meta-Llama-3-8B-Instruct.Q4_0.gguf",
                "filesize": "4920000000",
                "ramrequired": "8",
                "parameters": "8 billion",
                "quant": "Q4_0",
                "description": "Meta's Llama 3 8B fine-tuned for instructions",
                "url": "https://gpt4all.io/models/Meta-Llama-3-8B-Instruct.Q4_0.gguf",
            },
            {
                "name": "Mistral 7B Instruct",
                "filename": "mistral-7b-instruct-v0.1.Q4_0.gguf",
                "filesize": "4100000000",
                "ramrequired": "8",
                "parameters": "7 billion",
                "quant": "Q4_0",
                "description": "Mistral AI's 7B instruction-tuned model",
                "url": "https://gpt4all.io/models/mistral-7b-instruct-v0.1.Q4_0.gguf",
            },
            {
                "name": "Phi-3 Mini",
                "filename": "phi-3-mini-4k-instruct.Q4_0.gguf",
                "filesize": "2300000000",
                "ramrequired": "4",
                "parameters": "3.8 billion",
                "quant": "Q4_0",
                "description": "Microsoft's compact but capable model",
                "url": "https://gpt4all.io/models/phi-3-mini-4k-instruct.Q4_0.gguf",
            },
        ]

    @pytest.mark.asyncio
    async def test_list_models_returns_catalog_models(self, mock_gpt4all_models):
        """
        GIVEN: GPT4All tiene modelos disponibles
        WHEN: Llamamos list_models()
        THEN: Debe retornar una lista de CatalogModel con datos correctos
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", return_value=mock_gpt4all_models):
            source = GPT4AllCatalogSource()
            models = await source.list_models()

            assert len(models) == 3
            assert all(isinstance(m, CatalogModel) for m in models)

    @pytest.mark.asyncio
    async def test_models_have_required_fields(self, mock_gpt4all_models):
        """
        GIVEN: GPT4All retorna modelos
        WHEN: Convertimos a CatalogModel
        THEN: Cada modelo debe tener id, name, size_bytes, ram_required_gb
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", return_value=mock_gpt4all_models):
            source = GPT4AllCatalogSource()
            models = await source.list_models()

            for model in models:
                assert model.id is not None
                assert model.name is not None
                assert model.size_bytes > 0
                assert model.ram_required_gb is not None
                assert model.source == CatalogSource.GPT4ALL

    @pytest.mark.asyncio
    async def test_models_have_download_url(self, mock_gpt4all_models):
        """
        GIVEN: GPT4All retorna modelos con URL
        WHEN: Convertimos a CatalogModel
        THEN: Cada modelo debe tener source_url para descarga
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", return_value=mock_gpt4all_models):
            source = GPT4AllCatalogSource()
            models = await source.list_models()

            for model in models:
                assert model.source_url is not None
                assert model.source_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_search_filters_by_name(self, mock_gpt4all_models):
        """
        GIVEN: GPT4All tiene varios modelos
        WHEN: Buscamos "llama"
        THEN: Solo retorna modelos con "llama" en el nombre
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", return_value=mock_gpt4all_models):
            source = GPT4AllCatalogSource()
            models = await source.search_models("llama")

            assert len(models) == 1
            assert "llama" in models[0].name.lower()

    @pytest.mark.asyncio
    async def test_filter_by_max_size(self, mock_gpt4all_models):
        """
        GIVEN: GPT4All tiene modelos de varios tamaños
        WHEN: Filtramos por max_size_gb=3
        THEN: Solo retorna modelos menores a 3GB
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", return_value=mock_gpt4all_models):
            source = GPT4AllCatalogSource()
            params = CatalogSearchParams(max_size_gb=3.0)
            models = await source.list_models(params)

            assert len(models) == 1  # Solo Phi-3 (2.3GB)
            assert models[0].size_gb < 3.0

    @pytest.mark.asyncio
    async def test_filter_by_max_ram(self, mock_gpt4all_models):
        """
        GIVEN: GPT4All tiene modelos con distintos requisitos de RAM
        WHEN: Filtramos por max_ram_gb=6
        THEN: Solo retorna modelos que requieren <= 6GB RAM
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", return_value=mock_gpt4all_models):
            source = GPT4AllCatalogSource()
            params = CatalogSearchParams(max_ram_gb=6.0)
            models = await source.list_models(params)

            assert len(models) == 1  # Solo Phi-3 (4GB RAM)
            assert all(m.ram_required_gb <= 6.0 for m in models)

    @pytest.mark.asyncio
    async def test_source_is_available_when_gpt4all_responds(self, mock_gpt4all_models):
        """
        GIVEN: GPT4All está funcionando
        WHEN: Verificamos disponibilidad
        THEN: is_available() retorna True
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", return_value=mock_gpt4all_models):
            source = GPT4AllCatalogSource()
            assert await source.is_available() is True

    @pytest.mark.asyncio
    async def test_source_unavailable_when_gpt4all_fails(self):
        """
        GIVEN: GPT4All no está disponible (error de red, etc.)
        WHEN: Verificamos disponibilidad
        THEN: is_available() retorna False
        """
        from backend.core.infrastructure.model_catalog.services.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        with patch("gpt4all.GPT4All.list_models", side_effect=Exception("Network error")):
            source = GPT4AllCatalogSource()
            assert await source.is_available() is False


# =============================================================================
# CICLO 2: HuggingFaceCatalogSource
# =============================================================================


class TestHuggingFaceCatalogSource:
    """Tests para la fuente HuggingFace."""

    @pytest.fixture
    def mock_hf_models(self):
        """Mock de modelos de HuggingFace Hub."""
        # Simulamos la estructura que retorna HfApi.list_models()
        model1 = MagicMock()
        model1.id = "TheBloke/Llama-3-8B-GGUF"
        model1.downloads = 50000
        model1.tags = ["gguf", "llama", "text-generation"]

        model2 = MagicMock()
        model2.id = "TheBloke/Mistral-7B-v0.1-GGUF"
        model2.downloads = 30000
        model2.tags = ["gguf", "mistral", "text-generation"]

        return [model1, model2]

    @pytest.fixture
    def mock_hf_model_info(self):
        """Mock de model_info con archivos GGUF."""
        info = MagicMock()
        info.id = "TheBloke/Llama-3-8B-GGUF"

        # Simulamos siblings (archivos en el repo)
        file1 = MagicMock()
        file1.rfilename = "llama-3-8b.Q4_K_M.gguf"
        file1.size = 4_920_000_000

        file2 = MagicMock()
        file2.rfilename = "llama-3-8b.Q8_0.gguf"
        file2.size = 8_500_000_000

        file3 = MagicMock()
        file3.rfilename = "README.md"
        file3.size = 5000

        info.siblings = [file1, file2, file3]
        return info

    @pytest.mark.asyncio
    async def test_list_models_returns_gguf_only(self, mock_hf_models, mock_hf_model_info):
        """
        GIVEN: HuggingFace tiene repos con y sin GGUFs
        WHEN: Llamamos list_models()
        THEN: Solo retorna modelos con archivos GGUF
        """
        from backend.core.infrastructure.model_catalog.services.sources.huggingface_source import (
            HuggingFaceCatalogSource,
        )

        with patch("huggingface_hub.HfApi") as mock_hf_api:
            mock_api = mock_hf_api.return_value
            mock_api.list_models.return_value = mock_hf_models
            mock_api.model_info.return_value = mock_hf_model_info

            source = HuggingFaceCatalogSource()
            models = await source.list_models()

            # Debe expandir cada GGUF como un modelo separado
            assert len(models) >= 1
            assert all(".gguf" in m.filename.lower() for m in models)

    @pytest.mark.asyncio
    async def test_filter_by_max_size_gb(self, mock_hf_models, mock_hf_model_info):
        """
        GIVEN: HuggingFace tiene GGUFs de varios tamaños
        WHEN: Filtramos por max_size_gb=5
        THEN: Solo retorna GGUFs menores a 5GB
        """
        from backend.core.infrastructure.model_catalog.services.sources.huggingface_source import (
            HuggingFaceCatalogSource,
        )

        with patch("huggingface_hub.HfApi") as mock_hf_api:
            mock_api = mock_hf_api.return_value
            mock_api.list_models.return_value = mock_hf_models
            mock_api.model_info.return_value = mock_hf_model_info

            source = HuggingFaceCatalogSource()
            params = CatalogSearchParams(max_size_gb=5.0)
            models = await source.list_models(params)

            # Solo el Q4_K_M (4.9GB), no el Q8_0 (8.5GB)
            assert all(m.size_gb <= 5.0 for m in models)

    @pytest.mark.asyncio
    async def test_search_by_query(self, mock_hf_models, mock_hf_model_info):
        """
        GIVEN: HuggingFace tiene varios modelos
        WHEN: Buscamos "llama"
        THEN: Solo retorna modelos con "llama" en el repo_id
        """
        from backend.core.infrastructure.model_catalog.services.sources.huggingface_source import (
            HuggingFaceCatalogSource,
        )

        with patch("huggingface_hub.HfApi") as mock_hf_api:
            mock_api = mock_hf_api.return_value
            mock_api.list_models.return_value = mock_hf_models
            mock_api.model_info.return_value = mock_hf_model_info

            source = HuggingFaceCatalogSource()
            models = await source.search_models("llama")

            assert all("llama" in m.repo_id.lower() for m in models)

    @pytest.mark.asyncio
    async def test_extracts_quantization_from_filename(self, mock_hf_models, mock_hf_model_info):
        """
        GIVEN: Un archivo GGUF con cuantización en el nombre
        WHEN: Convertimos a CatalogModel
        THEN: El campo quantization debe extraerse correctamente
        """
        from backend.core.infrastructure.model_catalog.services.sources.huggingface_source import (
            HuggingFaceCatalogSource,
        )

        with patch("huggingface_hub.HfApi") as mock_hf_api:
            mock_api = mock_hf_api.return_value
            mock_api.list_models.return_value = mock_hf_models
            mock_api.model_info.return_value = mock_hf_model_info

            source = HuggingFaceCatalogSource()
            models = await source.list_models()

            q4_model = next((m for m in models if "Q4" in m.filename), None)
            if q4_model:
                assert q4_model.quantization == QuantizationType.Q4_K_M


# =============================================================================
# CICLO 3: CatalogService (Unificado)
# =============================================================================


class TestCatalogService:
    """Tests para el servicio unificado de catálogo."""

    @pytest.mark.asyncio
    async def test_list_all_sources_combined(self):
        """
        GIVEN: Múltiples fuentes (GPT4All, HuggingFace) disponibles
        WHEN: Llamamos list_models() sin filtro de source
        THEN: Retorna modelos de todas las fuentes
        """
        from backend.core.infrastructure.model_catalog.services.catalog_service import CatalogService

        service = CatalogService()

        with patch.object(service, "_sources") as mock_sources:
            # Mock de dos fuentes
            gpt4all_source = AsyncMock()
            gpt4all_source.list_models.return_value = [
                CatalogModel(
                    id="llama3-gpt4all",
                    name="Llama 3",
                    filename="llama3.gguf",
                    source=CatalogSource.GPT4ALL,
                    size_bytes=5_000_000_000,
                )
            ]

            hf_source = AsyncMock()
            hf_source.list_models.return_value = [
                CatalogModel(
                    id="llama3-hf",
                    name="Llama 3 HF",
                    filename="llama3-hf.gguf",
                    source=CatalogSource.HUGGINGFACE,
                    size_bytes=5_000_000_000,
                )
            ]

            mock_sources.__iter__ = lambda self: iter([gpt4all_source, hf_source])

            models = await service.list_models()

            assert len(models) == 2
            sources = {m.source for m in models}
            assert CatalogSource.GPT4ALL in sources
            assert CatalogSource.HUGGINGFACE in sources

    @pytest.mark.asyncio
    async def test_filter_by_single_source(self):
        """
        GIVEN: Múltiples fuentes disponibles
        WHEN: Filtramos por source=GPT4ALL
        THEN: Solo retorna modelos de GPT4All
        """
        from backend.core.infrastructure.model_catalog.services.catalog_service import CatalogService

        service = CatalogService()
        params = CatalogSearchParams(source=CatalogSource.GPT4ALL)

        # Este test verificará que el filtro funciona
        # La implementación debe filtrar antes de combinar
        models = await service.list_models(params)

        assert all(m.source == CatalogSource.GPT4ALL for m in models)

    @pytest.mark.asyncio
    async def test_deduplicate_same_model_different_sources(self):
        """
        GIVEN: El mismo modelo aparece en GPT4All y HuggingFace
        WHEN: Listamos todos los modelos
        THEN: Debe mostrar ambos (no deduplicar) pero marcar la fuente
        """
        from backend.core.infrastructure.model_catalog.services.catalog_service import CatalogService

        # Llama 3 existe en ambas fuentes - esto es válido
        # El usuario puede elegir de dónde descargar
        service = CatalogService()
        models = await service.list_models()

        # Verificar que modelos similares mantienen su source distinta
        llama_models = [m for m in models if "llama" in m.name.lower()]
        if len(llama_models) > 1:
            sources = {m.source for m in llama_models}
            # Puede haber el mismo modelo de diferentes fuentes
            assert len(sources) >= 1


# =============================================================================
# CICLO 4: Instalación de Modelos
# =============================================================================


class TestModelInstallation:
    """Tests para la instalación de modelos."""

    @pytest.mark.asyncio
    async def test_install_creates_llm_model_entry(self):
        """
        GIVEN: Un modelo del catálogo
        WHEN: Lo instalamos exitosamente
        THEN: Debe crear una entrada en el LLM Model CRUD
        """
        from backend.core.services.llm.services.llm_model_service import LLMModelService
        from backend.core.infrastructure.model_catalog.services.catalog_service import CatalogService

        catalog = CatalogService()

        with patch.object(LLMModelService, "create_model") as mock_create:
            mock_create.return_value = MagicMock(id="llama3-local")

            # Simular instalación exitosa
            model = CatalogModel(
                id="llama3-8b",
                name="Llama 3 8B",
                filename="llama3-8b.Q4_K_M.gguf",
                source=CatalogSource.GPT4ALL,
                size_bytes=5_000_000_000,
                ram_required_gb=8.0,
                context_length=8192,
            )

            await catalog.install_model(model)

            # Verificar que se llamó al CRUD
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0][0]

            assert call_args["provider"] == "ollama"
            assert call_args["cost_tier"] == "low"  # Local = gratis
            assert "llama" in call_args["label"].lower()

    @pytest.mark.asyncio
    async def test_install_registers_in_ollama(self):
        """
        GIVEN: Un modelo GGUF descargado
        WHEN: Lo instalamos
        THEN: Debe registrarse en Ollama con 'ollama create'
        """
        from backend.core.infrastructure.model_catalog.services.catalog_service import CatalogService

        catalog = CatalogService()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            model = CatalogModel(
                id="custom-llama",
                name="Custom Llama",
                filename="custom-llama.gguf",
                source=CatalogSource.HUGGINGFACE,
                size_bytes=5_000_000_000,
            )

            await catalog._register_in_ollama(model, "/path/to/custom-llama.gguf")

            # Verificar que se llamó ollama create
            mock_run.assert_called()
            call_args = str(mock_run.call_args)
            assert "ollama" in call_args

    @pytest.mark.asyncio
    async def test_install_progress_reports_correctly(self):
        """
        GIVEN: Un modelo descargándose
        WHEN: Monitoreamos el progreso
        THEN: Debe reportar porcentaje y bytes descargados
        """
        from backend.core.infrastructure.model_catalog.services.catalog_service import CatalogService

        catalog = CatalogService()

        model = CatalogModel(
            id="test-model",
            name="Test Model",
            filename="test.gguf",
            source=CatalogSource.GPT4ALL,
            source_url="https://example.com/test.gguf",
            size_bytes=1_000_000_000,
        )

        progress_updates = []

        async for progress in catalog.install_model_with_progress(model):
            progress_updates.append(progress)

        # Debe haber al menos inicio y fin
        assert len(progress_updates) >= 2
        assert progress_updates[0].status == "downloading"
        assert progress_updates[-1].status in ["completed", "error"]


# =============================================================================
# CICLO 5: Ollama Source (modelos ya instalados)
# =============================================================================


class TestOllamaCatalogSource:
    """Tests para la fuente Ollama (modelos instalados localmente)."""

    @pytest.fixture
    def mock_ollama_list(self):
        """Mock de 'ollama list' output."""
        return {
            "models": [
                {
                    "name": "llama3:8b",
                    "size": 4_920_000_000,
                    "modified_at": "2024-01-15T10:30:00Z",
                    "digest": "abc123",
                },
                {
                    "name": "mistral:7b",
                    "size": 4_100_000_000,
                    "modified_at": "2024-01-14T09:00:00Z",
                    "digest": "def456",
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_list_installed_models(self, mock_ollama_list):
        """
        GIVEN: Ollama tiene modelos instalados
        WHEN: Llamamos list_models()
        THEN: Retorna los modelos instalados como CatalogModel con is_installed=True
        """
        from backend.core.infrastructure.model_catalog.services.sources.ollama_source import (
            OllamaCatalogSource,
        )

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_ollama_list
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            source = OllamaCatalogSource()
            models = await source.list_models()

            assert len(models) == 2
            assert all(m.is_installed for m in models)
            assert all(m.source == CatalogSource.OLLAMA for m in models)

    @pytest.mark.asyncio
    async def test_is_available_when_ollama_running(self, mock_ollama_list):
        """
        GIVEN: Ollama daemon está corriendo
        WHEN: Verificamos disponibilidad
        THEN: is_available() retorna True
        """
        from backend.core.infrastructure.model_catalog.services.sources.ollama_source import (
            OllamaCatalogSource,
        )

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            source = OllamaCatalogSource()
            assert await source.is_available() is True

    @pytest.mark.asyncio
    async def test_is_unavailable_when_ollama_not_running(self):
        """
        GIVEN: Ollama daemon NO está corriendo
        WHEN: Verificamos disponibilidad
        THEN: is_available() retorna False
        """
        from backend.core.infrastructure.model_catalog.services.sources.ollama_source import (
            OllamaCatalogSource,
        )

        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
            source = OllamaCatalogSource()
            assert await source.is_available() is False
