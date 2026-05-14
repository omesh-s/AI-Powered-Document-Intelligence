"""Validate settings at process start (production hardening, dev warnings)."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_settings_at_startup(settings: Settings | None = None) -> None:
    """
    Fail fast in production for unsafe configuration; warn in development/staging.
    """
    s = settings or get_settings()
    key = (s.api_secret_key or "").strip()
    placeholder_secret = "change-me" in key.lower()

    if s.api_env == "production":
        if placeholder_secret or len(key) < 32:
            raise RuntimeError(
                "API_SECRET_KEY must be replaced with a strong secret before running in production "
                "(remove default placeholders; use e.g. openssl rand -hex 32)."
            )
        if s.embedding_provider == "openai" and not (s.openai_api_key or "").strip():
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai in production.")
        if s.llm_provider == "openai" and not (s.openai_api_key or "").strip():
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai in production.")
        if not s.cors_origin_list():
            raise RuntimeError("API_CORS_ORIGINS must list at least one origin in production.")
        return

    if placeholder_secret or len(key) < 40:
        logger.warning(
            "api.settings.dev_secret_reminder",
            extra={"hint": "Rotate API_SECRET_KEY for any shared or hosted environment."},
        )
