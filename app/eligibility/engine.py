"""Return/exchange eligibility rule chain (FR-4, P2, P3).

Pure functions. No LLM, no I/O beyond the read-only order store. The model
picks the tool and phrases the answer; the verdict — and crucially the *reason*
for it — is computed here (P2, FR-4.2).

The SRS §4.4 chain runs in exact order, short-circuiting on the first blocker:
`0 order state -> 1 damage claim -> 2 window -> 3 category -> 4 final sale ->
5 exchange type -> 6 footwear`. The ordering *is* the spec. Two parts of it are
load-bearing rather than incidental:

- **Damage (1) before category (3).** §6.2 covers non-returnable categories
  when the item arrives damaged or incorrect, so checking category first
  wrongly refuses damaged socks or damaged jewellery.
- **`lost_in_transit` inside step 0.** Otherwise it falls through to "not
  delivered, window hasn't started" — true, but the wrong reason where §1.6
  requires a lost-parcel escalation.

Eligibility is per line item (P3, FR-4.1): TR-4522 holds a returnable tee and
non-returnable socks, so an order-level verdict is wrong on that record.

Supporting pieces live alongside (NFR-7): verdict shape and clause wording in
`verdicts.py`, the three time thresholds in `windows.py`, the branching steps
0/1/6 in `eligibility_steps.py`, refund destinations in `refunds.py`.
"""

from __future__ import annotations

from typing import Any, Optional

import app.eligibility.verdicts as v
from app.eligibility.steps import damage_verdict, eligible_verdict, order_state_verdict
from app.orders.store import get_order
from app.eligibility.verdicts import category_of, is_non_returnable, verdict
from app.eligibility.windows import check_return_window

INTENTS = ("return", "exchange_size", "exchange_other", "damage_claim")


def _evaluate_item(
    order: dict[str, Any], item: dict[str, Any], intent: str
) -> dict[str, Any]:
    """Run the §4.4 chain for one line item, in order, short-circuiting on the
    first blocker.

    Pure over plain dicts, so every branch is reachable in a test without a
    matching record having to exist in the fixed dataset — the §2.5 footwear
    path has no delivered footwear order to run against.
    """
    blocked = order_state_verdict(order, item, intent)  # step 0
    if blocked is not None:
        return blocked

    if intent == "damage_claim":  # step 1 — deliberately before category
        return damage_verdict(order, item)

    window = check_return_window(order["delivered_at"])  # step 2
    if not window["within_window"]:
        return verdict(
            order, item, intent, eligible=False, action_allowed=None,
            clause_ids=["2.1"],
            reasons=[v.REASON_WINDOW_EXPIRED.format(days=window["days_since"])],
        )

    if is_non_returnable(item):  # step 3
        return verdict(
            order, item, intent, eligible=False, action_allowed=None,
            clause_ids=["2.3"],
            reasons=[v.REASON_CATEGORY_EXCLUDED.format(
                name=item.get("name"), category=category_of(item))],
            caveats=[v.CAVEAT_DAMAGE_FALLBACK],
        )

    if item.get("final_sale") and intent != "exchange_size":  # step 4
        return verdict(
            order, item, intent, eligible=False, action_allowed="exchange_size",
            clause_ids=["2.4"], reasons=[v.REASON_FINAL_SALE],
            caveats=[v.CAVEAT_STOCK],
        )

    if intent == "exchange_other":  # step 5
        return verdict(
            order, item, intent, eligible=False, action_allowed=None,
            clause_ids=["4.1"], reasons=[v.REASON_EXCHANGE_OTHER],
        )

    return eligible_verdict(order, item, intent, window["days_since"])  # step 6


def check_eligibility(
    order_id: str, sku: Optional[str] = None, intent: str = "return"
) -> dict[str, Any]:
    """Eligibility for one SKU, or for every SKU in the order (FR-4, §4.4).

    `sku=None` returns `{order_id, intent, verdicts: [...]}` — one verdict per
    line item, the only correct shape for a mixed order like TR-4522 (P3,
    FR-4.1). A given `sku` returns that single verdict.

    Unknown order IDs and SKUs return an explicit not-found result rather than
    the nearest match (FR-1.3) or an invented item (FR-6.6).
    """
    if intent not in INTENTS:
        return {
            "error": "unknown_intent",
            "intent": intent,
            "valid_intents": list(INTENTS),
        }

    order = get_order(order_id)
    if order is None:
        return {"error": "order_not_found", "order_id": order_id}

    items = order.get("items", [])
    if sku is None:
        return {
            "order_id": order_id,
            "intent": intent,
            "verdicts": [_evaluate_item(order, item, intent) for item in items],
        }

    item = next((i for i in items if i["sku"] == sku), None)
    if item is None:
        return {
            "error": "sku_not_in_order",
            "order_id": order_id,
            "sku": sku,
            "skus_in_order": [i["sku"] for i in items],
        }
    return _evaluate_item(order, item, intent)
