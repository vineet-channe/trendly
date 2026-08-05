"""The `issue_delay_credit` and `escalate_to_human` tool actions
(FR-1.5, FR-1.8, FR-6.1, FR-5.2, FR-5.3, P5).

Split out of the tool-dispatch layer (`tools.py`), alongside
`tool_actions.py`'s `initiate_return`, to keep every file under
CURSOR_INSTRUCTIONS.md §4's ~150-line cap. Reuses `_mock_reference` from
`tool_actions.py` rather than duplicating it (NFR-3 — deterministic, not
random, mock references).
"""

from __future__ import annotations

from typing import Any, Optional

from dates import business_days_since
from order_store import get_customer, get_order
from tool_actions import _mock_reference
from windows import DELAY_THRESHOLD_BUSINESS_DAYS, is_delayed

SUPPORT_HOURS_NOTE = "Trendly support hours: 9:00 AM-9:00 PM IST, seven days a week."
ESCALATION_REASONS = (
    "lost_parcel", "cod_refund", "repeat_exchange", "policy_silent",
    "explicit_request", "tool_errors", "other",
)


def issue_delay_credit(order_id: str) -> dict[str, Any]:
    """Issue the \u00a71.5 \u20b9250 delayed-order credit — the only credit the assistant
    may ever offer (FR-6.1). Re-checks the FR-1.8 business-day threshold
    itself and refuses if it isn't met, so this cannot be granted just
    because the model or the customer asserts the order is late.
    """
    order = get_order(order_id)
    if order is None:
        return {"error": "order_not_found", "order_id": order_id}

    expected_delivery = order.get("expected_delivery")
    if not is_delayed(expected_delivery):
        return {
            "issued": False, "error": "threshold_not_met", "order_id": order_id,
            "business_days_past_expected": (
                business_days_since(expected_delivery) if expected_delivery else None
            ),
            "threshold_business_days": DELAY_THRESHOLD_BUSINESS_DAYS,
            "reason": (
                "Not yet more than 3 business days past expected delivery "
                "(\u00a71.5, FR-1.8) — the credit is not authorised until that "
                "threshold is met."
            ),
            "clause_ids": ["1.5"],
        }

    return {
        "issued": True, "order_id": order_id, "amount_inr": 250,
        "credit_reference": _mock_reference("CR", order_id),
        "clause_ids": ["1.5"],
        "note": "The only credit the assistant may offer without further policy backing (FR-6.1).",
    }


def escalate_to_human(
    reason: str,
    order_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    customer_request: str = "",
    checks_performed: Optional[list[str]] = None,
    recommended_action: str = "",
) -> dict[str, Any]:
    """Structured, standalone escalation summary (FR-5.2, FR-5.3, P5).

    Includes the order snapshot when `order_id` is given and the customer's
    name only when `customer_id` is present (Tier-1 verified this session,
    FR-2.2) — never guessed. Phrased as a confident handoff, not an apology
    (P5): escalation is a correct outcome for triggers like a lost parcel or
    a repeat exchange, not a failure of the assistant.
    """
    if reason not in ESCALATION_REASONS:
        reason = "other"

    order_snapshot = None
    if order_id is not None:
        order = get_order(order_id)
        order_snapshot = (
            {
                "order_id": order["order_id"], "status": order["status"],
                "items": [item.get("name") for item in order.get("items", [])],
            }
            if order is not None
            else {"error": "order_not_found", "order_id": order_id}
        )

    customer_name = None
    if customer_id is not None:
        customer = get_customer(customer_id)
        customer_name = customer["name"] if customer is not None else None

    return {
        "status": "escalated",
        "ticket_reference": _mock_reference(
            "ESC", order_id or "no-order", reason, customer_request
        ),
        "reason": reason,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "order": order_snapshot,
        "customer_request": customer_request,
        "checks_performed": checks_performed or [],
        "recommended_action": recommended_action,
        "message": (
            "This has been handed off to a specialist who will resolve it "
            "directly — no need to repeat the details above."
        ),
        "support_hours": SUPPORT_HOURS_NOTE,
    }
