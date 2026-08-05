"""Tiered disclosure gate tests via execute_tool (Phase 6 / FR-2)."""

from __future__ import annotations

import pytest

from app.agent.dispatch import execute_tool
from app.session.store import get_session, reset_all_sessions


@pytest.fixture(autouse=True)
def _clean_sessions():
    reset_all_sessions()
    yield
    reset_all_sessions()


def test_unverified_lookup_tr4521_has_status_without_customer_id():
    """Done-when: 'where is TR-4521?' answers with no identifier."""
    state = get_session("s-tier0")
    result = execute_tool("lookup_order", {"order_id": "TR-4521"}, state)
    assert result["order_id"] == "TR-4521"
    assert result["status"] == "in_transit"
    assert result["tracking_number"]
    assert "items" in result
    assert "customer_id" not in result
    assert state.active_order_id == "TR-4521"
    assert not state.is_verified()


def test_unverified_return_requires_verification(reference_clock):
    """Done-when: 'return TR-4530' asks for verification first."""
    state = get_session("s-ret")
    result = execute_tool(
        "initiate_return",
        {"order_id": "TR-4530", "sku": "TR-KRT-033", "intent": "return"},
        state,
    )
    assert result["error"] == "verification_required"
    assert result.get("initiated") is not True


def test_unverified_delay_credit_requires_verification(reference_clock):
    state = get_session("s-credit")
    result = execute_tool(
        "issue_delay_credit", {"order_id": "TR-4525"}, state
    )
    assert result["error"] == "verification_required"
    assert result.get("issued") is not True


def test_verify_customer_with_marcus_email_sets_session():
    state = get_session("s-ver")
    result = execute_tool(
        "verify_customer",
        {"email": "marcus.bell@example.com", "order_id": "TR-4530"},
        state,
    )
    assert result == {"verified": True, "customer_id": "C-101"}
    assert state.is_verified()
    assert state.verified_customer_id == "C-101"


def test_verify_customer_wrong_contact_fails_without_owner_leak():
    state = get_session("s-bad")
    result = execute_tool(
        "verify_customer",
        {"email": "ananya.rao@example.com", "order_id": "TR-4530"},
        state,
    )
    assert result["error"] == "verification_failed"
    assert "C-101" not in str(result)
    assert "C-100" not in str(result)
    assert "Marcus" not in str(result)
    assert not state.is_verified()


def test_verified_c101_refused_on_tr4523():
    """Done-when: verified C-101 asking about TR-4523 (C-102) is refused."""
    state = get_session("s-cross")
    execute_tool(
        "verify_customer",
        {"email": "marcus.bell@example.com"},
        state,
    )
    assert state.verified_customer_id == "C-101"

    lookup = execute_tool("lookup_order", {"order_id": "TR-4523"}, state)
    assert lookup["error"] == "cross_customer"
    assert "Priya" not in str(lookup)
    assert "C-102" not in str(lookup)

    action = execute_tool(
        "initiate_return",
        {"order_id": "TR-4523", "sku": "TR-JKT-008", "intent": "return"},
        state,
    )
    assert action["error"] == "cross_customer"


def test_verified_c101_can_return_own_tr4530(reference_clock):
    state = get_session("s-own")
    execute_tool(
        "verify_customer",
        {"email": "marcus.bell@example.com", "order_id": "TR-4530"},
        state,
    )
    result = execute_tool(
        "initiate_return",
        {"order_id": "TR-4530", "sku": "TR-KRT-033", "intent": "return"},
        state,
    )
    assert result.get("initiated") is True
    assert result["order_id"] == "TR-4530"


def test_verified_owner_lookup_keeps_customer_id():
    state = get_session("s-own-lookup")
    execute_tool(
        "verify_customer",
        {"email": "ananya.rao@example.com", "order_id": "TR-4521"},
        state,
    )
    result = execute_tool("lookup_order", {"order_id": "TR-4521"}, state)
    assert result["customer_id"] == "C-100"
    assert result["status"] == "in_transit"


def test_escalate_strips_unverified_customer_id():
    state = get_session("s-esc")
    result = execute_tool(
        "escalate_to_human",
        {
            "reason": "explicit_request",
            "customer_request": "I want a human",
            "customer_id": "C-101",
            "order_id": "TR-4530",
        },
        state,
    )
    assert result["status"] == "escalated"
    assert result.get("customer_id") is None
    assert result.get("customer_name") is None
    assert "Marcus" not in str(result)
