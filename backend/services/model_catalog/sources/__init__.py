"""
Catalog Sources - Las fuentes de sabiduría.

Cada fuente es un reino diferente de donde provienen los modelos:
- GPT4All: Modelos curados y probados
- HuggingFace: El vasto océano de modelos de la comunidad
- Ollama: Modelos ya instalados localmente
"""

from backend.services.model_catalog.sources.base import CatalogSourceBase

__all__ = [
    "CatalogSourceBase",
    "GPT4AllCatalogSource",
    "HuggingFaceCatalogSource",
    "OllamaCatalogSource",
]


def __getattr__(name):
    """Lazy loading to avoid import errors during development."""
    if name == "GPT4AllCatalogSource":
        from backend.services.model_catalog.sources.gpt4all_source import (
            GPT4AllCatalogSource,
        )

        return GPT4AllCatalogSource
    if name == "HuggingFaceCatalogSource":
        from backend.services.model_catalog.sources.huggingface_source import (
            HuggingFaceCatalogSource,
        )

        return HuggingFaceCatalogSource
    if name == "OllamaCatalogSource":
        from backend.services.model_catalog.sources.ollama_source import (
            OllamaCatalogSource,
        )

        return OllamaCatalogSource
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
