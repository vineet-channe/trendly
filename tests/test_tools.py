"""Tool-layer tests (Phase 4 "Done when"): every tool callable directly, no
LLM in the loop, with a valid and an invalid input each.

Uses the shared `reference_clock` fixture (2026-08-04) from `conftest.py` so
delay/eligibility results match the SRS §4.1 status matrix.
"""

import app.tools.registry as tools


def test_lookup_order_valid():
    order = tools.lookup_order("TR-4530")
    assert order["status"] == "delivered"
    assert order["customer_id"] == "C-101"


def test_lookup_order_unknown_id_is_clean_not_found():
    result = tools.lookup_order("TR-9999")
    assert result == {"error": "order_not_found", "order_id": "TR-9999"}


def test_lookup_order_null_fields_pass_through_unfilled():
    # TR-4529 is cancelled: carrier/tracking/expected_delivery are null.
    order = tools.lookup_order("TR-4529")
    assert order["carrier"] is None
    assert order["expected_delivery"] is None


def test_search_policy_delegates_to_policy_search():
    result = tools.search_policy("jewellery")
    assert result["results"][0]["id"] == "2.3"
    assert result["weak_match"] is False


def test_search_policy_weak_match_returns_full_index():
    result = tools.search_policy("xyzzy_no_such_word")
    assert result["weak_match"] is True
    assert "full_index" in result


def test_check_eligibility_delegates_and_splits_mixed_orders(reference_clock):
    result = tools.check_eligibility("TR-4522")
    assert result["order_id"] == "TR-4522"
    assert len(result["verdicts"]) == 2


def test_check_eligibility_unknown_order():
    result = tools.check_eligibility("TR-9999")
    assert result == {"error": "order_not_found", "order_id": "TR-9999"}


def test_initiate_return_happy_path(reference_clock):
    result = tools.initiate_return("TR-4530", "TR-KRT-033", "return")
    assert result["initiated"] is True
    assert result["action"] == "return"
    assert result["rma_reference"].startswith("RMA-")
    assert result["refund_route"]["destination"] == "Original card"


def test_initiate_return_is_deterministic(reference_clock):
    first = tools.initiate_return("TR-4530", "TR-KRT-033", "return")
    second = tools.initiate_return("TR-4530", "TR-KRT-033", "return")
    assert first["rma_reference"] == second["rma_reference"]


def test_initiate_return_refuses_non_returnable_category(reference_clock):
    result = tools.initiate_return("TR-4527", "TR-EAR-042", "return")
    assert result["initiated"] is False
    assert result["error"] == "not_eligible"
    assert result["clause_ids"] == ["2.3"]


def test_initiate_return_final_sale_return_refused_by_eligibility(reference_clock):
    # The eligibility chain itself already marks final-sale + intent=return as
    # ineligible (clause 2.4, action_allowed="exchange_size"), so this surfaces
    # as "not_eligible" rather than reaching initiate_return's own
    # action-mismatch guard -- that guard exists for a case eligibility.py's
    # current chain doesn't actually produce (see DEV_LOG.md).
    result = tools.initiate_return("TR-4528", "TR-SHR-009", "return")
    assert result["initiated"] is False
    assert result["error"] == "not_eligible"
    assert result["action_allowed"] == "exchange_size"


def test_initiate_return_final_sale_exchange_size_succeeds(reference_clock):
    result = tools.initiate_return("TR-4528", "TR-SHR-009", "exchange_size")
    assert result["initiated"] is True
    assert result["action"] == "exchange_size"
    assert result["refund_route"] is None


def test_initiate_return_unknown_order():
    result = tools.initiate_return("TR-9999", "SKU-1")
    assert result == {"error": "order_not_found", "order_id": "TR-9999"}


def test_initiate_return_unknown_sku(reference_clock):
    result = tools.initiate_return("TR-4530", "NOT-A-SKU")
    assert result["error"] == "sku_not_in_order"


def test_issue_delay_credit_refuses_below_threshold(reference_clock):
    # TR-4521 is 2 business days past expected -- the build plan's named
    # example: the credit must not be issuable on request alone.
    result = tools.issue_delay_credit("TR-4521")
    assert result["issued"] is False
    assert result["error"] == "threshold_not_met"
    assert result["business_days_past_expected"] == 2


def test_issue_delay_credit_issues_above_threshold(reference_clock):
    # TR-4525 is 14 business days past expected.
    result = tools.issue_delay_credit("TR-4525")
    assert result["issued"] is True
    assert result["amount_inr"] == 250
    assert result["clause_ids"] == ["1.5"]


def test_issue_delay_credit_unknown_order():
    result = tools.issue_delay_credit("TR-9999")
    assert result == {"error": "order_not_found", "order_id": "TR-9999"}


def test_issue_delay_credit_missing_expected_delivery_is_not_delayed():
    # TR-4529 is cancelled; expected_delivery is null.
    result = tools.issue_delay_credit("TR-4529")
    assert result["issued"] is False
    assert result["business_days_past_expected"] is None


def test_escalate_to_human_lost_parcel_is_standalone():
    result = tools.escalate_to_human(
        "lost_parcel",
        order_id="TR-4526",
        customer_id="C-101",
        customer_request="Carrier marked my parcel lost, where is it?",
        checks_performed=["order status: lost_in_transit (\u00a71.6)"],
        recommended_action="Process replacement or refund per \u00a71.6 within 5 business days.",
    )
    assert result["status"] == "escalated"
    assert result["order"]["status"] == "lost_in_transit"
    assert result["customer_name"] == "Marcus Bell"
    assert "IST" in result["support_hours"]


def test_escalate_to_human_works_with_no_order_or_customer():
    result = tools.escalate_to_human(
        "explicit_request", customer_request="I want to talk to a human"
    )
    assert result["status"] == "escalated"
    assert result["order"] is None
    assert result["customer_name"] is None
    assert result["ticket_reference"].startswith("ESC-")


def test_escalate_to_human_unknown_reason_falls_back_to_other():
    result = tools.escalate_to_human("not_a_real_trigger", customer_request="help")
    assert result["reason"] == "other"


def test_tool_registry_and_schemas_stay_in_sync():
    schema_names = {schema["name"] for schema in tools.TOOL_SCHEMAS}
    assert schema_names == set(tools.TOOL_REGISTRY.keys())
