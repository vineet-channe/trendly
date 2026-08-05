"""T3 — Returns eligibility (SRS §8, FR-4). Live Claude; skipped without API key."""

from __future__ import annotations

from datetime import datetime

import pytest

from harness.asserts import (
    assert_clause_in_trace,
    has_tool,
    reply_matches,
    reply_matches_any,
)
from harness.runner import last, play_conversation

pytestmark = [pytest.mark.live]


@pytest.fixture(autouse=True)
def _needs_key(live_agent):
    return live_agent


def test_tr4530_happy_path_eligible(reference_clock):
    results = play_conversation(
        "t3-4530",
        [
            "I want to return the Block-Print Kurta on TR-4530. "
            "My email is marcus.bell@example.com. "
            "Please search the return policy, check eligibility, and tell me "
            "if it qualifies — cite the clause IDs."
        ],
    )
    out = last(results)
    assert has_tool(out["trace"], "check_eligibility")
    assert has_tool(out["trace"], "search_policy")
    reply_matches_any(out["reply"], ["eligible", "return", "pickup", "rma", "window"])


def test_tr4523_refused_on_date_2_1(reference_clock):
    results = play_conversation(
        "t3-4523",
        ["Can I return order TR-4523?"],
    )
    out = last(results)
    assert has_tool(out["trace"], "check_eligibility")
    assert_clause_in_trace(out["trace"], "2.1")
    reply_matches_any(out["reply"], ["2.1", "§2.1", "30 day", "30-day", "window"])


def test_tr4527_refused_on_category_2_3_not_date(reference_clock):
    results = play_conversation(
        "t3-4527",
        ["Can I return the jewellery in TR-4527?"],
    )
    out = last(results)
    assert has_tool(out["trace"], "check_eligibility")
    assert_clause_in_trace(out["trace"], "2.3")
    reply_matches_any(out["reply"], ["2.3", "§2.3", "categor", "jewellery", "jewelry"])
    # Correct reason is category, not the 30-day window.
    lower = out["reply"].lower()
    if "2.1" in lower or "§2.1" in lower:
        assert "2.3" in lower or "§2.3" in lower


def test_tr4528_final_sale_exchange_only(reference_clock):
    results = play_conversation(
        "t3-4528",
        ["Can I get a refund for TR-4528?"],
    )
    out = last(results)
    reply_matches_any(
        out["reply"],
        ["final sale", "exchange", "size", "2.4", "§2.4", "no refund"],
    )


def test_tr4522_per_item_split(reference_clock):
    results = play_conversation(
        "t3-4522",
        ["Can I return everything in TR-4522?"],
    )
    out = last(results)
    assert has_tool(out["trace"], "check_eligibility")
    reply_matches_any(out["reply"], ["tee", "sock", "item", "separat", "apparel"])
    reply_matches_any(out["reply"], ["2.3", "§2.3", "innerwear", "eligible", "return"])


def test_tr4529_cancelled_cannot_return(reference_clock):
    results = play_conversation(
        "t3-4529",
        ["I want to return TR-4529."],
    )
    out = last(results)
    reply_matches_any(out["reply"], ["cancel", "2.6", "§2.6", "refund"])


def test_tr4521_return_window_not_started(reference_clock):
    results = play_conversation(
        "t3-4521-return",
        ["Can I return TR-4521?"],
    )
    out = last(results)
    reply_matches_any(
        out["reply"],
        ["not delivered", "in transit", "hasn't been delivered", "window", "deliver"],
    )


def test_damaged_socks_eligible_under_6_2(frozen_clock):
    """Within 48h of TR-4522 delivery, damage overrides §2.3 (FR-4.6 / §6.2)."""
    frozen_clock(datetime(2026, 7, 14, 12, 0, 0))
    results = play_conversation(
        "t3-damage-socks",
        [
            "The ankle socks in TR-4522 arrived damaged. "
            "SKU TR-SOK-031. Can I get a replacement or refund under the damage policy?"
        ],
    )
    out = last(results)
    assert has_tool(out["trace"], "check_eligibility")
    assert_clause_in_trace(out["trace"], "6.2")
    reply_matches_any(out["reply"], ["6.2", "§6.2", "eligible", "damage", "replace"])
