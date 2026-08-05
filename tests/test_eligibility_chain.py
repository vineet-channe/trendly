"""Phase 2 tests for the §4.4 chain across all 10 orders (FR-4, FR-4.1, FR-4.2).

Every assertion checks the *reason* — the clause the verdict is grounded in —
not just the true/false. A refusal with the right verdict and the wrong clause
is still a wrong answer to the customer: TR-4527 is refused because jewellery
is non-returnable (§2.3), and telling that customer their 30 days ran out
(§2.1) would be a fabrication they could check against the policy.

Clock frozen at 2026-08-04 (SRS §4.1) via the `reference_clock` fixture.
"""

import order_store
import policy_index
from eligibility import check_eligibility


def _one(order_id, sku=None, intent="return"):
    """The single verdict for a one-item order, unwrapped from the order-level
    envelope so the assertions below stay readable.
    """
    result = check_eligibility(order_id, sku, intent)
    if "verdicts" in result:
        assert len(result["verdicts"]) == 1
        return result["verdicts"][0]
    return result


def test_tr4521_in_transit_window_has_not_started(reference_clock):
    verdict = _one("TR-4521")
    assert verdict["eligible"] is False
    assert verdict["clause_ids"] == ["2.1"]
    assert "in_transit" in verdict["reasons"][0]
    assert "has not started" in verdict["reasons"][0]


def test_tr4522_returns_two_separate_per_sku_verdicts(reference_clock):
    result = check_eligibility("TR-4522")
    verdicts = {v["sku"]: v for v in result["verdicts"]}
    assert set(verdicts) == {"TR-TSH-002", "TR-SOK-031"}

    tee = verdicts["TR-TSH-002"]
    assert tee["eligible"] is True
    assert tee["action_allowed"] == "return"

    socks = verdicts["TR-SOK-031"]
    assert socks["eligible"] is False
    assert socks["clause_ids"] == ["2.3"]
    # 21 days in, so the date is not the problem — the category is (FR-4.2).
    assert "2.1" not in socks["clause_ids"]


def test_tr4523_refused_on_the_date(reference_clock):
    verdict = _one("TR-4523")
    assert verdict["eligible"] is False
    assert verdict["clause_ids"] == ["2.1"]
    assert "60 calendar days" in verdict["reasons"][0]


def test_tr4524_partially_shipped_blocks_every_item(reference_clock):
    result = check_eligibility("TR-4524")
    assert len(result["verdicts"]) == 2
    for verdict in result["verdicts"]:
        assert verdict["eligible"] is False
        assert verdict["clause_ids"] == ["2.1"]
        assert "partially_shipped" in verdict["reasons"][0]


def test_tr4525_delayed_is_a_window_not_a_lost_parcel(reference_clock):
    verdict = _one("TR-4525")
    assert verdict["eligible"] is False
    assert verdict["clause_ids"] == ["2.1"]
    # Delayed is not lost: §1.6 must not leak into a delay verdict.
    assert "1.6" not in verdict["clause_ids"]


def test_tr4526_escalates_under_1_6_rather_than_giving_a_window_verdict(reference_clock):
    verdict = _one("TR-4526")
    assert verdict["eligible"] is False
    assert verdict["action_allowed"] == "escalate"
    assert verdict["clause_ids"] == ["1.6"]
    assert "lost-parcel claim" in verdict["reasons"][0]


def test_tr4527_refused_on_category_not_date(reference_clock):
    verdict = _one("TR-4527")
    assert verdict["eligible"] is False
    assert verdict["clause_ids"] == ["2.3"]
    assert "2.1" not in verdict["clause_ids"]
    assert "jewellery" in verdict["reasons"][0]
    # P7-adjacent: the refusal points at the §6.2 route rather than dead-ending.
    assert any("6.2" in caveat for caveat in verdict["caveats"])


def test_tr4528_final_sale_is_exchange_only(reference_clock):
    verdict = _one("TR-4528")
    assert verdict["eligible"] is False
    assert verdict["action_allowed"] == "exchange_size"
    assert verdict["clause_ids"] == ["2.4"]
    assert verdict["refund_route"] is None


def test_tr4529_cancelled_order_cannot_be_returned(reference_clock):
    verdict = _one("TR-4529")
    assert verdict["eligible"] is False
    assert verdict["clause_ids"] == ["2.6"]
    assert any("processed" in caveat for caveat in verdict["caveats"])


def test_tr4530_happy_path_is_eligible_with_a_card_refund(reference_clock):
    verdict = _one("TR-4530")
    assert verdict["eligible"] is True
    assert verdict["action_allowed"] == "return"
    assert verdict["clause_ids"] == ["2.1", "2.2"]
    assert "9 calendar days" in verdict["reasons"][0]
    route = verdict["refund_route"]
    assert route["destination"] == "Original card"
    assert route["timeline"] == "5-7 business days"


def test_every_order_yields_one_verdict_per_line_item(reference_clock):
    for order in order_store.list_orders():
        result = check_eligibility(order["order_id"])
        assert len(result["verdicts"]) == len(order["items"]), order["order_id"]


def test_no_verdict_cites_a_clause_that_is_not_in_the_policy(reference_clock):
    """Guards against a plausible-looking clause ID being invented in code —
    the same failure P1 guards against in the model's output.
    """
    for order in order_store.list_orders():
        for intent in ("return", "exchange_size", "exchange_other", "damage_claim"):
            for verdict in check_eligibility(order["order_id"], intent=intent)["verdicts"]:
                for clause_id in verdict["clause_ids"]:
                    assert policy_index.get_clause(clause_id) is not None, clause_id
