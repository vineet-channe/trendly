"""The `initiate_return` tool action (FR-4.3, P2, P6).

Split out of the tool-dispatch layer (`tools.py`) to keep it under
CURSOR_INSTRUCTIONS.md §4's ~150-line cap. `_mock_reference` is shared with
`escalation_actions.py` (the other two state-changing tools) — both need a
deterministic, non-random reference id (NFR-3).
"""

from __future__ import annotations

import hashlib
from typing import Any

from eligibility import check_eligibility


def _mock_reference(prefix: str, *parts: str) -> str:
    """Deterministic mock reference — same inputs always produce the same
    reference (NFR-3), rather than a random ID that would make test
    assertions non-reproducible."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}-{digest}"


def initiate_return(order_id: str, sku: str, intent: str = "return") -> dict[str, Any]:
    """Act on an eligible verdict: mock RMA + next steps (FR-4.3).

    Re-derives eligibility itself rather than trusting a verdict already in
    context (P2, P6) — a return cannot be talked into existence through the
    prompt. `orders.json` has `shipping_city` but no pincode, so §5.1 pickup
    vs §5.2 self-ship serviceability can't be determined from the data
    (documented gap, DEV_LOG.md); every eligible return is offered standard
    pickup with self-ship reimbursement mentioned as the alternative.
    """
    verdict = check_eligibility(order_id, sku=sku, intent=intent)
    if "error" in verdict:
        return verdict
    if not verdict["eligible"]:
        return {"initiated": False, "error": "not_eligible", **verdict}

    action = verdict["action_allowed"]
    if intent in ("return", "exchange_size") and action != intent:
        return {
            "initiated": False, "error": "action_not_allowed",
            "requested_intent": intent, "allowed_action": action, **verdict,
        }

    if action == "return":
        next_steps = [
            "Schedule a free reverse pickup; the carrier attempts pickup up to 2 times (\u00a75.1).",
            "If pickup isn't serviceable, self-ship to the warehouse for up to \u20b9150 reimbursement (\u00a75.2).",
            "Refund follows a 2-3 business day warehouse inspection (\u00a73.1).",
        ]
    elif action == "exchange_size":
        next_steps = [
            "Schedule a free reverse pickup for the original item (\u00a75.1).",
            "The new size ships once the original is picked up, no extra shipping fee.",
            "An unavailable size auto-converts to a refund (\u00a74.3) — not checked here (no stock data).",
        ]
    else:  # replacement_or_refund -- damage claim
        next_steps = [
            "Choose a free replacement or a full refund including shipping (\u00a76.2).",
            "Schedule a free reverse pickup for the damaged/incorrect item (\u00a75.1).",
        ]

    return {
        "initiated": True, "order_id": order_id, "sku": sku, "action": action,
        "rma_reference": _mock_reference("RMA", order_id, sku, intent),
        "next_steps": next_steps, "clause_ids": verdict["clause_ids"],
        "caveats": verdict["caveats"], "refund_route": verdict.get("refund_route"),
    }
