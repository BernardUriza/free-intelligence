"""
Catalog Service - El portal unificado de modelos locales.

Este servicio es el punto de entrada único para:
1. Listar modelos de todas las fuentes (GPT4All, HuggingFace, Ollama)
2. Buscar modelos por nombre/características
3. Descargar e instalar modelos
4. Registrar modelos instalados en el CRUD de LLM

Como el Palantír: una sola piedra que ve todos los reinos.
"""

import subprocess
import tempfile
from collections.abc import AsyncIterator

from backend.models.catalog_model import (
    CatalogModel,
    CatalogSearchParams,
    CatalogSource,
    ModelInstallProgress,
)
from backend.src.fi_model_catalog.services.sources.base import CatalogSourceBase
from backend.src.fi_model_catalog.services.sources.gpt4all_source import GPT4AllCatalogSource
from backend.src.fi_model_catalog.services.sources.huggingface_source import (
    HuggingFaceCatalogSource,
)
from backend.src.fi_model_catalog.services.sources.ollama_source import OllamaCatalogSource
from pathlib import Path


class CatalogService:
    """
    Servicio unificado de catálogo de modelos.

    Agrega múltiples fuentes y proporciona una interfaz única
    para descubrir, descargar e instalar modelos locales.
    """

    def __init__(self):
        self._sources: list[CatalogSourceBase] = [
            GPT4AllCatalogSource(),
            HuggingFaceCatalogSource(),
            OllamaCatalogSource(),
        ]
        self._ollama_source = OllamaCatalogSource()

    async def list_models(self, params: CatalogSearchParams | None = None) -> list[CatalogModel]:
        """
        Lista modelos de todas las fuentes disponibles.

        Args:
            params: Filtros opcionales (source, max_size_gb, etc.)

        Returns:
            Lista combinada de modelos de todas las fuentes
        """
        models = []

        # Determinar qué fuentes consultar
        sources_to_query = self._sources
        if params and params.source:
            sources_to_query = [s for s in self._sources if s.source_name == params.source.value]

        # Consultar cada fuente
        for source in sources_to_query:
            try:
                if await source.is_available():
                    source_models = await source.list_models(params)
                    models.extend(source_models)
            except Exception:
                # Si una fuente falla, continuar con las demás
                continue

        # Marcar modelos instalados
        models = await self._mark_installed_models(models)

        # Aplicar offset y limit si están especificados
        if params:
            offset = params.offset or 0
            limit = params.limit or len(models)
            models = models[offset : offset + limit]

        return models

    async def search_models(
        self, query: str, params: CatalogSearchParams | None = None
    ) -> list[CatalogModel]:
        """
        Busca modelos por nombre/descripción en todas las fuentes.

        Args:
            query: Término de búsqueda
            params: Filtros adicionales

        Returns:
            Lista de modelos que coinciden
        """
        models = []

        sources_to_query = self._sources
        if params and params.source:
            sources_to_query = [s for s in self._sources if s.source_name == params.source.value]

        for source in sources_to_query:
            try:
                if await source.is_available():
                    source_models = await source.search_models(query, params)
                    models.extend(source_models)
            except Exception:
                continue

        models = await self._mark_installed_models(models)

        return models

    async def get_model(self, model_id: str) -> CatalogModel | None:
        """Obtiene información de un modelo específico."""
        for source in self._sources:
            try:
                model = await source.get_model_info(model_id)
                if model:
                    return model
            except Exception:
                continue
        return None

    async def install_model(self, model: CatalogModel) -> dict | None:
        """
        Instala un modelo y lo registra en el CRUD de LLM.

        Args:
            model: Modelo a instalar

        Returns:
            Entrada creada en el CRUD de LLM, o None si falla
        """
        # Descargar el modelo
        async for progress in self.install_model_with_progress(model):
            if progress.status == "error":
                raise Exception(progress.error)
            if progress.status == "completed":
                break

        # Registrar en el CRUD
        return await self._register_in_llm_crud(model)

    async def install_model_with_progress(
        self, model: CatalogModel
    ) -> AsyncIterator[ModelInstallProgress]:
        """
        Instala un modelo con reporte de progreso.

        Args:
            model: Modelo a instalar

        Yields:
            Progreso de instalación
        """
        yield ModelInstallProgress(
            model_id=model.id,
            status="downloading",
            progress_percent=0,
            total_bytes=model.size_bytes,
            message=f"Starting installation of {model.name}",
        )

        try:
            # Determinar estrategia según la fuente
            if model.source == CatalogSource.OLLAMA:
                # Ya está instalado o usar ollama pull
                async for progress in self._ollama_source.download_model(
                    model.id,
                    "",  # Ollama maneja su propio destino
                ):
                    yield progress

            elif model.source == CatalogSource.GPT4ALL:
                # Descargar GGUF y registrar en Ollama
                async for progress in self._install_gpt4all_model(model):
                    yield progress

            elif model.source == CatalogSource.HUGGINGFACE:
                # Descargar GGUF de HF y registrar en Ollama
                async for progress in self._install_huggingface_model(model):
                    yield progress

            else:
                yield ModelInstallProgress(
                    model_id=model.id, status="error", error=f"Unknown source: {model.source}"
                )

        except Exception as e:
            yield ModelInstallProgress(model_id=model.id, status="error", error=str(e))

    async def _install_gpt4all_model(
        self, model: CatalogModel
    ) -> AsyncIterator[ModelInstallProgress]:
        """Instala un modelo de GPT4All descargando el GGUF y registrándolo en Ollama."""
        if not model.source_url:
            yield ModelInstallProgress(
                model_id=model.id, status="error", error="Model missing source_url"
            )
            return

        yield ModelInstallProgress(
            model_id=model.id,
            status="downloading",
            progress_percent=0,
            message=f"Downloading {model.filename} from GPT4All",
        )

        try:
            import httpx

            # Descargar GGUF a directorio temporal
            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = Path(tmpdir) / model.filename

                async with httpx.AsyncClient(follow_redirects=True) as client:
                    async with client.stream("GET", model.source_url, timeout=None) as response:
                        response.raise_for_status()
                        total = int(response.headers.get("content-length", 0))
                        downloaded = 0

                        with open(local_path, "wb") as f:
                            async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                                f.write(chunk)
                                downloaded += len(chunk)
                                percent = (downloaded / total * 100) if total > 0 else 0

                                yield ModelInstallProgress(
                                    model_id=model.id,
                                    status="downloading",
                                    progress_percent=min(percent, 90),
                                    downloaded_bytes=downloaded,
                                    total_bytes=total,
                                    message=f"Downloading: {downloaded // (1024 * 1024)}MB / {total // (1024 * 1024)}MB",
                                )

                yield ModelInstallProgress(
                    model_id=model.id,
                    status="downloading",
                    progress_percent=92,
                    message="Download complete, registering with Ollama...",
                )

                # Registrar en Ollama
                success = await self._register_in_ollama(model, str(local_path))

                if success:
                    yield ModelInstallProgress(
                        model_id=model.id,
                        status="completed",
                        progress_percent=100,
                        message=f"Successfully installed {model.name}",
                    )
                else:
                    yield ModelInstallProgress(
                        model_id=model.id,
                        status="error",
                        error="Failed to register model with Ollama",
                    )

        except Exception as e:
            yield ModelInstallProgress(model_id=model.id, status="error", error=str(e))

    async def _install_huggingface_model(
        self, model: CatalogModel
    ) -> AsyncIterator[ModelInstallProgress]:
        """Instala un modelo GGUF de HuggingFace."""
        if not model.repo_id:
            yield ModelInstallProgress(
                model_id=model.id, status="error", error="Model missing repo_id"
            )
            return

        yield ModelInstallProgress(
            model_id=model.id,
            status="downloading",
            progress_percent=5,
            message=f"Downloading from HuggingFace: {model.repo_id}",
        )

        try:
            from huggingface_hub import hf_hub_download

            # Descargar a directorio temporal
            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = hf_hub_download(
                    repo_id=model.repo_id,
                    filename=model.filename,
                    local_dir=tmpdir,
                )

                yield ModelInstallProgress(
                    model_id=model.id,
                    status="downloading",
                    progress_percent=70,
                    message="Download complete, registering with Ollama",
                )

                # Registrar en Ollama
                await self._register_in_ollama(model, local_path)

                yield ModelInstallProgress(
                    model_id=model.id,
                    status="completed",
                    progress_percent=100,
                    message=f"Successfully installed {model.name}",
                )

        except Exception as e:
            yield ModelInstallProgress(model_id=model.id, status="error", error=str(e))

    async def _register_in_ollama(self, model: CatalogModel, gguf_path: str) -> bool:
        """
        Registra un GGUF descargado en Ollama.

        Crea un Modelfile y ejecuta 'ollama create'.
        """
        # Generar nombre para Ollama
        ollama_name = self._generate_ollama_name(model)

        # Crear Modelfile temporal
        modelfile_content = f"FROM {gguf_path}\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".Modelfile", delete=False) as f:
            f.write(modelfile_content)
            modelfile_path = f.name

        try:
            # Ejecutar ollama create
            result = subprocess.run(
                ["ollama", "create", ollama_name, "-f", modelfile_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutos timeout
            )

            return result.returncode == 0

        finally:
            # Limpiar Modelfile temporal
            Path(modelfile_path).unlink(missing_ok=True)

    async def _register_in_llm_crud(self, model: CatalogModel) -> dict | None:
        """
        Registra el modelo instalado en el CRUD de LLM Models.

        Esto permite que el modelo aparezca en /admin/models
        y pueda ser usado por las Personas.
        """
        try:
            from backend.src.fi_llm.services.llm_model_service import LLMModelService

            service = LLMModelService()

            # Generar datos para el CRUD
            ollama_name = self._generate_ollama_name(model)
            crud_data = {
                "id": f"local-{model.id}",
                "label": model.name,
                "provider": "ollama",
                "model_name": ollama_name,
                "cost_tier": "low",  # Local = gratis
                "max_tokens": model.context_length or 4096,
                "context_window": model.context_length or 4096,
                "is_active": True,
                "size_bytes": model.size_bytes,  # RAM footprint for local models
            }

            return service.create_model(crud_data)

        except Exception:
            # Si falla el registro en CRUD, el modelo igual está instalado
            return None

    async def _mark_installed_models(self, models: list[CatalogModel]) -> list[CatalogModel]:
        """Marca los modelos que ya están instalados en Ollama."""
        try:
            installed_models = await self._ollama_source.list_models()

            # Normalizar nombres instalados (quitar puntuación para comparar)
            def normalize(name: str) -> str:
                import re

                return re.sub(r"[^a-z0-9]", "", name.lower())

            installed_normalized = {normalize(m.filename) for m in installed_models}

            for model in models:
                # Normalizar el nombre del modelo del catálogo
                model_name = model.filename.replace(".gguf", "").replace(".GGUF", "")
                model_normalized = normalize(model_name)

                # También verificar el nombre generado que usaríamos para Ollama
                ollama_name = self._generate_ollama_name(model)
                ollama_normalized = normalize(ollama_name)

                # Verificar si coincide con alguno instalado
                if (
                    model_normalized in installed_normalized
                    or ollama_normalized in installed_normalized
                    or any(
                        inst in model_normalized or model_normalized in inst
                        for inst in installed_normalized
                    )
                ):
                    model.is_installed = True

            return models

        except Exception:
            return models

    def _guess_ollama_name(self, model: CatalogModel) -> str:
        """Intenta adivinar el nombre de Ollama para un modelo."""
        name = model.name.lower()

        # Mapeos conocidos
        mappings = {
            "llama": "llama3",
            "mistral": "mistral",
            "phi": "phi3",
            "qwen": "qwen3",
            "gemma": "gemma",
        }

        for key, value in mappings.items():
            if key in name:
                # Intentar extraer tamaño
                import re

                match = re.search(r"(\d+)[bB]", name)
                if match:
                    return f"{value}:{match.group(1)}b"
                return value

        # Fallback: usar el filename limpio
        return model.filename.replace(".gguf", "").lower()

    def _generate_ollama_name(self, model: CatalogModel) -> str:
        """Genera un nombre válido para Ollama."""
        import re

        name = model.filename.replace(".gguf", "").replace(".GGUF", "")
        name = re.sub(r"[^a-zA-Z0-9_-]", "-", name)
        name = re.sub(r"-+", "-", name).strip("-").lower()
        return name[:50]  # Ollama tiene límite de longitud

    async def get_sources_status(self) -> dict[str, bool]:
        """Obtiene el estado de disponibilidad de cada fuente."""
        status = {}
        for source in self._sources:
            try:
                status[source.source_name] = await source.is_available()
            except Exception:
                status[source.source_name] = False
        return status
