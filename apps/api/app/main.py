import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.api.routes import health as health_routes
from app.core.config import get_settings
from app.core.errors import AppError, ErrorBody, ErrorResponse
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.core.startup_validation import validate_settings_at_startup

configure_logging()
logger = get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.2f}"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
        request_id = incoming or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    validate_settings_at_startup(settings)

    app = FastAPI(
        title="Document Intelligence API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> Response:
        rid = getattr(request.state, "request_id", str(uuid.uuid4()))
        body = ErrorResponse(
            error=ErrorBody(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                requestId=rid,
            )
        )
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=exc.status_code, content=body.model_dump(by_alias=True))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> Response:
        rid = getattr(request.state, "request_id", str(uuid.uuid4()))
        body = ErrorResponse(
            error=ErrorBody(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=exc.errors(),
                requestId=rid,
            )
        )
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content=body.model_dump(by_alias=True))

    async def _http_error_response(request: Request, exc: StarletteHTTPException) -> Response:
        rid = getattr(request.state, "request_id", str(uuid.uuid4()))
        code_map = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            403: "FORBIDDEN",
            401: "UNAUTHORIZED",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            501: "NOT_IMPLEMENTED",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        detail = exc.detail
        if isinstance(detail, str):
            message = detail
            details: object | None = None
        elif isinstance(detail, (list, dict)):
            message = "Request failed"
            details = detail
        else:
            message = str(detail)
            details = None
        body = ErrorResponse(
            error=ErrorBody(
                code=code,
                message=message,
                details=details,
                requestId=rid,
            )
        )
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=exc.status_code, content=body.model_dump(by_alias=True))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
        return await _http_error_response(request, exc)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
        rid = getattr(request.state, "request_id", str(uuid.uuid4()))
        body = ErrorResponse(
            error=ErrorBody(
                code="RATE_LIMITED",
                message="Too many requests",
                details=str(exc.detail),
                requestId=rid,
            )
        )
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=429, content=body.model_dump(by_alias=True))

    app.include_router(health_routes.router, tags=["health"])
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
