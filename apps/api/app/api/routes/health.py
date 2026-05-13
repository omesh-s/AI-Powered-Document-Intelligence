import os
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

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
    """Basic readiness — extend with DB/Redis pings in later phases."""
    _ = request
    checks = {"api": True}
    ok = all(checks.values())
    if not ok:
        response.status_code = 503
    return ReadinessResponse(status="ready" if ok else "not_ready", checks=checks)
