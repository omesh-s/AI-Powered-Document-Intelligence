from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
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
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.enums import (
    DocumentLifecycleStatus,
    PageExtractionMethod,
    StructuredBlockType,
)

EMBEDDING_DIMENSION = 1536


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_workspace_status_created", "workspace_id", "status", "created_at"),
        Index("ix_documents_workspace_created", "workspace_id", "created_at"),
        Index("ix_documents_latest_version_id", "latest_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[DocumentLifecycleStatus] = mapped_column(
        Enum(DocumentLifecycleStatus, native_enum=False),
        nullable=False,
        default=DocumentLifecycleStatus.UPLOADED,
    )
    latest_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id",
    )
    latest_version: Mapped["DocumentVersion | None"] = relationship(
        foreign_keys=[latest_version_id],
        post_update=True,
    )
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(back_populates="document")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
        Index("ix_document_versions_document_id", "document_id"),
        Index("ix_document_versions_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document: Mapped[Document] = relationship(
        back_populates="versions",
        foreign_keys=[document_id],
    )
    pages: Mapped[list[Page]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(back_populates="document_version")
    citations: Mapped[list["Citation"]] = relationship(back_populates="document_version")


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "page_number",
            name="uq_pages_document_version_page_number",
        ),
        Index("ix_pages_document_version_page_number", "document_version_id", "page_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_method: Mapped[PageExtractionMethod] = mapped_column(
        Enum(PageExtractionMethod, native_enum=False),
        nullable=False,
        default=PageExtractionMethod.NATIVE_TEXT,
    )
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_version: Mapped[DocumentVersion] = relationship(back_populates="pages")
    structured_blocks: Mapped[list[StructuredBlock]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list[Chunk]] = relationship(back_populates="page")


class StructuredBlock(Base):
    __tablename__ = "structured_blocks"
    __table_args__ = (
        Index("ix_structured_blocks_page_order", "page_id", "order_index"),
        Index("ix_structured_blocks_block_type", "block_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_type: Mapped[StructuredBlockType] = mapped_column(
        Enum(StructuredBlockType, native_enum=False),
        nullable=False,
    )
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    page: Mapped[Page] = relationship(back_populates="structured_blocks")


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_document_version_chunk_index", "document_version_id", "chunk_index"),
        Index("ix_chunks_page_id", "page_id"),
        Index("ix_chunks_vector_id", "vector_id"),
        Index("ix_chunks_embedding_model", "embedding_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding: Mapped[Any | None] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)

    document_version: Mapped[DocumentVersion] = relationship(back_populates="chunks")
    page: Mapped[Page | None] = relationship(back_populates="chunks")
    citations: Mapped[list["Citation"]] = relationship(back_populates="chunk")
