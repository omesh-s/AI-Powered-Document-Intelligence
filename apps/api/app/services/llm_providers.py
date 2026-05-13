from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError


class LLMProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def complete(self, *, system: str, user: str) -> str:
        raise NotImplementedError


class FakeLLMProvider(LLMProvider):
    """Deterministic assistant output for tests and offline dev."""

    def __init__(self, *, model_name: str = "fake-llm-v1") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def complete(self, *, system: str, user: str) -> str:
        _ = system
        if "[[INSUFFICIENT_EVIDENCE]]" in user:
            return (
                "I do not have enough supported evidence in the retrieved context to answer "
                "this question."
            )
        if "[CHUNK_" in user:
            return "GROUNDED_ANSWER_FROM_CONTEXT"
        return "NO_CONTEXT_BLOCKS"


class OpenAILLMProvider(LLMProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, *, system: str, user: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise AppError(
                "LLM_PROVIDER_ERROR",
                "LLM provider request failed",
                status_code=502,
                details={"status": resp.status_code, "body": resp.text[:500]},
            )
        data = resp.json()
        return str(data["choices"][0]["message"]["content"] or "")


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise AppError(
                "LLM_NOT_CONFIGURED",
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai",
                status_code=503,
            )
        return OpenAILLMProvider(api_key=settings.openai_api_key, model=settings.openai_chat_model)
    return FakeLLMProvider(model_name="fake-llm-v1")
