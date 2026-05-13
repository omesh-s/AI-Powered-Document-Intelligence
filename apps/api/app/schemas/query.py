from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedMeta


class AskRequest(BaseModel):
    workspace_id: UUID
    document_id: UUID | None = None
    session_id: UUID | None = None
    question: str = Field(..., min_length=1, max_length=8000)
    debug: bool = False


class CitationResponse(BaseModel):
    document_id: UUID
    document_name: str
    document_version_id: UUID
    page_number: int | None = None
    chunk_id: UUID | None = None
    excerpt: str
    score: float


class QueryMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    answerability: str | None = None
    created_at: datetime | None = None
    citations: list[CitationResponse] | None = None
    debug_json: dict[str, Any] | None = None


class QuerySessionSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    document_id: UUID | None = None


class QueryDebugPayload(BaseModel):
    retrieved_chunk_ids: list[str]
    raw_scores: list[float]
    selected_chunk_ids: list[str]
    embedding_model: str | None = None
    reranker: str | None = None
    timings_ms: dict[str, float] = Field(default_factory=dict)
    llm_path: str = ""


class AskResponse(BaseModel):
    session: QuerySessionSummary
    message: QueryMessageResponse
    citations: list[CitationResponse]
    debug: QueryDebugPayload | None = None


class QuerySessionListItem(BaseModel):
    id: UUID
    workspace_id: UUID
    document_id: UUID | None = None
    title: str | None = None
    created_at: datetime


class QuerySessionListResponse(BaseModel):
    items: list[QuerySessionListItem]
    pagination: PaginatedMeta


class QuerySessionDetailResponse(BaseModel):
    session: QuerySessionSummary
    messages: list[QueryMessageResponse]
