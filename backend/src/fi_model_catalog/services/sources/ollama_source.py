"""
Ollama Catalog Source - Los modelos que ya moran en tu reino.

Esta fuente lista los modelos que ya están instalados en Ollama.
No descarga nada nuevo, solo muestra lo que ya tienes.
Como el inventario de la armería de Gondor.
"""

import os
from collections.abc import AsyncIterator
from datetime import datetime

import httpx

from backend.models.catalog_model import (
    CatalogModel,
    CatalogSearchParams,
    CatalogSource,
    ModelInstallProgress,
)
from backend.src.fi_model_catalog.services.sources.base import CatalogSourceBase


def _parse_ollama_name(name: str) -> tuple[str, str]:
    """Parsea nombre de Ollama (ej: 'llama3:8b' -> ('llama3', '8b'))."""
    if ":" in name:
        parts = name.split(":", 1)
        return parts[0], parts[1]
    return name, "latest"


def _extract_parameters_from_name(name: str) -> str | None:
    """Intenta extraer parámetros del nombre (ej: 'llama3:8b' -> '8B')."""
    _, tag = _parse_ollama_name(name)
    # Buscar patrones como "8b", "7b", "70b"
    import re

    match = re.search(r"(\d+\.?\d*)b", tag.lower())
    if match:
        return f"{match.group(1)}B"
    return None


def _generate_model_id(name: str) -> str:
    """Genera un ID único para un modelo de Ollama."""
    # Reemplazar : por - y limpiar
    import re

    model_id = name.replace(":", "-")
    model_id = re.sub(r"[^a-zA-Z0-9_-]", "-", model_id)
    model_id = re.sub(r"-+", "-", model_id).strip("-").lower()
    return f"ollama-{model_id}"


class OllamaCatalogSource(CatalogSourceBase):
    """
    Fuente de catálogo para modelos instalados en Ollama.

    Consulta el daemon de Ollama para listar modelos disponibles.
    Estos modelos ya están descargados y listos para usar.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self._base_url = os.getenv("OLLAMA_HOST", base_url)

    @property
    def source_name(self) -> str:
        return "ollama"

    async def list_models(self, params: CatalogSearchParams | None = None) -> list[CatalogModel]:
        """Lista todos los modelos instalados en Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self._base_url}/api/tags", timeout=10.0)
                response.raise_for_status()
                data = response.json()

            models = []
            for raw in data.get("models", []):
                model = self._convert_to_catalog_model(raw)
                if model and self._matches_filters(model, params):
                    models.append(model)

            return models

        except Exception:
            return []

    async def search_models(
        self, query: str, params: CatalogSearchParams | None = None
    ) -> list[CatalogModel]:
        """Busca entre los modelos instalados."""
        all_models = await self.list_models(params)
        query_lower = query.lower()

        return [
            m
            for m in all_models
            if query_lower in m.name.lower() or query_lower in m.filename.lower()
        ]

    async def get_model_info(self, model_id: str) -> CatalogModel | None:
        """Obtiene información de un modelo específico."""
        all_models = await self.list_models()
        return next((m for m in all_models if m.id == model_id), None)

    async def download_model(
        self, model_id: str, destination: str
    ) -> AsyncIterator[ModelInstallProgress]:
        """
        Para Ollama, 'descargar' significa hacer 'ollama pull'.

        Esta función no descarga archivos directamente,
        sino que usa el API de Ollama para pull.
        """
        # Extraer nombre de Ollama del model_id
        ollama_name = model_id.replace("ollama-", "").replace("-", ":")

        yield ModelInstallProgress(
            model_id=model_id,
            status="downloading",
            progress_percent=0,
            message=f"Pulling {ollama_name} via Ollama",
        )

        try:
            async with httpx.AsyncClient() as client:
                # Ollama pull es streaming
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/pull",
                    json={"name": ollama_name},
                    timeout=None,  # Descargas pueden ser largas
                ) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        import json

                        try:
                            data = json.loads(line)
                            status = data.get("status", "")

                            if "pulling" in status.lower():
                                total = data.get("total", 0)
                                completed = data.get("completed", 0)
                                percent = (completed / total * 100) if total > 0 else 0

                                yield ModelInstallProgress(
                                    model_id=model_id,
                                    status="downloading",
                                    progress_percent=percent,
                                    downloaded_bytes=completed,
                                    total_bytes=total,
                                    message=status,
                                )

                            elif "success" in status.lower():
                                yield ModelInstallProgress(
                                    model_id=model_id,
                                    status="completed",
                                    progress_percent=100,
                                    message=f"Successfully pulled {ollama_name}",
                                )
                                return

                        except json.JSONDecodeError:
                            continue

            yield ModelInstallProgress(
                model_id=model_id,
                status="completed",
                progress_percent=100,
                message=f"Pulled {ollama_name}",
            )

        except Exception as e:
            yield ModelInstallProgress(model_id=model_id, status="error", error=str(e))

    async def is_available(self) -> bool:
        """Verifica si el daemon de Ollama está corriendo."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self._base_url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False

    async def delete_model(self, model_name: str) -> bool:
        """Elimina un modelo de Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self._base_url}/api/delete", json={"name": model_name}, timeout=30.0
                )
                return response.status_code == 200
        except Exception:
            return False

    def _convert_to_catalog_model(self, raw: dict) -> CatalogModel | None:
        """Convierte un modelo raw de Ollama a CatalogModel."""
        try:
            name = raw.get("name", "")
            size_bytes = raw.get("size", 0)
            modified_at = raw.get("modified_at")

            # Parsear fecha si existe
            installed_at = None
            if modified_at:
                try:
                    installed_at = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
                except Exception:
                    pass

            return CatalogModel(
                id=_generate_model_id(name),
                name=name,
                filename=name,  # En Ollama, el nombre es el identificador
                source=CatalogSource.OLLAMA,
                size_bytes=size_bytes,
                parameters=_extract_parameters_from_name(name),
                is_installed=True,  # Por definición, están instalados
                installed_at=installed_at,
                tags=["ollama", "installed", "local"],
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

        # Filtro por installed_only (siempre es True para Ollama)
        # No necesita filtro adicional

        # Filtro por source
        if params.source and params.source != CatalogSource.OLLAMA:
            return False

        return True
