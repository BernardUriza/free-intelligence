"""Route aggregation for RAG Service."""

from fastapi import APIRouter

from routes.documents import router as documents_router
from routes.embed import router as embed_router
from routes.evaluation import router as evaluation_router
from routes.health import router as health_router
from routes.query import router as query_router
from routes.similarity import router as similarity_router
from routes.upload import router as upload_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(embed_router)
api_router.include_router(upload_router)
api_router.include_router(query_router)
api_router.include_router(documents_router)
api_router.include_router(evaluation_router)
api_router.include_router(similarity_router)
