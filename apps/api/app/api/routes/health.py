import asyncio
import os
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"] = "ready"
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=os.environ.get("APP_VERSION", "0.1.0"))


@router.get("/ready", response_model=ReadinessResponse)
async def ready(request: Request, response: Response) -> ReadinessResponse:
    """Readiness for ingestion/query infra.

    - DB is critical.
    - Redis is checked when broker/backend are configured for redis.
    """
    _ = request
    settings = get_settings()

    async def check_db() -> bool:
        try:

            async def _ping() -> bool:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                return True

            return await asyncio.wait_for(_ping(), timeout=2.0)
        except Exception:
            return False

    redis_required = (settings.celery_broker_url or "").startswith("redis://") or (
        settings.celery_result_backend or ""
    ).startswith("redis://")

    async def check_redis() -> bool:
        if not redis_required:
            return True
        try:
            import redis.asyncio as redis_async

            async def _ping() -> bool:
                r = redis_async.from_url(
                    settings.redis_url,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                    decode_responses=False,
                )
                try:
                    await r.ping()
                    return True
                finally:
                    # Ensure we don't leak connections.
                    await r.close()

            return await asyncio.wait_for(_ping(), timeout=2.0)
        except Exception:
            return False

    db_ok = await check_db()
    redis_ok = await check_redis()

    checks = {"api": True, "db": db_ok, "redis": redis_ok}
    ok = all(checks.values())
    if not ok:
        response.status_code = 503
    return ReadinessResponse(status="ready" if ok else "not_ready", checks=checks)
