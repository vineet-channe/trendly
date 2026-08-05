"""Contact matching + verify_customer tool tests (Phase 6 / FR-2.2)."""

from __future__ import annotations

from app.orders.contacts import find_customer_by_contact
from app.tools import verify as verify_mod


def test_email_match_is_case_insensitive():
    customer = find_customer_by_contact(email="Marcus.Bell@Example.com")
    assert customer is not None
    assert customer["customer_id"] == "C-101"


def test_phone_match_normalizes_digits():
    customer = find_customer_by_contact(phone="14155550102")
    assert customer is not None
    assert customer["customer_id"] == "C-101"


def test_unknown_contact_returns_none():
    assert find_customer_by_contact(email="nobody@example.com") is None
    assert find_customer_by_contact(phone="000") is None


def test_verify_customer_tool_direct_phone_match():
    result = verify_mod.verify_customer(phone="+1-415-555-0102")
    assert result == {"verified": True, "customer_id": "C-101"}


def test_verify_customer_tool_wrong_order_owner():
    result = verify_mod.verify_customer(
        email="ananya.rao@example.com", order_id="TR-4530"
    )
    assert result["error"] == "verification_failed"
    assert "C-100" not in str(result)
    assert "C-101" not in str(result)
