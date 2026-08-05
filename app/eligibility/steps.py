"""The three compound steps of the §4.4 chain (FR-4).

Steps 2-5 (window, category, final sale, exchange type) are single-condition
refusals and stay inline in `eligibility.py`, where the ordering is visible.
The three steps here each carry branching of their own, so they live apart to
keep the chain itself readable and both files inside NFR-7's ~150-line cap:

- `order_state_verdict` — step 0, three distinct order states (§2.6, §1.6, §2.1)
- `damage_verdict` — step 1, the §6.1 window plus the §6.2 category override
- `eligible_verdict` — step 6 and the allowed outcome (§2.5, §2.2, §4.2/§4.3)

Pure functions over plain dicts; no LLM, no I/O (P2).
"""

from __future__ import annotations

from typing import Any, Optional

import app.eligibility.verdicts as v
from app.eligibility.refunds import refund_route
from app.eligibility.verdicts import category_of, is_non_returnable, verdict
from app.eligibility.windows import check_damage_window


def order_state_verdict(
    order: dict[str, Any], item: dict[str, Any], intent: str
) -> Optional[dict[str, Any]]:
    """Step 0 — order state. Returns `None` when the order is delivered and the
    rest of the chain should run.

    `lost_in_transit` is handled here rather than being allowed to fall through
    to "not delivered": §1.6 makes it a lost-parcel escalation, and "your return
    window hasn't started" would be a true sentence with the wrong meaning.
    """
    status = order.get("status")
    if status == "cancelled":
        return verdict(
            order, item, intent, eligible=False, action_allowed=None,
            clause_ids=["2.6"], reasons=[v.REASON_CANCELLED],
            caveats=[v.CAVEAT_CANCELLED_REFUND.format(
                status=order.get("refund_status") or "unavailable")],
        )
    if status == "lost_in_transit":
        return verdict(
            order, item, intent, eligible=False, action_allowed="escalate",
            clause_ids=["1.6"], reasons=[v.REASON_LOST_IN_TRANSIT],
        )
    if not order.get("delivered_at"):
        return verdict(
            order, item, intent, eligible=False, action_allowed=None,
            clause_ids=["2.1"],
            reasons=[v.REASON_NOT_DELIVERED.format(status=status)],
        )
    return None


def damage_verdict(order: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    """Step 1 — the §6.1 48-hour reporting window, evaluated before the category
    check so §6.2 can override a §2.3 exclusion (FR-4.6).
    """
    window = check_damage_window(order.get("delivered_at"))
    hours = window["hours_since"]
    if not window["within_window"]:
        return verdict(
            order, item, "damage_claim", eligible=False, action_allowed=None,
            clause_ids=["6.1"],
            reasons=[v.REASON_DAMAGE_EXPIRED.format(hours=hours)],
            caveats=[v.CAVEAT_DAMAGE_HUMAN_REVIEW],
        )
    clause_ids = ["6.1", "6.2"]
    reasons = [
        v.REASON_DAMAGE_IN_WINDOW.format(hours=hours),
        v.REASON_DAMAGE_RESOLUTION,
    ]
    if is_non_returnable(item):
        clause_ids.append("2.3")
        reasons.append(
            v.REASON_DAMAGE_OVERRIDES_CATEGORY.format(category=category_of(item))
        )
    return verdict(
        order, item, "damage_claim", eligible=True,
        action_allowed="replacement_or_refund",
        clause_ids=clause_ids, reasons=reasons,
        refund=refund_route(order.get("payment_method"), "damaged"),
    )


def eligible_verdict(
    order: dict[str, Any], item: dict[str, Any], intent: str, days_since: int
) -> dict[str, Any]:
    """Step 6 and the allowed outcome — footwear caveat (§2.5), condition caveat
    (§2.2), the §4.3 stock rule on exchanges, and the refund route for a return
    (FR-4.4).
    """
    clause_ids = ["2.1", "2.2"]
    reasons = [v.REASON_IN_WINDOW.format(days=days_since)]
    caveats = [v.CAVEAT_CONDITION]
    if category_of(item) == "footwear":
        clause_ids.append("2.5")
        caveats.append(v.CAVEAT_FOOTWEAR)

    if intent == "exchange_size":
        clause_ids.append("4.2")
        caveats.append(v.CAVEAT_STOCK)
        if item.get("final_sale"):
            clause_ids.append("2.4")
            reasons.append(v.REASON_FINAL_SALE_EXCHANGE)
        return verdict(
            order, item, intent, eligible=True, action_allowed="exchange_size",
            clause_ids=clause_ids, reasons=reasons, caveats=caveats,
        )

    return verdict(
        order, item, intent, eligible=True, action_allowed="return",
        clause_ids=clause_ids, reasons=reasons, caveats=caveats,
        refund=refund_route(order.get("payment_method"), "change_of_mind"),
    )
