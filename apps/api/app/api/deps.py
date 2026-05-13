from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import AppError
from app.core.storage import ObjectStorageClient, S3ObjectStorage
from app.models.user import User
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


RequestIdDep = Annotated[str, Depends(get_request_id)]


def get_object_storage() -> ObjectStorageClient:
    return S3ObjectStorage.from_settings()


StorageDep = Annotated[ObjectStorageClient, Depends(get_object_storage)]


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            "AUTH_REQUIRED",
            "Bearer access token required",
            status_code=401,
        )
    return credentials.credentials


async def get_current_user(
    db: DbSessionDep,
    token: Annotated[str, Depends(get_bearer_token)],
) -> User:
    return await auth_service.authenticate_access_token(db, token)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
