from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.query import Citation
from app.services import ingestion_service
from tests.conftest import FAKE_OBJECT_BYTES, FAKE_OBJECT_RAISE_ON, auth_headers
from tests.test_phase4_ingestion import (
    FakeObjectStorage,
    _create_document_via_upload_url,
    _create_workspace,
    _register,
)


def _para(token: str, reps: int = 30) -> str:
    return " ".join([token] * reps)


async def _process_job_local(job_id: UUID) -> None:
    storage = FakeObjectStorage(FAKE_OBJECT_BYTES, FAKE_OBJECT_RAISE_ON)
    async with AsyncSessionLocal() as session:
        await ingestion_service.process_ingestion_job(
            session,
            job_id=job_id,
            storage_client=storage,
        )


def _ingest_txt(client: TestClient, token: str, workspace_id: UUID, text: str) -> dict[str, Any]:
    content_bytes = text.encode("utf-8")
    doc_body, _sk, job_id = _create_document_via_upload_url(
        client,
        token=token,
        workspace_id=workspace_id,
        filename="phase5.txt",
        content_type="text/plain",
        file_size=len(content_bytes),
        content_bytes=content_bytes,
    )
    asyncio.run(_process_job_local(job_id))
    return doc_body


def test_ask_single_document_grounded_with_citations(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"q5_{unique_email}")
    ws = _create_workspace(client, token, "Q5WS")
    ws_id = UUID(ws["id"])
    body = _para("RISK_ALPHA", 35) + "\n\n" + _para("OTHER_BETA", 35)
    doc = _ingest_txt(client, token, ws_id, body)
    doc_id = UUID(doc["id"])
    q = _para("RISK_ALPHA", 35)
    r = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(doc_id),
            "question": q,
            "debug": False,
        },
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["message"]["answerability"] == "grounded"
    assert "GROUNDED_ANSWER_FROM_CONTEXT" in out["message"]["content"]
    assert len(out["citations"]) >= 1
    assert all(str(c["document_id"]) == str(doc_id) for c in out["citations"])
    assert out["debug"] is None


def test_ask_forbidden_non_member_workspace(client: TestClient, unique_email: str) -> None:
    t1 = _register(client, f"o_{unique_email}")
    t2 = _register(client, f"i_{unique_email}")
    ws = _create_workspace(client, t1, "OwnerOnly")
    ws_id = UUID(ws["id"])
    body = _para("SECRET", 40)
    doc = _ingest_txt(client, t1, ws_id, body)
    r = client.post(
        "/api/query/ask",
        headers=auth_headers(t2),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(doc["id"]),
            "question": _para("SECRET", 40),
        },
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "WORKSPACE_ACCESS_DENIED"


def test_list_sessions_forbidden_non_member(client: TestClient, unique_email: str) -> None:
    t1 = _register(client, f"a_{unique_email}")
    t2 = _register(client, f"b_{unique_email}")
    ws = _create_workspace(client, t1, "OwnedWS")
    r = client.get(
        "/api/query/sessions",
        headers=auth_headers(t2),
        params={"workspace_id": ws["id"]},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "WORKSPACE_ACCESS_DENIED"


def test_insufficient_evidence_high_threshold(
    client: TestClient, unique_email: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUERY_ANSWERABILITY_THRESHOLD", "2.0")
    get_settings.cache_clear()
    try:
        token = _register(client, f"ins_{unique_email}")
        ws = _create_workspace(client, token, "InsWS")
        ws_id = UUID(ws["id"])
        body = _para("LOW_SIGNAL", 40)
        doc = _ingest_txt(client, token, ws_id, body)
        doc_id = UUID(doc["id"])
        r = client.post(
            "/api/query/ask",
            headers=auth_headers(token),
            json={
                "workspace_id": str(ws_id),
                "document_id": str(doc_id),
                "question": "What is the meaning of life?",
                "debug": False,
            },
        )
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["message"]["answerability"] == "insufficient_evidence"
        assert out["citations"] == []
        assert "insufficient" in out["message"]["content"].lower()
    finally:
        monkeypatch.delenv("QUERY_ANSWERABILITY_THRESHOLD", raising=False)
        get_settings.cache_clear()


def test_session_continuation_appends_messages(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"cont_{unique_email}")
    ws = _create_workspace(client, token, "ContWS")
    ws_id = UUID(ws["id"])
    body = _para("THREAD_X", 40)
    doc = _ingest_txt(client, token, ws_id, body)
    doc_id = UUID(doc["id"])
    q1 = _para("THREAD_X", 40)
    r1 = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={"workspace_id": str(ws_id), "document_id": str(doc_id), "question": q1},
    )
    assert r1.status_code == 200
    sid = r1.json()["session"]["id"]
    r2 = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(doc_id),
            "session_id": sid,
            "question": "Follow-up about THREAD_X?",
        },
    )
    assert r2.status_code == 200
    det = client.get(f"/api/query/sessions/{sid}", headers=auth_headers(token))
    assert det.status_code == 200
    msgs = det.json()["messages"]
    assert len(msgs) == 4
    roles = [m["role"] for m in msgs]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_citations_persisted_linked_to_assistant(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"cite_{unique_email}")
    ws = _create_workspace(client, token, "CiteWS")
    ws_id = UUID(ws["id"])
    body = _para("CITE_Z", 40)
    doc = _ingest_txt(client, token, ws_id, body)
    doc_id = UUID(doc["id"])
    q = _para("CITE_Z", 40)
    r = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={"workspace_id": str(ws_id), "document_id": str(doc_id), "question": q},
    )
    assert r.status_code == 200
    mid = UUID(r.json()["message"]["id"])

    async def _count() -> int:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import func

            stmt = (
                select(func.count()).select_from(Citation).where(Citation.query_message_id == mid)
            )
            return int((await session.execute(stmt)).scalar_one())

    cnt = asyncio.run(_count())
    assert cnt == len(r.json()["citations"])


def test_session_list_scoped_to_user_and_filters(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"lst_{unique_email}")
    ws = _create_workspace(client, token, "LstWS")
    ws_id = UUID(ws["id"])
    d1 = _ingest_txt(client, token, ws_id, _para("D1", 40))
    _ingest_txt(client, token, ws_id, _para("D2", 40))
    client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(d1["id"]),
            "question": _para("D1", 40),
        },
    )
    r = client.get(
        "/api/query/sessions",
        headers=auth_headers(token),
        params={"workspace_id": str(ws_id), "document_id": str(d1["id"])},
    )
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 1
    assert r.json()["items"][0]["document_id"] == str(d1["id"])

    r2 = client.get(
        "/api/query/sessions",
        headers=auth_headers(token),
        params={"workspace_id": str(ws_id)},
    )
    assert r2.status_code == 200
    assert r2.json()["pagination"]["total"] >= 1


def test_session_detail_ordered_with_citations(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"det_{unique_email}")
    ws = _create_workspace(client, token, "DetWS")
    ws_id = UUID(ws["id"])
    doc = _ingest_txt(client, token, ws_id, _para("DETAIL_Q", 40))
    doc_id = UUID(doc["id"])
    client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(doc_id),
            "question": _para("DETAIL_Q", 40),
        },
    )
    lst = client.get(
        "/api/query/sessions",
        headers=auth_headers(token),
        params={"workspace_id": str(ws_id)},
    )
    sid = lst.json()["items"][0]["id"]
    det = client.get(f"/api/query/sessions/{sid}", headers=auth_headers(token))
    assert det.status_code == 200
    data = det.json()
    assert data["messages"][0]["role"] == "user"
    asst = [m for m in data["messages"] if m["role"] == "assistant"][0]
    assert asst["citations"] is not None
    assert len(asst["citations"]) >= 1
    assert asst["answerability"] == "grounded"


def test_retrieval_filter_by_document_id(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"fil_{unique_email}")
    ws = _create_workspace(client, token, "FilWS")
    ws_id = UUID(ws["id"])
    doc_a = _ingest_txt(client, token, ws_id, _para("ONLY_A", 40))
    _ingest_txt(client, token, ws_id, _para("ONLY_B", 40))
    doc_a_id = UUID(doc_a["id"])
    r = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(doc_a_id),
            "question": _para("ONLY_A", 40),
        },
    )
    assert r.status_code == 200
    for c in r.json()["citations"]:
        assert c["document_id"] == str(doc_a_id)


def test_vector_retrieval_prefers_matching_chunk_text(
    client: TestClient, unique_email: str
) -> None:
    token = _register(client, f"vec_{unique_email}")
    ws = _create_workspace(client, token, "VecWS")
    ws_id = UUID(ws["id"])
    left = _para("LEFTMARK", 40)
    right = _para("RIGHTMARK", 40)
    body = left + "\n\n" + right
    doc = _ingest_txt(client, token, ws_id, body)
    doc_id = UUID(doc["id"])
    r = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(doc_id),
            "question": right.strip(),
        },
    )
    assert r.status_code == 200
    cites = r.json()["citations"]
    assert cites
    assert "RIGHTMARK" in cites[0]["excerpt"]


def test_ask_workspace_scope_without_document_id(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"wscope_{unique_email}")
    ws = _create_workspace(client, token, "WScope")
    ws_id = UUID(ws["id"])
    body = _para("WORKSPACE_SCOPE_TOKEN", 40)
    _ingest_txt(client, token, ws_id, body)
    r = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "question": _para("WORKSPACE_SCOPE_TOKEN", 40),
        },
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["session"]["document_id"] is None
    assert out["message"]["answerability"] == "grounded"
    assert len(out["citations"]) >= 1


def test_debug_mode_returns_retrieval_metadata(client: TestClient, unique_email: str) -> None:
    token = _register(client, f"dbg_{unique_email}")
    ws = _create_workspace(client, token, "DbgWS")
    ws_id = UUID(ws["id"])
    doc = _ingest_txt(client, token, ws_id, _para("DBG", 40))
    doc_id = UUID(doc["id"])
    r = client.post(
        "/api/query/ask",
        headers=auth_headers(token),
        json={
            "workspace_id": str(ws_id),
            "document_id": str(doc_id),
            "question": _para("DBG", 40),
            "debug": True,
        },
    )
    assert r.status_code == 200
    dbg = r.json()["debug"]
    assert dbg is not None
    assert "retrieved_chunk_ids" in dbg
    assert "raw_scores" in dbg
    assert "selected_chunk_ids" in dbg
    assert "timings_ms" in dbg
