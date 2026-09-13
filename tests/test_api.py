from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, limiter

TEST_API_KEY = "test-key-123"


@pytest.fixture(autouse=True)
def _isolate_rate_limiter_and_api_key(monkeypatch):
    """slowapi's Limiter keeps request counts in shared, module-level storage,
    so without a reset, one test's calls to /chat would count against the
    next test's rate-limit budget. Also pin CHAT_API_KEY to a known test
    value instead of depending on whatever happens to be in the real .env.
    """
    monkeypatch.setenv("CHAT_API_KEY", TEST_API_KEY)
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(key=TEST_API_KEY):
    return {"x-api-key": key}


# --- health ---------------------------------------------------------------


def test_health_requires_no_auth(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- auth -------------------------------------------------------------


def test_chat_without_api_key_header_is_rejected(client):
    response = client.post("/chat", json={"question": "test"})
    assert response.status_code == 422  # FastAPI's own validation for a missing required header


def test_chat_with_wrong_api_key_is_rejected(client):
    response = client.post("/chat", json={"question": "test"}, headers=auth_headers("wrong-key"))
    assert response.status_code == 401


def test_documents_get_requires_api_key(client):
    response = client.get("/documents")
    assert response.status_code == 422


def test_documents_post_requires_api_key(client):
    response = client.post(
        "/documents",
        json={"company": "Apple", "year": 2025, "document_type": "10-K", "stage_path": "x", "source_filename": "x"},
    )
    assert response.status_code == 422


# --- /chat happy path + error handling ------------------------------------


def test_chat_with_valid_key_and_question_returns_answer(client):
    fake_result = {
        "answer": "Apple's revenue was $416.161 billion.",
        "tool_calls": ["sql_tool"],
        "hybrid_results": [],
        "sql_results": [
            {"company": "Apple", "year": 2025, "metric_name": "revenue", "metric_value": 416161000000}
        ],
    }
    with patch("src.api.main.answer_question", return_value=fake_result):
        response = client.post("/chat", json={"question": "What was Apple's revenue?"}, headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == fake_result["answer"]
    assert body["tool_calls"] == ["sql_tool"]
    assert body["sources"] == [{"type": "financial_metric", "company": "Apple", "year": 2025, "detail": "revenue"}]


def test_chat_rejects_a_request_body_missing_the_question_field(client):
    response = client.post("/chat", json={}, headers=auth_headers())
    assert response.status_code == 422


def test_chat_rejects_a_non_string_question(client):
    response = client.post("/chat", json={"question": 12345}, headers=auth_headers())
    assert response.status_code == 422


def test_chat_deduplicates_repeated_sources_from_neighbor_chunks():
    fake_result = {
        "answer": "answer",
        "tool_calls": ["hybrid_search"],
        "hybrid_results": [
            {"company": "Apple", "year": 2025, "section": "Item 1A. Risk Factors", "is_neighbor": False},
            {"company": "Apple", "year": 2025, "section": "Item 1A. Risk Factors", "is_neighbor": True},
        ],
        "sql_results": [],
    }
    with patch("src.api.main.answer_question", return_value=fake_result):
        client = TestClient(app)
        response = client.post("/chat", json={"question": "q"}, headers=auth_headers())

    assert len(response.json()["sources"]) == 1


# --- rate limiting ----------------------------------------------------


def test_chat_rate_limit_allows_ten_then_blocks_the_eleventh(client):
    fake_result = {"answer": "x", "tool_calls": [], "hybrid_results": [], "sql_results": []}
    with patch("src.api.main.answer_question", return_value=fake_result):
        statuses = [
            client.post("/chat", json={"question": "q"}, headers=auth_headers()).status_code for _ in range(11)
        ]

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429
