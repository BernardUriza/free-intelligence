"""
Catalog Model - Representa un modelo disponible para descarga/instalación.

Este es el "mapa" que describe cada modelo en el catálogo unificado,
ya sea que provenga de GPT4All, HuggingFace, o el reino de Ollama.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class CatalogSource(str, Enum):
    """De qué reino proviene el modelo."""

    GPT4ALL = "gpt4all"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"


class QuantizationType(str, Enum):
    """Nivel de cuantización - el arte de comprimir la sabiduría."""

    Q4_0 = "Q4_0"  # Más pequeño, menos preciso
    Q4_K_M = "Q4_K_M"  # Balance popular
    Q5_K_M = "Q5_K_M"  # Mejor calidad
    Q8_0 = "Q8_0"  # Alta calidad, más grande
    F16 = "F16"  # Full precision
    UNKNOWN = "unknown"


class CatalogModel(BaseModel):
    """
    Un modelo disponible en el catálogo.

    Como un pergamino en la biblioteca de Rivendell:
    describe qué contiene, cuánto pesa, y qué se necesita para leerlo.
    """

    # Identificación
    id: str = Field(..., description="ID único del modelo (ej: 'llama3-8b-instruct-q4')")
    name: str = Field(..., description="Nombre legible (ej: 'Llama 3 8B Instruct')")
    filename: str = Field(..., description="Nombre del archivo GGUF")

    # Origen
    source: CatalogSource = Field(..., description="De dónde viene el modelo")
    source_url: str | None = Field(None, description="URL de descarga directa")
    repo_id: str | None = Field(
        None, description="Repo de HuggingFace (ej: 'TheBloke/Llama-3-8B-GGUF')"
    )

    # Especificaciones técnicas
    size_bytes: int = Field(..., description="Tamaño en bytes")
    ram_required_gb: float | None = Field(None, description="RAM mínima requerida en GB")
    parameters: str | None = Field(None, description="Cantidad de parámetros (ej: '8B')")
    quantization: QuantizationType = Field(default=QuantizationType.UNKNOWN)
    context_length: int | None = Field(None, description="Ventana de contexto en tokens")

    # Metadata
    description: str | None = Field(None, description="Descripción del modelo")
    license: str | None = Field(None, description="Licencia (ej: 'llama3', 'apache-2.0')")
    tags: list[str] = Field(default_factory=list, description="Tags para filtrado")

    # Estado
    is_installed: bool = Field(default=False, description="¿Ya está instalado localmente?")
    installed_at: datetime | None = Field(None)

    @property
    def size_gb(self) -> float:
        """Tamaño en GB, más legible para humanos."""
        return round(self.size_bytes / 1_000_000_000, 2)

    @property
    def is_small(self) -> bool:
        """¿Cabe en una máquina modesta? (<8GB)"""
        return self.size_gb < 8

    @property
    def is_medium(self) -> bool:
        """Tamaño medio (8-20GB)"""
        return 8 <= self.size_gb < 20

    @property
    def is_large(self) -> bool:
        """Modelo grande (>20GB)"""
        return self.size_gb >= 20


class CatalogSearchParams(BaseModel):
    """Parámetros para buscar en el catálogo."""

    query: str | None = Field(None, description="Búsqueda por nombre/descripción")
    source: CatalogSource | None = Field(None, description="Filtrar por origen")
    max_size_gb: float | None = Field(None, description="Tamaño máximo en GB")
    max_ram_gb: float | None = Field(None, description="RAM máxima requerida")
    tags: list[str] | None = Field(None, description="Filtrar por tags")
    installed_only: bool = Field(default=False, description="Solo mostrar instalados")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ModelInstallRequest(BaseModel):
    """Solicitud para instalar un modelo."""

    model_id: str = Field(..., description="ID del modelo a instalar")
    source: CatalogSource = Field(..., description="Origen del modelo")
    # Para HuggingFace, necesitamos el archivo específico
    filename: str | None = Field(None, description="Archivo específico GGUF")


class ModelInstallProgress(BaseModel):
    """Progreso de instalación de un modelo."""

    model_id: str
    status: str = Field(
        ..., description="downloading | extracting | registering | completed | error"
    )
    progress_percent: float = Field(default=0, ge=0, le=100)
    downloaded_bytes: int = Field(default=0)
    total_bytes: int = Field(default=0)
    message: str | None = Field(None)
    error: str | None = Field(None)
