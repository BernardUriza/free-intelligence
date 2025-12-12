"""
Catalog Admin API - Endpoints para gestionar el catálogo de modelos locales.

Como la puerta de Moria: quien sepa las palabras correctas, puede entrar.
Rutas públicas bajo /api/admin/catalog/* (requiere rol admin).
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.models.catalog_model import (
    CatalogModel,
    CatalogSearchParams,
    CatalogSource,
    ModelInstallProgress,
    ModelInstallRequest,
)
from backend.services.model_catalog.catalog_service import CatalogService

router = APIRouter(prefix="/admin/catalog", tags=["catalog"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CatalogListResponse(BaseModel):
    """Respuesta de listado de modelos."""

    models: list[CatalogModel]
    total: int
    sources_status: dict[str, bool]


class SourcesStatusResponse(BaseModel):
    """Estado de las fuentes del catálogo."""

    gpt4all: bool
    huggingface: bool
    ollama: bool


class InstallResponse(BaseModel):
    """Respuesta de instalación de modelo."""

    success: bool
    message: str
    model_id: str | None = None
    llm_crud_id: str | None = None


# =============================================================================
# Singleton service
# =============================================================================

_catalog_service: CatalogService | None = None


def get_catalog_service() -> CatalogService:
    """Obtiene la instancia singleton del servicio."""
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = CatalogService()
    return _catalog_service


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/models", response_model=CatalogListResponse)
async def list_catalog_models(
    source: str | None = Query(
        None, description="Filtrar por fuente: gpt4all, huggingface, ollama"
    ),
    query: str | None = Query(None, description="Buscar por nombre"),
    max_size_gb: float | None = Query(None, description="Tamaño máximo en GB"),
    max_ram_gb: float | None = Query(None, description="RAM máxima requerida en GB"),
    installed_only: bool = Query(False, description="Solo modelos instalados"),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
):
    """
    Lista modelos disponibles en el catálogo.

    Combina modelos de GPT4All, HuggingFace y Ollama.
    Soporta filtrado por fuente, tamaño, RAM y búsqueda por nombre.
    """
    catalog = get_catalog_service()

    # Construir parámetros de búsqueda
    catalog_source = None
    if source:
        try:
            catalog_source = CatalogSource(source)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Fuente inválida: {source}. Usar: gpt4all, huggingface, ollama",
            )

    params = CatalogSearchParams(
        source=catalog_source,
        max_size_gb=max_size_gb,
        max_ram_gb=max_ram_gb,
        installed_only=installed_only,
        limit=limit,
        offset=offset,
    )

    # Obtener modelos
    if query:
        models = await catalog.search_models(query, params)
    else:
        models = await catalog.list_models(params)

    # Filtrar por installed_only si está activo
    if installed_only:
        models = [m for m in models if m.is_installed]

    # Obtener estado de fuentes
    sources_status = await catalog.get_sources_status()

    return CatalogListResponse(
        models=models,
        total=len(models),
        sources_status=sources_status,
    )


@router.get("/models/{model_id}", response_model=CatalogModel)
async def get_catalog_model(model_id: str):
    """Obtiene información detallada de un modelo específico."""
    catalog = get_catalog_service()
    model = await catalog.get_model(model_id)

    if not model:
        raise HTTPException(status_code=404, detail=f"Modelo no encontrado: {model_id}")

    return model


@router.get("/sources/status", response_model=SourcesStatusResponse)
async def get_sources_status():
    """Obtiene el estado de disponibilidad de cada fuente."""
    catalog = get_catalog_service()
    status = await catalog.get_sources_status()

    return SourcesStatusResponse(
        gpt4all=status.get("gpt4all", False),
        huggingface=status.get("huggingface", False),
        ollama=status.get("ollama", False),
    )


@router.post("/models/install", response_model=InstallResponse)
async def install_model(request: ModelInstallRequest):
    """
    Instala un modelo del catálogo.

    Descarga el modelo (si es necesario), lo registra en Ollama,
    y crea una entrada en el CRUD de LLM Models.
    """
    catalog = get_catalog_service()

    # Buscar el modelo
    model = await catalog.get_model(request.model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Modelo no encontrado: {request.model_id}")

    try:
        # Instalar (sin progreso para endpoint síncrono)
        result = await catalog.install_model(model)

        return InstallResponse(
            success=True,
            message=f"Modelo {model.name} instalado exitosamente",
            model_id=model.id,
            llm_crud_id=result.get("id") if result else None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}/install/stream")
async def install_model_stream(model_id: str):
    """
    Instala un modelo con progreso en tiempo real (Server-Sent Events).

    Útil para mostrar barra de progreso en el frontend.
    """
    catalog = get_catalog_service()

    model = await catalog.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Modelo no encontrado: {model_id}")

    async def generate_progress():
        """Generador de eventos SSE."""
        try:
            async for progress in catalog.install_model_with_progress(model):
                # Formato SSE
                data = progress.model_dump_json()
                yield f"data: {data}\n\n"

                if progress.status in ("completed", "error"):
                    break

        except Exception as e:
            error_progress = ModelInstallProgress(model_id=model_id, status="error", error=str(e))
            yield f"data: {error_progress.model_dump_json()}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.delete("/models/{model_id}")
async def delete_installed_model(model_id: str):
    """
    Elimina un modelo instalado de Ollama.

    Nota: Solo funciona para modelos de la fuente 'ollama'.
    """
    catalog = get_catalog_service()

    model = await catalog.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Modelo no encontrado: {model_id}")

    if model.source != CatalogSource.OLLAMA:
        raise HTTPException(
            status_code=400, detail="Solo se pueden eliminar modelos instalados (fuente: ollama)"
        )

    if not model.is_installed:
        raise HTTPException(status_code=400, detail="El modelo no está instalado")

    # Eliminar de Ollama
    from backend.services.model_catalog.sources.ollama_source import OllamaCatalogSource

    ollama = OllamaCatalogSource()
    success = await ollama.delete_model(model.filename)

    if not success:
        raise HTTPException(status_code=500, detail="Error al eliminar el modelo de Ollama")

    return {"success": True, "message": f"Modelo {model.name} eliminado"}
