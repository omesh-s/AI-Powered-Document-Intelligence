from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _jwt_settings() -> tuple[str, str]:
    s = get_settings()
    return s.api_secret_key, "HS256"


def create_access_token(
    subject: str,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    secret, algorithm = _jwt_settings()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.api_jwt_access_expire_minutes)
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "typ": "access"}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    secret, algorithm = _jwt_settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(days=settings.api_jwt_refresh_expire_days)
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "typ": "refresh"}
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_token(token: str) -> dict[str, Any]:
    secret, algorithm = _jwt_settings()
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as exc:
        raise ValueError("invalid token") from exc


def decode_access_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("typ") != "access":
        raise ValueError("not an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("typ") != "refresh":
        raise ValueError("not a refresh token")
    return payload


def access_token_ttl_seconds() -> int:
    return get_settings().api_jwt_access_expire_minutes * 60


def refresh_token_ttl_seconds() -> int:
    return get_settings().api_jwt_refresh_expire_days * 24 * 60 * 60
