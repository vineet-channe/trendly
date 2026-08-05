"""FastAPI /health and /chat wiring tests (SRS §5.1) — mocked run_turn."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.session.store import reset_all_sessions

client = TestClient(app)


def setup_function() -> None:
    reset_all_sessions()


def teardown_function() -> None:
    reset_all_sessions()


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_reply_state_trace():
    fake = {
        "reply": "Order TR-4530 is delivered.",
        "trace": [
            {
                "tool": "lookup_order",
                "input": {"order_id": "TR-4530"},
                "output": {"order_id": "TR-4530", "status": "delivered"},
            }
        ],
        "state": {
            "verified": False,
            "active_order": "TR-4530",
            "escalated": False,
        },
    }
    with patch("app.main.run_turn", return_value=fake) as mocked:
        with patch("app.main.log_turn") as logged:
            response = client.post(
                "/chat",
                json={"session_id": "s-1", "message": "Where is TR-4530?"},
            )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "s-1"
    assert body["reply"] == fake["reply"]
    assert body["state"]["active_order"] == "TR-4530"
    assert body["trace"][0]["tool"] == "lookup_order"
    mocked.assert_called_once_with("s-1", "Where is TR-4530?")
    logged.assert_called_once()


def test_chat_rejects_empty_message():
    response = client.post(
        "/chat",
        json={"session_id": "s-1", "message": ""},
    )
    assert response.status_code == 422
