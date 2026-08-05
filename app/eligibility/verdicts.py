"""Verdict shape and clause wording for the eligibility chain (FR-4.2, P4).

Holds three things the chain in `eligibility.py` needs but that would bury the
rule ordering if they were inlined: the §4.4 verdict dict, the §2.3 category
set, and the reason/caveat wording each step attaches.

There's a second benefit beyond NFR-7's line budget: every sentence explaining
a refusal sits next to the clause it paraphrases, so it can be audited against
`trendly_policy.md` without reading control flow. FR-3.4 forbids softening a
clause, which is easier to check as a list of strings than as f-strings
scattered through the chain.
"""

from __future__ import annotations

from typing import Any, Optional

# §2.3, normalised against the `category` values actually present in
# orders.json (`apparel`, `accessories`, `innerwear`, `jewellery`, `footwear`).
# Socks sit under `innerwear` in the data, matching §2.3's "Innerwear and socks".
NON_RETURNABLE_CATEGORIES = {
    "innerwear", "socks", "jewellery", "beauty", "fragrance",
    "beauty/fragrance", "face_masks", "face masks", "gift_card", "gift_cards",
    "gift cards",
}

# Step 0 — order state.
REASON_CANCELLED = (
    "The order was cancelled, and no return can be raised against a cancelled "
    "order (§2.6)."
)
CAVEAT_CANCELLED_REFUND = "Cancellation refund status on record: {status} (§3)."
REASON_LOST_IN_TRANSIT = (
    "The carrier marked this parcel lost. Under §1.6 that is a lost-parcel claim, "
    "not a return: a human agent resolves it within 5 business days by free "
    "replacement or full refund, at the customer's choice."
)
REASON_NOT_DELIVERED = (
    "The order is {status} and has not been delivered yet. The 30-day window is "
    "counted from delivery (§2.1), so it has not started."
)

# Step 1 — damage claim (§6).
REASON_DAMAGE_EXPIRED = (
    "Delivered {hours} hours ago, past §6.1's 48-hour window for reporting "
    "damaged, defective, or incorrect items."
)
CAVEAT_DAMAGE_HUMAN_REVIEW = (
    "Offer a human review — the assistant cannot waive §6.1 itself."
)
REASON_DAMAGE_IN_WINDOW = (
    "Reported {hours} hours after delivery, inside §6.1's 48-hour window."
)
REASON_DAMAGE_RESOLUTION = (
    "§6.2 gives the customer a free replacement or a full refund including "
    "shipping, at their choice."
)
REASON_DAMAGE_OVERRIDES_CATEGORY = (
    "§2.3 normally excludes {category}, but §6.2 covers non-returnable "
    "categories when the item arrives damaged or incorrect."
)

# Steps 2-6 — returns, exchanges, footwear (§2, §4).
REASON_WINDOW_EXPIRED = (
    "Delivered {days} calendar days ago. The return window is 30 days from "
    "delivery, and requests after 30 days are not eligible under any "
    "circumstance (§2.1)."
)
REASON_CATEGORY_EXCLUDED = (
    "{name} falls under {category}, which cannot be returned or exchanged for "
    "hygiene and safety reasons (§2.3). This is a category exclusion, not a date "
    "problem — the order is still inside its 30-day window."
)
CAVEAT_DAMAGE_FALLBACK = (
    "If the item arrived damaged, defective, or incorrect, §6.2 covers it even in "
    "this category — but it must be reported within 48 hours of delivery (§6.1)."
)
REASON_FINAL_SALE = (
    "This item is marked final sale, so it is eligible for a size exchange only — "
    "no refund and no store credit (§2.4). It is still inside the 30-day window."
)
REASON_FINAL_SALE_EXCHANGE = (
    "Final sale still allows a size exchange (§2.4), but an unavailable size needs "
    "human confirmation: §4.3 would convert it to a refund that §2.4 excludes."
)
REASON_EXCHANGE_OTHER = (
    "Trendly offers size exchanges only, not colour or style exchanges. To change "
    "colour or style the item is returned and a new order placed (§4.1)."
)
REASON_IN_WINDOW = (
    "Delivered {days} calendar days ago, inside the 30-day window (§2.1)."
)
CAVEAT_CONDITION = (
    "Item must be unworn and unwashed, with original tags and packaging (§2.2)."
)
CAVEAT_FOOTWEAR = (
    "Footwear must be returned in its original shoe box; without the box a ₹300 "
    "deduction applies (§2.5)."
)
CAVEAT_STOCK = (
    "If the requested size is unavailable the exchange automatically converts to a "
    "refund under §4.3. Stock data is not available here, so this is stated as the "
    "rule rather than checked (FR-4.8)."
)


def category_of(item: dict[str, Any]) -> str:
    """The item's category, lowercased — `None` becomes `""` rather than
    raising, since a missing field must not be invented (FR-6.6).
    """
    return str(item.get("category") or "").strip().lower()


def is_non_returnable(item: dict[str, Any]) -> bool:
    """Whether §2.3 excludes this item's category."""
    return category_of(item) in NON_RETURNABLE_CATEGORIES


def verdict(
    order: dict[str, Any],
    item: dict[str, Any],
    intent: str,
    *,
    eligible: bool,
    action_allowed: Optional[str],
    clause_ids: list[str],
    reasons: list[str],
    caveats: Optional[list[str]] = None,
    refund: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the SRS §4.4 verdict dict.

    `clause_ids` is not decoration: the reply has to cite it (P4, FR-3.2) and a
    refusal has to cite the *right* clause — TR-4527 is refused on §2.3, never
    §2.1 (FR-4.2). `action_allowed` is one of `None`, `"return"`,
    `"exchange_size"`, `"replacement_or_refund"`, `"escalate"`.
    """
    return {
        "order_id": order["order_id"],
        "sku": item["sku"],
        "item_name": item.get("name"),
        "intent": intent,
        "eligible": eligible,
        "action_allowed": action_allowed,
        "clause_ids": clause_ids,
        "reasons": reasons,
        "caveats": caveats or [],
        "refund_route": refund,
    }
