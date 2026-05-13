from __future__ import annotations

import re
import uuid
from pathlib import PurePath
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

import boto3
from botocore.client import BaseClient

from app.core.config import get_settings


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    headers: dict[str, str]
    object_key: str


class ObjectStorageClient(ABC):
    """S3-compatible object storage abstraction."""

    @abstractmethod
    def presign_put_object(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedUpload:
        raise NotImplementedError

    @abstractmethod
    def get_object_bytes(self, *, bucket: str, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete_object(self, *, bucket: str, key: str) -> None:
        raise NotImplementedError


class S3ObjectStorage(ObjectStorageClient):
    """Default implementation using boto3 (MinIO, AWS S3, etc.)."""

    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @classmethod
    def from_settings(cls) -> S3ObjectStorage:
        s = get_settings()
        session = boto3.session.Session(
            aws_access_key_id=s.s3_access_key_id or None,
            aws_secret_access_key=s.s3_secret_access_key or None,
            region_name=s.s3_region,
        )
        client = session.client(
            "s3",
            endpoint_url=s.s3_endpoint_url,
            region_name=s.s3_region,
        )
        return cls(client)

    def presign_put_object(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        expires_in: int,
    ) -> PresignedUpload:
        params = {
            "Bucket": bucket,
            "Key": key,
            "ContentType": content_type,
        }
        url = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=expires_in,
        )
        return PresignedUpload(url=url, headers={"Content-Type": content_type}, object_key=key)

    def get_object_bytes(self, *, bucket: str, key: str) -> bytes:
        resp = self._client.get_object(Bucket=bucket, Key=key)
        body = resp["Body"].read()
        if isinstance(body, (bytes, bytearray)):
            return bytes(body)
        return body.read()

    def delete_object(self, *, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)


def build_workspace_object_key(workspace_id: UUID, document_id: UUID, filename: str) -> str:
    """Namespaced object key when a document id is already known (legacy / reprocess paths)."""
    safe_name = sanitize_upload_filename(filename)
    return f"workspaces/{workspace_id}/documents/{document_id}/{safe_name}"


def sanitize_upload_filename(original: str) -> str:
    """Strip path segments, remove traversal, keep extension, bounded length."""
    base = original.replace("\\", "/").split("/")[-1].strip()
    if not base or base in (".", ".."):
        raise ValueError("invalid filename")
    path = PurePath(base)
    stem = path.stem or "file"
    ext = path.suffix[:21]
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "file"
    safe_stem = safe_stem[:180]
    safe_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext)[:20]
    if safe_ext and not safe_ext.startswith("."):
        safe_ext = f".{safe_ext}"
    return f"{safe_stem}{safe_ext}"[:220]


def build_presigned_upload_object_key(
    *,
    workspace_id: UUID,
    user_id: UUID,
    original_filename: str,
    upload_id: UUID | None = None,
) -> str:
    """
    Client upload key before a Document row exists.
    Format: workspaces/{ws}/users/{user}/uploads/{upload_id}/{safe_filename}
    """
    uid = upload_id or uuid.uuid4()
    safe = sanitize_upload_filename(original_filename)
    return f"workspaces/{workspace_id}/users/{user_id}/uploads/{uid}/{safe}"


def storage_key_is_within_workspace_scope(
    storage_key: str,
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> bool:
    prefix = f"workspaces/{workspace_id}/users/{user_id}/uploads/"
    if not storage_key.startswith(prefix):
        return False
    remainder = storage_key[len(prefix) :]
    parts = remainder.split("/")
    if len(parts) != 2:
        return False
    upload_part, filename_part = parts
    try:
        uuid.UUID(upload_part)
    except ValueError:
        return False
    if not filename_part or "/" in filename_part or filename_part in (".", ".."):
        return False
    if ".." in storage_key:
        return False
    return True


class MalwareScanProvider(ABC):
    """Placeholder hook for antivirus / malware scanning of uploaded objects."""

    @abstractmethod
    def scan_bytes(self, content: bytes, *, content_type: str) -> None:
        """Raise AppError if content should be rejected."""


class NoopMalwareScanProvider(MalwareScanProvider):
    def scan_bytes(self, content: bytes, *, content_type: str) -> None:
        _ = (content, content_type)
