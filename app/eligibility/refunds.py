"""Refund destination and timeline lookup (FR-4.4, FR-4.5, FR-4.7, §3).

The §3.1 table transcribed into code so the timeline quoted to a customer is
tied to the order's actual `payment_method` rather than to whatever the model
remembers about refunds. Two rules ride along with it:

- COD refunds need bank details, which a human collects over a secure link
  (§3.3) — this function flags the handoff and never asks for them (FR-4.5).
- The ₹99 shipping fee comes back only on a Trendly error (§3.2), never on
  change of mind.

Split out of `eligibility.py` per NFR-7's ~150-line cap.
"""

from __future__ import annotations

from typing import Any, Optional

# §3.1 — refund destination and post-inspection timeline per payment method.
# Keys cover the dataset's `payment_method` values (`prepaid_card`,
# `credit_card`, `upi`, `cash_on_delivery`) plus the debit-card and
# store-credit rows the policy table lists but no order uses.
_ROUTES: dict[str, dict[str, Any]] = {
    "credit_card": {"destination": "Original card", "timeline": "5-7 business days"},
    "debit_card": {"destination": "Original card", "timeline": "5-7 business days"},
    "prepaid_card": {"destination": "Original card", "timeline": "5-7 business days"},
    "upi": {"destination": "Original UPI ID", "timeline": "3-5 business days"},
    "cash_on_delivery": {
        "destination": "Bank transfer or store credit",
        "timeline": "7-10 business days",
    },
    "store_credit": {"destination": "Store credit", "timeline": "Immediate"},
}

# §3.2 — "Trendly error" for shipping-fee purposes: wrong, damaged, defective.
_TRENDLY_ERROR_REASONS = {"damaged", "defective", "wrong_item", "incorrect_item"}

# FR-4.4 — every timeline in §3.1 starts *after* warehouse inspection.
INSPECTION_WINDOW = "2-3 business days"

# FR-4.7 — the fee rule is answerable as policy but never bites on this
# dataset, so the note travels with the verdict instead of being asserted as
# a real deduction.
_FREE_SHIPPING_NOTE = (
    "The ₹99 fee applies only to orders below ₹1,499 (§1.3); every order in this "
    "dataset shipped free, so no shipping fee is actually at stake here."
)


def refund_route(payment_method: Optional[str], reason: str = "change_of_mind") -> dict[str, Any]:
    """Refund destination, timeline, and shipping-fee treatment for one order
    (FR-4.4, FR-4.5, FR-4.7; policy §3.1-§3.3).

    Returns `{payment_method, destination, timeline, after_inspection,
    shipping_fee_refunded, requires_human, clause_ids, notes}`.

    An unrecognised or missing payment method returns no destination and
    flags a human rather than guessing a timeline (FR-6.6) — a wrong refund
    ETA is a promise the business then has to keep.
    """
    method = (payment_method or "").strip().lower()
    route = _ROUTES.get(method)
    notes: list[str] = []
    clause_ids = ["3.1"]

    trendly_error = reason.strip().lower() in _TRENDLY_ERROR_REASONS
    if trendly_error:
        notes.append(
            "Return is due to a Trendly error, so the original shipping fee is "
            "refunded under §3.2."
        )
    else:
        notes.append(
            "Change-of-mind return, so the original shipping fee is not refunded "
            "under §3.2."
        )
    notes.append(_FREE_SHIPPING_NOTE)
    clause_ids.append("3.2")

    if route is None:
        return {
            "payment_method": payment_method,
            "destination": None,
            "timeline": None,
            "after_inspection": INSPECTION_WINDOW,
            "shipping_fee_refunded": trendly_error,
            "requires_human": True,
            "clause_ids": clause_ids,
            "notes": notes
            + [
                "Payment method is missing or unrecognised, so no refund timeline "
                "can be quoted from §3.1 — route to a human agent."
            ],
        }

    requires_human = method == "cash_on_delivery"
    if requires_human:
        clause_ids.append("3.3")
        notes.append(
            "Cash-on-delivery refunds need bank details, which a human agent "
            "collects over a secure link (§3.3). Never collect them in chat."
        )

    return {
        "payment_method": method,
        "destination": route["destination"],
        "timeline": route["timeline"],
        "after_inspection": INSPECTION_WINDOW,
        "shipping_fee_refunded": trendly_error,
        "requires_human": requires_human,
        "clause_ids": clause_ids,
        "notes": notes,
    }
