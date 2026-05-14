"""Document pages/chunks API (Phase 6)."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers
from tests.test_phase4_ingestion import _create_document_via_upload_url, _create_workspace, _register, process_job_sync


@pytest.fixture
def indexed_document(client: TestClient, unique_email: str) -> dict[str, UUID]:
    token = _register(client, f"art_{unique_email}")
    ws = _create_workspace(client, token, "ArtWS")
    ws_id = UUID(ws["id"])
    text = "paragraph one " * 40 + "\n\n" + "paragraph two " * 40
    doc_body, _sk, job_id = _create_document_via_upload_url(
        client,
        token=token,
        workspace_id=ws_id,
        filename="p.txt",
        content_type="text/plain",
        file_size=len(text.encode()),
        content_bytes=text.encode(),
    )
    process_job_sync(job_id)
    return {"token": token, "workspace_id": ws_id, "document_id": UUID(doc_body["id"])}


def test_list_pages_and_chunks(client: TestClient, indexed_document: dict[str, UUID]) -> None:
    token = indexed_document["token"]
    did = indexed_document["document_id"]
    rp = client.get(f"/api/documents/{did}/pages", headers=auth_headers(token))
    assert rp.status_code == 200, rp.text
    pages = rp.json()["pages"]
    assert len(pages) >= 1
    assert pages[0]["page_number"] == 1

    rc = client.get(f"/api/documents/{did}/chunks", headers=auth_headers(token))
    assert rc.status_code == 200, rc.text
    chunks = rc.json()["chunks"]
    assert len(chunks) >= 1
    assert "text" in chunks[0]
    assert chunks[0]["chunk_index"] == 0


def test_list_documents_status_filter(client: TestClient, indexed_document: dict[str, UUID]) -> None:
    token = indexed_document["token"]
    wid = indexed_document["workspace_id"]
    r = client.get(
        "/api/documents/",
        headers=auth_headers(token),
        params={"workspace_id": str(wid), "status": "indexed", "page": 1, "size": 10},
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["status"] == "indexed"
