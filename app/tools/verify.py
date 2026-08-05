"""`verify_customer` tool — Tier-1 identity check (FR-2.2, FR-2.3).

Matches email/phone against the customer store. On success the agent
dispatch layer records `SessionState.verify(customer_id)`. Failures never
reveal who owns an order (FR-2.5).
"""

from __future__ import annotations

from typing import Any, Optional

from app.orders.contacts import find_customer_by_contact
from app.orders.store import get_order
from app.session.disclosure import verification_failed_error


def verify_customer(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    order_id: Optional[str] = None,
) -> dict[str, Any]:
    """Verify the caller via matching email or phone (FR-2.2).

    Optional ``order_id`` also requires that contact to own that order.
    Mismatches return a generic ``verification_failed`` with no ownership
    hint (FR-2.3, FR-2.5). Unknown order IDs return ``order_not_found``.
    """
    if not (email and email.strip()) and not (phone and phone.strip()):
        return {
            **verification_failed_error(),
            "detail": "email_or_phone_required",
        }

    customer = find_customer_by_contact(email=email, phone=phone)
    if customer is None:
        return verification_failed_error()

    if order_id:
        order = get_order(order_id)
        if order is None:
            return {"error": "order_not_found", "order_id": order_id}
        if order["customer_id"] != customer["customer_id"]:
            return verification_failed_error()

    return {
        "verified": True,
        "customer_id": customer["customer_id"],
    }
