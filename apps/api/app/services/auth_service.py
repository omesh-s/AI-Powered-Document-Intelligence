from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import (
    access_token_ttl_seconds,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    refresh_token_ttl_seconds,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import AuthResponse, TokenPair
from app.schemas.user import UserResponse


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
    )


def issue_token_pair(user: User) -> TokenPair:
    sub = str(user.id)
    access = create_access_token(
        sub,
        extra_claims={"role": user.role.value},
    )
    refresh = create_refresh_token(sub)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=access_token_ttl_seconds(),
        refresh_expires_in=refresh_token_ttl_seconds(),
    )


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None,
) -> AuthResponse:
    normalized = email.strip().lower()
    existing = await session.scalar(select(User.id).where(User.email == normalized))
    if existing is not None:
        raise AppError(
            "EMAIL_ALREADY_REGISTERED",
            "An account with this email already exists",
            status_code=409,
        )
    user = User(
        email=normalized,
        full_name=full_name.strip() if full_name else None,
        hashed_password=hash_password(password),
    )
    async with session.begin():
        session.add(user)
        await session.flush()
    await session.refresh(user)
    tokens = issue_token_pair(user)
    return AuthResponse(user=user_to_response(user), tokens=tokens)


async def login_user(session: AsyncSession, *, email: str, password: str) -> AuthResponse:
    normalized = email.strip().lower()
    user = await session.scalar(select(User).where(User.email == normalized))
    if user is None or not verify_password(password, user.hashed_password):
        raise AppError(
            "INVALID_CREDENTIALS",
            "Invalid email or password",
            status_code=401,
            details=None,
        )
    if not user.is_active:
        raise AppError("USER_INACTIVE", "This account is disabled", status_code=403)
    tokens = issue_token_pair(user)
    return AuthResponse(user=user_to_response(user), tokens=tokens)


async def refresh_session(session: AsyncSession, *, refresh_token: str) -> AuthResponse:
    try:
        payload = decode_refresh_token(refresh_token)
    except ValueError:
        raise AppError("INVALID_REFRESH_TOKEN", "Invalid or expired refresh token", status_code=401)
    sub = payload.get("sub")
    if not sub:
        raise AppError("INVALID_REFRESH_TOKEN", "Invalid or expired refresh token", status_code=401)
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise AppError("INVALID_REFRESH_TOKEN", "Invalid or expired refresh token", status_code=401) from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("INVALID_REFRESH_TOKEN", "Invalid or expired refresh token", status_code=401)
    tokens = issue_token_pair(user)
    return AuthResponse(user=user_to_response(user), tokens=tokens)


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def authenticate_access_token(session: AsyncSession, token: str) -> User:
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise AppError("INVALID_ACCESS_TOKEN", "Invalid or expired access token", status_code=401)
    sub = payload.get("sub")
    if not sub:
        raise AppError("INVALID_ACCESS_TOKEN", "Invalid or expired access token", status_code=401)
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise AppError("INVALID_ACCESS_TOKEN", "Invalid or expired access token", status_code=401) from exc
    user = await session.get(User, user_id)
    if user is None:
        raise AppError("INVALID_ACCESS_TOKEN", "Invalid or expired access token", status_code=401)
    if not user.is_active:
        raise AppError("USER_INACTIVE", "This account is disabled", status_code=403)
    return user
