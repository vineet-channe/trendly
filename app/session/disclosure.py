"""Tiered disclosure gates and Tier-0 redaction (FR-2, SRS §4.2).

Enforcement lives here (and is called from `agent.dispatch`) so Tier-1
actions and cross-customer lookups cannot be talked past via the prompt —
same pattern as the repeat-exchange gate (FR-5.1).
"""

from __future__ import annotations

from typing import Any, Optional

from app.orders.store import get_order
from app.session.state import SessionState

TIER1_TOOLS = frozenset({"initiate_return", "issue_delay_credit"})

# Tools that take an order_id and must respect FR-2.4 once the session is
# verified as a specific customer.
ORDER_SCOPED_TOOLS = frozenset({
    "lookup_order",
    "check_eligibility",
    "initiate_return",
    "issue_delay_credit",
    "escalate_to_human",
    "verify_customer",
})

_VERIFICATION_REQUIRED = (
    "Verification required before this action. Ask the customer for the "
    "email or phone on the order. Do not reveal who owns the order."
)
_CROSS_CUSTOMER = (
    "This session is verified for a different customer. Refuse without "
    "confirming who owns the requested order (FR-2.4, §7)."
)
_VERIFICATION_FAILED = (
    "Could not verify identity from the details provided. Do not reveal "
    "who owns the order; Tier-0 status answers remain available."
)


def order_id_from_input(
    name: str, tool_input: dict[str, Any]
) -> Optional[str]:
    """Pull `order_id` from tool input when the tool is order-scoped."""
    if name not in ORDER_SCOPED_TOOLS:
        return None
    order_id = tool_input.get("order_id")
    return order_id if isinstance(order_id, str) and order_id else None


def tier0_order_view(order: dict[str, Any]) -> dict[str, Any]:
    """Order payload safe for unverified sessions (FR-2.1, FR-2.5).

    Drops `customer_id` so the model cannot voice or imply identity.
    Name/email/phone are not on the order object and are never attached.
    """
    return {k: v for k, v in order.items() if k != "customer_id"}


def verification_required_error(order_id: Optional[str] = None) -> dict[str, Any]:
    """Stable Tier-1 gate refusal (FR-2.2, FR-2.3)."""
    out: dict[str, Any] = {
        "error": "verification_required",
        "message": _VERIFICATION_REQUIRED,
    }
    if order_id:
        out["order_id"] = order_id
    return out


def cross_customer_error(order_id: Optional[str] = None) -> dict[str, Any]:
    """Stable cross-customer refusal with no ownership hint (FR-2.4)."""
    out: dict[str, Any] = {
        "error": "cross_customer",
        "message": _CROSS_CUSTOMER,
    }
    if order_id:
        out["order_id"] = order_id
    return out


def verification_failed_error() -> dict[str, Any]:
    """Stable identity-mismatch refusal (FR-2.3, FR-2.5)."""
    return {"error": "verification_failed", "message": _VERIFICATION_FAILED}


def gate_tool_access(
    state: SessionState, name: str, tool_input: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """Return an error dict if the call must not proceed, else ``None``.

    Order of checks (FR-2):
    1. Cross-customer — verified session + foreign order → refuse even Tier 0
    2. Tier-1 action without verification → ``verification_required``
    """
    order_id = order_id_from_input(name, tool_input)
    order = get_order(order_id) if order_id else None

    if state.is_verified() and order is not None:
        if order["customer_id"] != state.verified_customer_id:
            return cross_customer_error(order_id)

    if name in TIER1_TOOLS:
        if not state.is_verified():
            return verification_required_error(order_id)
        if order is not None and order["customer_id"] != state.verified_customer_id:
            return cross_customer_error(order_id)

    return None
