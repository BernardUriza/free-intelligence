"""
HuggingFace Catalog Source - El océano infinito de modelos.

HuggingFace Hub contiene cientos de miles de modelos.
Filtramos por GGUFs para mantener compatibilidad con Ollama.
Como el mar de Belegaer: vasto, pero navegable con el mapa correcto.
"""

import re
from collections.abc import AsyncIterator

from backend.models.catalog_model import (
    CatalogModel,
    CatalogSearchParams,
    CatalogSource,
    ModelInstallProgress,
    QuantizationType,
)
from backend.core.infrastructure.model_catalog.services.sources.base import CatalogSourceBase


def _extract_quantization_from_filename(filename: str) -> QuantizationType:
    """Extrae el tipo de cuantización del nombre del archivo GGUF."""
    filename_upper = filename.upper()

    # Patrones de cuantización (orden: más específico primero)
    patterns = {
        "Q4_K_M": QuantizationType.Q4_K_M,
        "Q4-K-M": QuantizationType.Q4_K_M,
        "Q4KM": QuantizationType.Q4_K_M,
        "Q5_K_M": QuantizationType.Q5_K_M,
        "Q5-K-M": QuantizationType.Q5_K_M,
        "Q5KM": QuantizationType.Q5_K_M,
        "Q8_0": QuantizationType.Q8_0,
        "Q8-0": QuantizationType.Q8_0,
        "Q80": QuantizationType.Q8_0,
        "Q4_0": QuantizationType.Q4_0,
        "Q4-0": QuantizationType.Q4_0,
        "Q40": QuantizationType.Q4_0,
        "Q4K": QuantizationType.Q4_K_M,  # Common shorthand
        "Q5K": QuantizationType.Q5_K_M,
        "Q3K": QuantizationType.Q4_0,  # Approximate to Q4
        "Q2K": QuantizationType.Q4_0,  # Approximate to Q4
        "F16": QuantizationType.F16,
        "FP16": QuantizationType.F16,
    }

    for pattern, quant_type in patterns.items():
        if pattern in filename_upper:
            return quant_type

    return QuantizationType.UNKNOWN


def _generate_model_id(repo_id: str, filename: str) -> str:
    """Genera un ID único para un modelo de HuggingFace."""
    # Combinar repo_id y filename para unicidad
    base = f"{repo_id}_{filename}"
    base = base.replace("/", "-").replace(".gguf", "").replace(".GGUF", "")
    base = re.sub(r"[^a-zA-Z0-9_-]", "-", base)
    base = re.sub(r"-+", "-", base).strip("-").lower()
    return f"hf-{base}"


def _extract_model_name(repo_id: str, filename: str) -> str:
    """Genera un nombre legible para el modelo."""
    # Extraer nombre del repo (última parte)
    repo_name = repo_id.split("/")[-1] if "/" in repo_id else repo_id

    # Limpiar el nombre del archivo
    file_clean = filename.replace(".gguf", "").replace(".GGUF", "")

    # Si el filename ya contiene info útil, usarlo
    if repo_name.lower() in file_clean.lower():
        return file_clean.replace("-", " ").replace("_", " ").title()

    return f"{repo_name} ({file_clean})"


class HuggingFaceCatalogSource(CatalogSourceBase):
    """
    Fuente de catálogo para modelos GGUF de HuggingFace Hub.

    Filtra automáticamente por modelos con archivos GGUF
    y permite búsqueda por nombre, autor, y tags.
    """

    def __init__(self, default_limit: int = 50):
        self._default_limit = default_limit
        self._api = None

    @property
    def source_name(self) -> str:
        return "huggingface"

    def _get_api(self):
        """Lazy loading del API client."""
        if self._api is None:
            from huggingface_hub import HfApi

            self._api = HfApi()
        return self._api

    async def list_models(self, params: CatalogSearchParams | None = None) -> list[CatalogModel]:
        """Lista modelos GGUF populares de HuggingFace."""
        try:
            api = self._get_api()

            # Buscar repos con tag 'gguf'
            limit = params.limit if params else self._default_limit
            repos = api.list_models(
                filter="gguf",
                sort="downloads",
                direction=-1,
                limit=limit,
            )

            models = []
            for repo in repos:
                repo_models = await self._get_gguf_files_from_repo(repo.id, params)
                models.extend(repo_models)

            return models

        except ImportError:
            return []
        except Exception:
            return []

    async def search_models(
        self, query: str, params: CatalogSearchParams | None = None
    ) -> list[CatalogModel]:
        """Busca modelos GGUF por query."""
        try:
            api = self._get_api()

            # Buscar con query + filtro gguf
            limit = params.limit if params else self._default_limit
            repos = api.list_models(
                search=query,
                filter="gguf",
                sort="downloads",
                direction=-1,
                limit=limit,
            )

            models = []
            for repo in repos:
                repo_models = await self._get_gguf_files_from_repo(repo.id, params)
                # Filtrar por query en el repo_id
                for m in repo_models:
                    if query.lower() in (m.repo_id or "").lower():
                        models.append(m)

            return models

        except Exception:
            return []

    async def get_model_info(self, model_id: str) -> CatalogModel | None:
        """Obtiene información de un modelo específico por ID."""
        # El ID tiene formato: hf-{repo}-{filename}
        # Necesitamos parsear para obtener repo_id y filename
        all_models = await self.list_models()
        return next((m for m in all_models if m.id == model_id), None)

    async def download_model(
        self, model_id: str, destination: str
    ) -> AsyncIterator[ModelInstallProgress]:
        """Descarga un modelo GGUF de HuggingFace."""
        model = await self.get_model_info(model_id)
        if not model or not model.repo_id:
            yield ModelInstallProgress(
                model_id=model_id, status="error", error=f"Model {model_id} not found"
            )
            return

        yield ModelInstallProgress(
            model_id=model_id,
            status="downloading",
            progress_percent=0,
            total_bytes=model.size_bytes,
            message=f"Starting download of {model.name} from HuggingFace",
        )

        try:
            from huggingface_hub import hf_hub_download

            # Descargar el archivo específico
            local_path = hf_hub_download(
                repo_id=model.repo_id,
                filename=model.filename,
                local_dir=destination,
            )

            yield ModelInstallProgress(
                model_id=model_id,
                status="completed",
                progress_percent=100,
                downloaded_bytes=model.size_bytes,
                total_bytes=model.size_bytes,
                message=f"Downloaded to {local_path}",
            )

        except Exception as e:
            yield ModelInstallProgress(model_id=model_id, status="error", error=str(e))

    async def is_available(self) -> bool:
        """Verifica si HuggingFace Hub está accesible."""
        try:
            api = self._get_api()
            # Health check: listar un modelo
            list(api.list_models(limit=1))
            return True
        except Exception:
            return False

    async def _get_gguf_files_from_repo(
        self, repo_id: str, params: CatalogSearchParams | None = None
    ) -> list[CatalogModel]:
        """Obtiene todos los archivos GGUF de un repo."""
        try:
            api = self._get_api()
            # Solicitar metadata de archivos para obtener tamaños
            info = api.model_info(repo_id, files_metadata=True)

            models = []
            for sibling in info.siblings or []:
                filename = sibling.rfilename
                if not filename.lower().endswith(".gguf"):
                    continue

                # Obtener tamaño del archivo (priorizar lfs.size si existe)
                size_bytes = 0
                if hasattr(sibling, "lfs") and sibling.lfs:
                    size_bytes = (
                        sibling.lfs.get("size", 0)
                        if isinstance(sibling.lfs, dict)
                        else getattr(sibling.lfs, "size", 0)
                    )
                if not size_bytes and hasattr(sibling, "size"):
                    size_bytes = sibling.size or 0

                # Aplicar filtro de tamaño
                if params and params.max_size_gb:
                    size_gb = size_bytes / 1_000_000_000
                    if size_gb > params.max_size_gb:
                        continue

                model = CatalogModel(
                    id=_generate_model_id(repo_id, filename),
                    name=_extract_model_name(repo_id, filename),
                    filename=filename,
                    source=CatalogSource.HUGGINGFACE,
                    repo_id=repo_id,
                    source_url=f"https://huggingface.co/{repo_id}/resolve/main/{filename}",
                    size_bytes=size_bytes,
                    quantization=_extract_quantization_from_filename(filename),
                    tags=["huggingface", "gguf"],
                )
                models.append(model)

            return models

        except Exception:
            return []
