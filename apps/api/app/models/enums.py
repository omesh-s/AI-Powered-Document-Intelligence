from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class DocumentLifecycleStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PARSING = "parsing"
    OCR_IN_PROGRESS = "ocr_in_progress"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"


class IngestionJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageExtractionMethod(str, Enum):
    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    HYBRID = "hybrid"


class StructuredBlockType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    OTHER = "other"


class QueryMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
