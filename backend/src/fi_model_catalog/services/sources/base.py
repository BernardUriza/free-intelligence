"""
Base class for catalog sources.

El contrato que todo reino debe cumplir para participar en el catálogo.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from backend.models.catalog_model import (
    CatalogModel,
    CatalogSearchParams,
    ModelInstallProgress,
)


class CatalogSourceBase(ABC):
    """
    Clase base abstracta para fuentes de catálogo.

    Cada fuente (GPT4All, HuggingFace, Ollama) debe implementar
    estos métodos para integrarse al catálogo unificado.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nombre de la fuente (gpt4all, huggingface, ollama)."""
        ...

    @abstractmethod
    async def list_models(self, params: CatalogSearchParams | None = None) -> list[CatalogModel]:
        """
        Lista modelos disponibles de esta fuente.

        Args:
            params: Parámetros de búsqueda/filtrado opcionales

        Returns:
            Lista de modelos disponibles
        """
        ...

    @abstractmethod
    async def search_models(
        self, query: str, params: CatalogSearchParams | None = None
    ) -> list[CatalogModel]:
        """
        Busca modelos por nombre/descripción.

        Args:
            query: Término de búsqueda
            params: Parámetros adicionales de filtrado

        Returns:
            Lista de modelos que coinciden
        """
        ...

    @abstractmethod
    async def get_model_info(self, model_id: str) -> CatalogModel | None:
        """
        Obtiene información detallada de un modelo específico.

        Args:
            model_id: ID del modelo

        Returns:
            Información del modelo o None si no existe
        """
        ...

    @abstractmethod
    async def download_model(
        self, model_id: str, destination: str
    ) -> AsyncIterator[ModelInstallProgress]:
        """
        Descarga un modelo con progreso.

        Args:
            model_id: ID del modelo a descargar
            destination: Ruta de destino

        Yields:
            Progreso de descarga
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Verifica si la fuente está disponible.

        Por ejemplo, GPT4All requiere conexión a su API,
        Ollama requiere el daemon corriendo.

        Returns:
            True si la fuente está operativa
        """
        ...
