"""T6 — Robustness (SRS §8). Thin coverage; live Claude; skipped without API key."""

from __future__ import annotations

import pytest

from harness.asserts import reply_matches_any
from harness.runner import last, play_conversation

pytestmark = [pytest.mark.live]


@pytest.fixture(autouse=True)
def _needs_key(live_agent):
    return live_agent


def test_malformed_order_id(reference_clock):
    results = play_conversation(
        "t6-malformed",
        ["Where is order banana-42?"],
    )
    out = last(results)
    reply_matches_any(
        out["reply"],
        ["not found", "couldn't find", "could not find", "don't recognize", "invalid", "format"],
    )


def test_mid_conversation_order_switch_updates_active(reference_clock):
    results = play_conversation(
        "t6-switch",
        [
            "Where is TR-4530?",
            "Actually, check TR-4525 instead — what's going on with that one?",
        ],
    )
    out = last(results)
    assert out["state"]["active_order"] == "TR-4525"
    reply_matches_any(out["reply"], ["delay", "credit", "250", "sorry", "late", "TR-4525"])
