from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.enums import QueryMessageRole

if TYPE_CHECKING:
    from app.models.document import Chunk, Document, DocumentVersion
    from app.models.user import User
    from app.models.workspace import Workspace


class QuerySession(Base):
    __tablename__ = "query_sessions"
    __table_args__ = (
        Index("ix_query_sessions_workspace_created", "workspace_id", "created_at"),
        Index("ix_query_sessions_user_created", "user_id", "created_at"),
        Index("ix_query_sessions_scope_document", "scope_document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scope_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="query_sessions")
    user: Mapped["User"] = relationship()
    scope_document: Mapped["Document | None"] = relationship()
    messages: Mapped[list["QueryMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="QueryMessage.created_at",
    )


class QueryMessage(Base):
    __tablename__ = "query_messages"
    __table_args__ = (
        Index("ix_query_messages_session_created", "session_id", "created_at"),
        Index("ix_query_messages_role", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("query_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[QueryMessageRole] = mapped_column(
        Enum(QueryMessageRole, native_enum=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    debug_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["QuerySession"] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="query_message",
        cascade="all, delete-orphan",
    )


class Citation(Base):
    __tablename__ = "citations"
    __table_args__ = (
        Index("ix_citations_query_message_id", "query_message_id"),
        Index("ix_citations_document_id", "document_id"),
        Index("ix_citations_chunk_id", "chunk_id"),
        Index("ix_citations_document_version_page", "document_version_id", "page_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("query_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    quote_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)

    query_message: Mapped["QueryMessage"] = relationship(back_populates="citations")
    document: Mapped["Document"] = relationship()
    document_version: Mapped["DocumentVersion"] = relationship(back_populates="citations")
    chunk: Mapped["Chunk | None"] = relationship(back_populates="citations")
