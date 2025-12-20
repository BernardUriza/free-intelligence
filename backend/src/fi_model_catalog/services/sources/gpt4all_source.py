"""
GPT4All Catalog Source - La fuente de modelos curados.

GPT4All mantiene una lista cuidadosamente seleccionada de modelos
que han sido probados y optimizados para ejecución local.
Como un catálogo de biblioteca élfica: pocos, pero de calidad.
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
from backend.src.fi_model_catalog.services.sources.base import CatalogSourceBase


def _extract_quantization(filename: str) -> QuantizationType:
    """Extrae el tipo de cuantización del nombre del archivo."""
    filename_upper = filename.upper()
    if "Q4_K_M" in filename_upper:
        return QuantizationType.Q4_K_M
    if "Q5_K_M" in filename_upper:
        return QuantizationType.Q5_K_M
    if "Q8_0" in filename_upper:
        return QuantizationType.Q8_0
    if "Q4_0" in filename_upper:
        return QuantizationType.Q4_0
    if "F16" in filename_upper:
        return QuantizationType.F16
    return QuantizationType.UNKNOWN


def _extract_parameters(params_str: str | None) -> str | None:
    """Normaliza el string de parámetros (ej: '8 billion' -> '8B')."""
    if not params_str:
        return None
    # Buscar número + billion/million
    match = re.search(r"(\d+\.?\d*)\s*(billion|million|B|M)", params_str, re.IGNORECASE)
    if match:
        num = match.group(1)
        unit = match.group(2).lower()
        if unit in ("billion", "b"):
            return f"{num}B"
        if unit in ("million", "m"):
            return f"{num}M"
    return params_str


def _generate_model_id(filename: str) -> str:
    """Genera un ID único basado en el filename."""
    # Remover extensión y limpiar
    model_id = filename.replace(".gguf", "").replace(".GGUF", "")
    model_id = re.sub(r"[^a-zA-Z0-9_-]", "-", model_id)
    model_id = re.sub(r"-+", "-", model_id).strip("-").lower()
    return f"gpt4all-{model_id}"


class GPT4AllCatalogSource(CatalogSourceBase):
    """
    Fuente de catálogo para modelos de GPT4All.

    GPT4All mantiene ~50 modelos curados con información
    detallada sobre requisitos de RAM y hardware.
    """

    @property
    def source_name(self) -> str:
        return "gpt4all"

    async def list_models(self, params: CatalogSearchParams | None = None) -> list[CatalogModel]:
        """Lista todos los modelos disponibles en GPT4All."""
        try:
            from gpt4all import GPT4All

            raw_models = GPT4All.list_models()
        except ImportError:
            # Si gpt4all no está instalado, retornar lista vacía
            return []
        except Exception:
            return []

        models = []
        for raw in raw_models:
            model = self._convert_to_catalog_model(raw)
            if model and self._matches_filters(model, params):
                models.append(model)

        return models

    async def search_models(
        self, query: str, params: CatalogSearchParams | None = None
    ) -> list[CatalogModel]:
        """Busca modelos por nombre/descripción."""
        all_models = await self.list_models(params)
        query_lower = query.lower()

        return [
            m
            for m in all_models
            if query_lower in m.name.lower()
            or query_lower in (m.description or "").lower()
            or query_lower in m.filename.lower()
        ]

    async def get_model_info(self, model_id: str) -> CatalogModel | None:
        """Obtiene información de un modelo específico."""
        all_models = await self.list_models()
        return next((m for m in all_models if m.id == model_id), None)

    async def download_model(
        self, model_id: str, destination: str
    ) -> AsyncIterator[ModelInstallProgress]:
        """
        Descarga un modelo de GPT4All.

        GPT4All maneja la descarga internamente, pero podemos
        reportar progreso básico.
        """
        model = await self.get_model_info(model_id)
        if not model:
            yield ModelInstallProgress(
                model_id=model_id, status="error", error=f"Model {model_id} not found"
            )
            return

        yield ModelInstallProgress(
            model_id=model_id,
            status="downloading",
            progress_percent=0,
            total_bytes=model.size_bytes,
            message=f"Starting download of {model.name}",
        )

        try:
            from gpt4all import GPT4All

            # GPT4All descarga automáticamente al instanciar
            # El modelo se guarda en ~/.cache/gpt4all/
            _ = GPT4All(model.filename, model_path=destination, allow_download=True)

            yield ModelInstallProgress(
                model_id=model_id,
                status="completed",
                progress_percent=100,
                downloaded_bytes=model.size_bytes,
                total_bytes=model.size_bytes,
                message=f"Successfully downloaded {model.name}",
            )

        except Exception as e:
            yield ModelInstallProgress(model_id=model_id, status="error", error=str(e))

    async def is_available(self) -> bool:
        """Verifica si GPT4All está disponible."""
        try:
            from gpt4all import GPT4All

            # Intentar listar modelos como health check
            GPT4All.list_models()
            return True
        except Exception:
            return False

    def _convert_to_catalog_model(self, raw: dict) -> CatalogModel | None:
        """Convierte un modelo raw de GPT4All a CatalogModel."""
        try:
            filename = raw.get("filename", "")
            name = raw.get("name", filename)
            size_str = raw.get("filesize", "0")
            ram_str = raw.get("ramrequired", "0")

            # Parsear tamaño (puede ser string o int)
            size_bytes = int(size_str) if size_str else 0

            # Parsear RAM requerida
            ram_gb = float(ram_str) if ram_str else None

            return CatalogModel(
                id=_generate_model_id(filename),
                name=name,
                filename=filename,
                source=CatalogSource.GPT4ALL,
                source_url=raw.get("url"),
                size_bytes=size_bytes,
                ram_required_gb=ram_gb,
                parameters=_extract_parameters(raw.get("parameters")),
                quantization=_extract_quantization(filename),
                description=raw.get("description"),
                tags=["gpt4all", "curated"],
            )
        except Exception:
            return None

    def _matches_filters(self, model: CatalogModel, params: CatalogSearchParams | None) -> bool:
        """Verifica si un modelo cumple los filtros."""
        if not params:
            return True

        # Filtro por tamaño máximo
        if params.max_size_gb and model.size_gb > params.max_size_gb:
            return False

        # Filtro por RAM máxima
        if params.max_ram_gb and model.ram_required_gb:
            if model.ram_required_gb > params.max_ram_gb:
                return False

        # Filtro por source (siempre es GPT4ALL aquí)
        if params.source and params.source != CatalogSource.GPT4ALL:
            return False

        # Filtro por tags
        if params.tags:
            if not any(tag in model.tags for tag in params.tags):
                return False

        return True
