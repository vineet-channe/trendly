"""Phase 2 tests for the non-return intents and the chain's ordering (FR-4).

Two orderings from SRS §4.4 are asserted directly here, because they are the
part of the chain most likely to be "simplified" into a bug later:

- a damage claim on non-returnable socks is eligible under §6.2, proving the
  damage check runs before the category check;
- a damage claim on a lost parcel still escalates under §1.6, proving step 0
  runs before the damage check.
"""

from datetime import datetime

import eligibility
from eligibility import check_eligibility

# Item copied from TR-4525 (Court Sneakers). The dataset has no *delivered*
# footwear order — TR-4525 is `delayed` — so §2.5 is unreachable through
# check_eligibility. `_evaluate_item` is pure over dicts precisely so this
# branch can still be tested without inventing an order in orders.json (NFR-4).
_DELIVERED_FOOTWEAR = {
    "order_id": "TR-4525",
    "status": "delivered",
    "delivered_at": "2026-07-28T10:00:00Z",
    "payment_method": "credit_card",
    "items": [{
        "sku": "TR-SNK-017", "name": "Court Sneakers", "category": "footwear",
        "size": "42", "qty": 1, "price": 4499, "final_sale": False,
    }],
}


def test_damaged_socks_are_eligible_under_6_2_despite_2_3(frozen_clock):
    # TR-4522 delivered 2026-07-14T09:20Z; report it the next morning.
    frozen_clock(datetime(2026, 7, 15, 9, 0))
    verdict = check_eligibility("TR-4522", "TR-SOK-031", "damage_claim")
    assert verdict["eligible"] is True
    assert verdict["action_allowed"] == "replacement_or_refund"
    assert "6.2" in verdict["clause_ids"]
    # §2.3 is cited as overridden, not silently dropped (P4).
    assert "2.3" in verdict["clause_ids"]
    assert any("§6.2 covers non-returnable" in r for r in verdict["reasons"])
    # Trendly error, so §3.2 refunds the shipping fee.
    assert verdict["refund_route"]["shipping_fee_refunded"] is True


def test_damaged_jewellery_is_also_covered_by_6_2(frozen_clock):
    frozen_clock(datetime(2026, 7, 24, 9, 0))  # TR-4527 delivered 2026-07-23
    verdict = check_eligibility("TR-4527", "TR-EAR-042", "damage_claim")
    assert verdict["eligible"] is True
    assert "6.2" in verdict["clause_ids"]


def test_the_same_damage_claim_is_refused_once_48_hours_pass(reference_clock):
    verdict = check_eligibility("TR-4522", "TR-SOK-031", "damage_claim")
    assert verdict["eligible"] is False
    assert verdict["clause_ids"] == ["6.1"]
    assert any("human review" in caveat for caveat in verdict["caveats"])


def test_lost_parcel_still_escalates_even_as_a_damage_claim(reference_clock):
    verdict = check_eligibility("TR-4526", "TR-BAG-011", "damage_claim")
    assert verdict["action_allowed"] == "escalate"
    assert verdict["clause_ids"] == ["1.6"]


def test_cancelled_order_blocks_a_damage_claim_too(reference_clock):
    verdict = check_eligibility("TR-4529", "TR-SCF-027", "damage_claim")
    assert verdict["clause_ids"] == ["2.6"]


def test_colour_or_style_exchange_is_refused_under_4_1(reference_clock):
    verdict = check_eligibility("TR-4530", "TR-KRT-033", "exchange_other")
    assert verdict["eligible"] is False
    assert verdict["clause_ids"] == ["4.1"]


def test_size_exchange_on_a_final_sale_item_is_allowed(reference_clock):
    verdict = check_eligibility("TR-4528", "TR-SHR-009", "exchange_size")
    assert verdict["eligible"] is True
    assert verdict["action_allowed"] == "exchange_size"
    assert "2.4" in verdict["clause_ids"]
    # §4.3 would convert an unavailable size to a refund that §2.4 forbids —
    # flagged rather than resolved, since the policy genuinely conflicts here.
    assert any("§2.4 excludes" in r for r in verdict["reasons"])


def test_size_exchange_states_the_stock_rule_without_checking_stock(reference_clock):
    verdict = check_eligibility("TR-4530", "TR-KRT-033", "exchange_size")
    assert verdict["eligible"] is True
    assert "4.2" in verdict["clause_ids"]
    assert any("§4.3" in caveat for caveat in verdict["caveats"])
    assert verdict["refund_route"] is None  # an exchange is not a refund


def test_delivered_footwear_carries_the_shoe_box_caveat(reference_clock):
    verdict = eligibility._evaluate_item(
        _DELIVERED_FOOTWEAR, _DELIVERED_FOOTWEAR["items"][0], "return"
    )
    assert verdict["eligible"] is True
    assert "2.5" in verdict["clause_ids"]
    assert any("₹300" in caveat for caveat in verdict["caveats"])


def test_unknown_order_is_not_fuzzy_matched(reference_clock):
    result = check_eligibility("TR-9999")
    assert result["error"] == "order_not_found"
    assert "verdicts" not in result


def test_unknown_sku_reports_what_the_order_actually_contains(reference_clock):
    result = check_eligibility("TR-4530", "TR-NOPE-000")
    assert result["error"] == "sku_not_in_order"
    assert result["skus_in_order"] == ["TR-KRT-033"]


def test_unknown_intent_is_rejected(reference_clock):
    result = check_eligibility("TR-4530", None, "refund_everything")
    assert result["error"] == "unknown_intent"
    assert "return" in result["valid_intents"]
