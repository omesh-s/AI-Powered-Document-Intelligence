"""Phase 3: auth, workspaces, documents, ingestion job stub."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def _assert_error_envelope(body: dict) -> None:
    assert "error" in body
    err = body["error"]
    assert "code" in err
    assert "message" in err
    assert "requestId" in err
    assert "details" in err


def test_register_success(client: TestClient, unique_email: str) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1", "full_name": "Test User"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "tokens" in data
    assert data["tokens"]["token_type"] == "bearer"
    assert data["tokens"]["expires_in"] > 0
    assert data["tokens"]["refresh_expires_in"] > 0
    assert data["user"]["email"] == unique_email.lower()


def test_register_duplicate_email_fails(client: TestClient, unique_email: str) -> None:
    payload = {"email": unique_email, "password": "securepass1"}
    r1 = client.post("/api/auth/register", json=payload)
    assert r1.status_code == 200
    r2 = client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409
    _assert_error_envelope(r2.json())


def test_login_success(client: TestClient, unique_email: str) -> None:
    password = "anothersecure1"
    client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": password},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert response.status_code == 200
    assert response.json()["tokens"]["access_token"]


def test_login_bad_password_fails(client: TestClient, unique_email: str) -> None:
    client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "rightpassword1"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "wrongpassword1"},
    )
    assert response.status_code == 401
    _assert_error_envelope(response.json())


def test_me_requires_auth(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    _assert_error_envelope(response.json())


def test_refresh_returns_valid_access(client: TestClient, unique_email: str) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    refresh = reg.json()["tokens"]["refresh_token"]
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    new_access = response.json()["tokens"]["access_token"]
    me = client.get("/api/auth/me", headers=auth_headers(new_access))
    assert me.status_code == 200
    assert me.json()["email"] == unique_email.lower()


def test_me_with_token(client: TestClient, unique_email: str) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    token = reg.json()["tokens"]["access_token"]
    response = client.get("/api/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["email"] == unique_email.lower()


def test_create_workspace_success(client: TestClient, unique_email: str) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    token = reg.json()["tokens"]["access_token"]
    response = client.post(
        "/api/workspaces/",
        headers=auth_headers(token),
        json={"name": "My Team"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My Team"
    assert body["slug"]


def test_workspace_detail_forbidden_non_member(client: TestClient, unique_email: str) -> None:
    owner_reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    owner_token = owner_reg.json()["tokens"]["access_token"]
    ws = client.post(
        "/api/workspaces/",
        headers=auth_headers(owner_token),
        json={"name": "Private"},
    ).json()

    other_email = f"other_{uuid.uuid4().hex[:10]}@example.com"
    other_reg = client.post(
        "/api/auth/register",
        json={"email": other_email, "password": "securepass1"},
    )
    other_token = other_reg.json()["tokens"]["access_token"]

    response = client.get(
        f"/api/workspaces/{ws['id']}",
        headers=auth_headers(other_token),
    )
    assert response.status_code == 403
    _assert_error_envelope(response.json())


def test_upload_url_validates_content_type(client: TestClient, unique_email: str) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    token = reg.json()["tokens"]["access_token"]
    ws = client.post(
        "/api/workspaces/",
        headers=auth_headers(token),
        json={"name": "Docs"},
    ).json()

    response = client.post(
        "/api/documents/upload-url",
        headers=auth_headers(token),
        json={
            "workspace_id": ws["id"],
            "filename": "x.pdf",
            "content_type": "application/octet-stream",
            "file_size": 1024,
        },
    )
    assert response.status_code == 415
    _assert_error_envelope(response.json())


def test_upload_url_validates_file_size(client: TestClient, unique_email: str) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    token = reg.json()["tokens"]["access_token"]
    ws = client.post(
        "/api/workspaces/",
        headers=auth_headers(token),
        json={"name": "Docs"},
    ).json()

    response = client.post(
        "/api/documents/upload-url",
        headers=auth_headers(token),
        json={
            "workspace_id": ws["id"],
            "filename": "x.pdf",
            "content_type": "application/pdf",
            "file_size": 200 * 1024 * 1024,
        },
    )
    assert response.status_code == 413
    _assert_error_envelope(response.json())


def test_create_document_creates_version_and_queued_job(
    client: TestClient,
    unique_email: str,
) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    token = reg.json()["tokens"]["access_token"]
    ws = client.post(
        "/api/workspaces/",
        headers=auth_headers(token),
        json={"name": "Docs"},
    ).json()

    up = client.post(
        "/api/documents/upload-url",
        headers=auth_headers(token),
        json={
            "workspace_id": ws["id"],
            "filename": "report.pdf",
            "content_type": "application/pdf",
            "file_size": 5000,
        },
    )
    assert up.status_code == 200
    storage_key = up.json()["storage_key"]

    create = client.post(
        "/api/documents/",
        headers=auth_headers(token),
        json={
            "workspace_id": ws["id"],
            "filename": "report.pdf",
            "content_type": "application/pdf",
            "file_size": 5000,
            "storage_key": storage_key,
            "checksum_sha256": "a" * 64,
        },
    )
    assert create.status_code == 200
    doc = create.json()
    assert doc["status"] == "queued"
    assert doc["latest_version_id"] is not None
    assert doc["ingestion_job"] is not None
    assert doc["ingestion_job"]["status"] == "pending"
    assert doc["ingestion_job"]["stage"] == "queued"


def test_list_documents_only_member_workspace(client: TestClient, unique_email: str) -> None:
    reg_a = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    token_a = reg_a.json()["tokens"]["access_token"]
    ws = client.post(
        "/api/workspaces/",
        headers=auth_headers(token_a),
        json={"name": "A"},
    ).json()

    other_email = f"b_{uuid.uuid4().hex[:10]}@example.com"
    reg_b = client.post(
        "/api/auth/register",
        json={"email": other_email, "password": "securepass1"},
    )
    token_b = reg_b.json()["tokens"]["access_token"]

    response = client.get(
        "/api/documents/",
        headers=auth_headers(token_b),
        params={"workspace_id": ws["id"]},
    )
    assert response.status_code == 403
    _assert_error_envelope(response.json())


def test_delete_document_soft_delete(client: TestClient, unique_email: str) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "securepass1"},
    )
    token = reg.json()["tokens"]["access_token"]
    ws = client.post(
        "/api/workspaces/",
        headers=auth_headers(token),
        json={"name": "Docs"},
    ).json()
    up = client.post(
        "/api/documents/upload-url",
        headers=auth_headers(token),
        json={
            "workspace_id": ws["id"],
            "filename": "a.txt",
            "content_type": "text/plain",
            "file_size": 10,
        },
    ).json()
    doc = client.post(
        "/api/documents/",
        headers=auth_headers(token),
        json={
            "workspace_id": ws["id"],
            "filename": "a.txt",
            "content_type": "text/plain",
            "file_size": 10,
            "storage_key": up["storage_key"],
        },
    ).json()

    delete = client.delete(f"/api/documents/{doc['id']}", headers=auth_headers(token))
    assert delete.status_code == 204

    get_doc = client.get(f"/api/documents/{doc['id']}", headers=auth_headers(token))
    assert get_doc.status_code == 404


def test_http_error_envelope_shape(api_client: TestClient) -> None:
    response = api_client.get("/api/no-such-path-for-phase3-test")
    assert response.status_code == 404
    _assert_error_envelope(response.json())
