from fastapi import APIRouter

from app.api.routes import admin, auth, documents, ingestion, query, users, workspaces

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
