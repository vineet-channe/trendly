"""T1 — Order lookup & context (SRS §8). Live Claude; skipped without API key."""

from __future__ import annotations

import pytest

from harness.asserts import has_tool, reply_excludes, reply_matches, reply_matches_any
from harness.runner import last, play_conversation

ALL_ORDERS = [
    "TR-4521",
    "TR-4522",
    "TR-4523",
    "TR-4524",
    "TR-4525",
    "TR-4526",
    "TR-4527",
    "TR-4528",
    "TR-4529",
    "TR-4530",
]

pytestmark = [pytest.mark.live]


@pytest.fixture(autouse=True)
def _needs_key(live_agent):
    return live_agent


def test_all_ten_orders_answer_on_order_id_alone(reference_clock):
    for order_id in ALL_ORDERS:
        results = play_conversation(
            f"t1-status-{order_id}",
            [f"Where is my order {order_id}?"],
        )
        out = last(results)
        if order_id == "TR-4526":
            # Lost parcel must escalate (FR-1.6); handoff may omit a long status.
            assert out["state"]["escalated"] is True or has_tool(
                out["trace"], "escalate_to_human"
            )
            reply_matches_any(out["reply"], ["specialist", "lost", "TR-4526", "support"])
            continue
        assert has_tool(out["trace"], "lookup_order")
        assert out["state"]["active_order"] == order_id
        # Reply may omit repeating the ID after lookup; require ID or status signal.
        if order_id not in out["reply"]:
            reply_matches_any(
                out["reply"],
                [
                    "transit", "deliver", "delay", "ship", "cancel", "track",
                    "backorder", "lost", "credit", "return", "expect",
                ],
            )


def test_unknown_order_id_is_not_fuzzy_matched(reference_clock):
    results = play_conversation(
        "t1-unknown",
        ["Where is order TR-9999?"],
    )
    out = last(results)
    reply_matches_any(
        out["reply"],
        ["not found", "couldn't find", "could not find", "no order", "don't have"],
    )
    reply_excludes(out["reply"], "TR-4521", "TR-4530")


def test_tr4521_is_not_reported_as_delayed_and_no_credit(reference_clock):
    results = play_conversation(
        "t1-4521-delay",
        ["Where is TR-4521? Is it delayed?"],
    )
    out = last(results)
    reply_matches(out["reply"], "TR-4521")
    lower = out["reply"].lower()
    # Must not treat 2 business days past expected as delayed (FR-1.8).
    if "not delayed" not in lower and "isn't delayed" not in lower:
        reply_excludes(out["reply"], "is delayed", "has been delayed", "order is delayed")
    # Must not offer/issue the credit (mentioning the rule while refusing is ok).
    reply_excludes(
        out["reply"],
        "issued you",
        "i've added",
        "i have added",
        "credited ₹250",
        "here's your ₹250",
        "offering you ₹250",
        "offer you ₹250",
    )
    issued = [
        e
        for e in out["trace"]
        if e.get("tool") == "issue_delay_credit" and e.get("output", {}).get("issued") is True
    ]
    assert not issued



def test_pronoun_followup_keeps_active_order(reference_clock):
    results = play_conversation(
        "t1-pronoun",
        [
            "Where is TR-4521?",
            "When will it arrive?",
        ],
    )
    assert last(results)["state"]["active_order"] == "TR-4521"
    reply_matches_any(
        last(results)["reply"],
        ["arriv", "expect", "deliver", "transit", "eta", "august", "july"],
    )
    # Second turn should not re-ask for the order id as if unknown.
    reply_excludes(last(results)["reply"], "which order", "order id", "order number")
