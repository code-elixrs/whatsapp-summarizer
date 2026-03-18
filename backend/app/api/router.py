from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.items import router as items_router
from app.api.spaces import router as spaces_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(spaces_router)
api_router.include_router(items_router)
