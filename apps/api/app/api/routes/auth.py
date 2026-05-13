from fastapi import APIRouter, Request

from app.api.deps import CurrentUserDep, DbSessionDep
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter()

_settings = get_settings()
_REGISTER = f"{_settings.rate_limit_register_per_minute}/minute"
_LOGIN = f"{_settings.rate_limit_login_per_minute}/minute"
_REFRESH = f"{_settings.rate_limit_refresh_per_minute}/minute"


@router.post("/register", response_model=AuthResponse)
@limiter.limit(_REGISTER)
async def register(request: Request, db: DbSessionDep, body: RegisterRequest) -> AuthResponse:
    _ = request
    return await auth_service.register_user(
        db,
        email=str(body.email),
        password=body.password,
        full_name=body.full_name,
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(_LOGIN)
async def login(request: Request, db: DbSessionDep, body: LoginRequest) -> AuthResponse:
    _ = request
    return await auth_service.login_user(
        db,
        email=str(body.email),
        password=body.password,
    )


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit(_REFRESH)
async def refresh_tokens(request: Request, db: DbSessionDep, body: RefreshRequest) -> AuthResponse:
    _ = request
    return await auth_service.refresh_session(db, refresh_token=body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUserDep) -> UserResponse:
    return auth_service.user_to_response(current_user)
