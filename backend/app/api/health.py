import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    db_status = "disconnected"
    redis_status = "disconnected"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception:
        pass

    status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"
    return HealthResponse(status=status, database=db_status, redis=redis_status)
