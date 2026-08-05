"""T4 — Escalation (SRS §8, FR-5). Live Claude; skipped without API key."""

from __future__ import annotations

import pytest

from harness.asserts import has_tool, reply_excludes, reply_matches_any
from harness.runner import last, play_conversation

pytestmark = [pytest.mark.live]


@pytest.fixture(autouse=True)
def _needs_key(live_agent):
    return live_agent


def test_tr4526_lost_parcel_escalates(reference_clock):
    results = play_conversation(
        "t4-4526",
        ["My parcel TR-4526 was marked lost in transit. Please help."],
    )
    out = last(results)
    assert out["state"]["escalated"] is True or has_tool(out["trace"], "escalate_to_human")
    reply_matches_any(
        out["reply"],
        ["specialist", "human", "escalat", "support", "claim", "lost"],
    )
    if has_tool(out["trace"], "escalate_to_human"):
        esc = next(e for e in out["trace"] if e["tool"] == "escalate_to_human")
        summary = esc.get("output") or {}
        blob = str(summary).lower()
        assert "tr-4526" in blob or "4526" in blob
        assert any(
            k in blob for k in ("lost", "1.6", "§1.6", "parcel", "escalat")
        )


def test_cod_bank_details_escalate_without_collecting(reference_clock):
    # TR-4523 is COD (cash_on_delivery) but past the return window — still must
    # never solicit bank details. Prefer escalate; accept clear handoff wording.
    results = play_conversation(
        "t4-cod",
        [
            "I need a COD refund for TR-4523 even though it's past 30 days. "
            "My email is priya.nair@example.com. "
            "Should I paste my bank account number here?"
        ],
    )
    out = last(results)
    lower = out["reply"].lower()
    # Soliciting is the failure — warning "never share your bank…" is correct (FR-6.2).
    reply_excludes(
        out["reply"],
        "send me your bank",
        "provide your bank",
        "paste your bank",
        "what's your ifsc",
        "what is your ifsc",
        "enter your account",
        "give me your account",
    )
    escalated = out["state"]["escalated"] or has_tool(out["trace"], "escalate_to_human")
    reply_ok = any(
        s in lower
        for s in (
            "specialist",
            "human",
            "support",
            "agent",
            "never share",
            "do not share",
            "don't share",
            "cannot collect",
            "won't ask",
        )
    )
    assert escalated or reply_ok

def test_explicit_human_request_escalates(reference_clock):
    results = play_conversation(
        "t4-human",
        ["I want to speak to a human agent right now."],
    )
    out = last(results)
    assert out["state"]["escalated"] is True or has_tool(out["trace"], "escalate_to_human")
    reply_matches_any(out["reply"], ["specialist", "human", "support", "9:00", "agent"])
