from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_env: Literal["development", "staging", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    api_secret_key: str = Field(..., min_length=32)
    api_jwt_access_expire_minutes: int = 30
    api_jwt_refresh_expire_days: int = 14
    api_cors_origins: str = "http://localhost:5173"

    database_url: str = Field(
        ...,
        description="Async SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host:5432/db",
    )
    database_sync_url: str = Field(
        ...,
        description="Sync SQLAlchemy URL for Alembic, e.g. postgresql+psycopg://...",
    )

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_documents: str = "documents"
    s3_presign_expires_seconds: int = 3600

    vector_backend: Literal["pgvector", "qdrant"] = "pgvector"
    embedding_dimension: int = 1536
    embedding_provider: Literal["fake", "openai"] = "fake"
    embedding_batch_size: int = 32

    llm_provider: Literal["fake", "openai"] = "fake"

    # Phase 5 — retrieval & QA
    query_top_k_retrieval: int = 20
    query_top_k_final_context: int = 5
    query_min_similarity_score: float = 0.0
    query_max_context_chars: int = 12000
    query_reranking_enabled: bool = False
    query_answerability_threshold: float = 0.0
    reranker_provider: Literal["noop", "placeholder"] = "noop"

    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    ocr_provider: Literal["stub", "tesseract", "remote"] = "stub"

    rate_limit_auth_per_minute: int = 20
    rate_limit_query_per_minute: int = 30
    rate_limit_register_per_minute: int = 10
    rate_limit_login_per_minute: int = 5
    rate_limit_refresh_per_minute: int = 8
    rate_limit_upload_url_per_minute: int = 30
    rate_limit_document_create_per_minute: int = 30

    max_upload_bytes: int = 50 * 1024 * 1024
    allowed_upload_content_types: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "text/plain"
    )

    # Ingestion chunking (Phase 4)
    chunk_max_chars: int = 2000
    chunk_min_chars: int = 200
    chunk_overlap_chars: int = 200

    log_level: str = "INFO"
    log_json: bool = True

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    def allowed_upload_mime_set(self) -> set[str]:
        return {
            m.strip().lower() for m in self.allowed_upload_content_types.split(",") if m.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
