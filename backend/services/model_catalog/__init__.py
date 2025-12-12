"""
Model Catalog Service - El portal unificado de modelos locales.

Como la biblioteca de Minas Tirith, este servicio cataloga todos los
modelos disponibles de múltiples fuentes (GPT4All, HuggingFace, Ollama)
y permite descargarlos e instalarlos con un solo hechizo.
"""

# Lazy imports to avoid circular dependencies during development
__all__ = ["CatalogService"]


def __getattr__(name):
    if name == "CatalogService":
        from backend.services.model_catalog.catalog_service import CatalogService

        return CatalogService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
