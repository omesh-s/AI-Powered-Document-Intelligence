import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Shared in-memory object store for tests.
# Keyed by S3 object key (the `storage_key` stored in DocumentVersion).
FAKE_OBJECT_BYTES: dict[str, bytes] = {}
FAKE_OBJECT_RAISE_ON: set[str] = set()

# Settings load at import time for several modules — provide safe defaults for tests.
os.environ.setdefault("API_SECRET_KEY", "abcdefghijklmnopqrstuvwxyz0123456789abcd")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://docintel:docintel@127.0.0.1:5432/docintel",
)
os.environ.setdefault(
    "DATABASE_SYNC_URL",
    "postgresql+psycopg://docintel:docintel@127.0.0.1:5432/docintel",
)
os.environ.setdefault("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
os.environ.setdefault("S3_ACCESS_KEY_ID", "test")
os.environ.setdefault("S3_SECRET_ACCESS_KEY", "test")
# Avoid rate-limit flakes in CI when many auth calls run in one file
os.environ.setdefault("RATE_LIMIT_REGISTER_PER_MINUTE", "200")
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MINUTE", "200")
os.environ.setdefault("RATE_LIMIT_REFRESH_PER_MINUTE", "200")
os.environ.setdefault("RATE_LIMIT_UPLOAD_URL_PER_MINUTE", "200")
os.environ.setdefault("EMBEDDING_PROVIDER", "fake")
os.environ.setdefault("LLM_PROVIDER", "fake")


@pytest.fixture(scope="session")
def database_live() -> bool:
    """True when Postgres accepts connections (run docker compose for integration tests)."""

    async def ping() -> bool:
        from app.core.database import engine

        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    return asyncio.run(ping())


@pytest.fixture
def api_client() -> TestClient:
    """HTTP client without requiring Postgres (for error-shape smoke tests)."""

    from app.api.deps import get_object_storage
    from app.core.storage import ObjectStorageClient, PresignedUpload
    from app.main import app

    class FakeObjectStorage(ObjectStorageClient):
        def presign_put_object(
            self,
            *,
            bucket: str,
            key: str,
            content_type: str,
            expires_in: int,
        ) -> PresignedUpload:
            _ = bucket
            return PresignedUpload(
                url=f"https://storage.test/presign?key={key}",
                headers={"Content-Type": content_type},
                object_key=key,
            )

        def get_object_bytes(self, *, bucket: str, key: str) -> bytes:
            _ = bucket
            if key in FAKE_OBJECT_RAISE_ON:
                raise RuntimeError("FakeObjectStorage: forced failure for key")
            return FAKE_OBJECT_BYTES.get(key, b"")

        def delete_object(self, *, bucket: str, key: str) -> None:
            _ = (bucket, key)

    app.dependency_overrides[get_object_storage] = lambda: FakeObjectStorage()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client(database_live: bool) -> TestClient:
    if not database_live:
        pytest.skip("PostgreSQL not reachable (start docker compose postgres)")

    from app.api.deps import get_object_storage
    from app.core.storage import ObjectStorageClient, PresignedUpload
    from app.main import app

    class FakeObjectStorage(ObjectStorageClient):
        def presign_put_object(
            self,
            *,
            bucket: str,
            key: str,
            content_type: str,
            expires_in: int,
        ) -> PresignedUpload:
            _ = bucket
            return PresignedUpload(
                url=f"https://storage.test/presign?key={key}",
                headers={"Content-Type": content_type},
                object_key=key,
            )

        def get_object_bytes(self, *, bucket: str, key: str) -> bytes:
            _ = bucket
            if key in FAKE_OBJECT_RAISE_ON:
                raise RuntimeError("FakeObjectStorage: forced failure for key")
            return FAKE_OBJECT_BYTES.get(key, b"")

        def delete_object(self, *, bucket: str, key: str) -> None:
            _ = (bucket, key)

    app.dependency_overrides[get_object_storage] = lambda: FakeObjectStorage()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:12]}@example.com"


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def fake_object_store() -> tuple[dict[str, bytes], set[str]]:
    """Expose fake object bytes and failure keys to tests."""
    return FAKE_OBJECT_BYTES, FAKE_OBJECT_RAISE_ON
