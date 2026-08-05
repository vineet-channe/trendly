"""Phase 2 tests for refund destinations and timelines (FR-4.4, FR-4.5, FR-4.7).

The timelines are asserted against the §3.1 table directly, because the whole
point of putting them in code is that the quoted ETA can't drift from the
policy the customer could read themselves.
"""

import app.orders.store as order_store
from app.eligibility.refunds import INSPECTION_WINDOW, refund_route


def test_card_route_matches_policy_table():
    route = refund_route("credit_card")
    assert route["destination"] == "Original card"
    assert route["timeline"] == "5-7 business days"
    assert route["requires_human"] is False


def test_prepaid_card_uses_the_card_row():
    # TR-4521's payment_method is `prepaid_card`, which the §3.1 table covers
    # under "Credit / debit card" rather than as a separate row.
    assert refund_route("prepaid_card")["timeline"] == "5-7 business days"


def test_upi_route():
    route = refund_route("upi")
    assert route["destination"] == "Original UPI ID"
    assert route["timeline"] == "3-5 business days"


def test_store_credit_is_immediate():
    assert refund_route("store_credit")["timeline"] == "Immediate"


def test_cod_route_requires_a_human_and_cites_3_3():
    route = refund_route("cash_on_delivery")
    assert route["timeline"] == "7-10 business days"
    assert route["requires_human"] is True
    assert "3.3" in route["clause_ids"]
    # FR-4.5 — the handoff exists so the assistant never asks for bank details.
    assert any("secure link" in note for note in route["notes"])


def test_every_timeline_is_stated_as_after_inspection():
    for method in ("credit_card", "upi", "cash_on_delivery", "store_credit"):
        assert refund_route(method)["after_inspection"] == INSPECTION_WINDOW


def test_unknown_payment_method_invents_nothing():
    route = refund_route("crypto")
    assert route["destination"] is None
    assert route["timeline"] is None
    assert route["requires_human"] is True


def test_missing_payment_method_invents_nothing():
    route = refund_route(None)
    assert route["destination"] is None
    assert route["requires_human"] is True


def test_shipping_fee_refunded_only_on_trendly_error():
    for reason in ("damaged", "defective", "wrong_item"):
        assert refund_route("upi", reason)["shipping_fee_refunded"] is True
    assert refund_route("upi", "change_of_mind")["shipping_fee_refunded"] is False


def test_shipping_fee_note_records_the_dataset_gap():
    # FR-4.7 — every order here totals >= Rs.1,499 and shipped free, so the fee
    # rule is answerable as policy but never actually deducted.
    assert all(order["total"] >= 1499 for order in order_store.list_orders())
    notes = " ".join(refund_route("upi", "damaged")["notes"])
    assert "1,499" in notes


def test_every_route_cites_its_clauses():
    route = refund_route("credit_card", "damaged")
    assert route["clause_ids"][:2] == ["3.1", "3.2"]


def test_payment_methods_in_the_dataset_all_resolve():
    for order in order_store.list_orders():
        route = refund_route(order["payment_method"])
        assert route["destination"] is not None, order["order_id"]
