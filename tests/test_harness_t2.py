"""T2 — Policy grounding (SRS §8, P1, P7). Live Claude; skipped without API key."""

from __future__ import annotations

import pytest

from harness.asserts import (
    assert_clause_in_trace,
    has_tool,
    reply_excludes,
    reply_matches_any,
)
from harness.runner import last, play_conversation

pytestmark = [pytest.mark.live]


@pytest.fixture(autouse=True)
def _needs_key(live_agent):
    return live_agent


def test_jewellery_question_cites_2_3_via_search_policy(reference_clock):
    results = play_conversation(
        "t2-jewellery",
        ["Can I return jewellery I bought from Trendly?"],
    )
    out = last(results)
    assert has_tool(out["trace"], "search_policy")
    assert_clause_in_trace(out["trace"], "2.3")
    reply_matches_any(out["reply"], ["2.3", "§2.3", "jewellery", "jewelry", "non-return"])


def test_paraphrased_refund_question_does_not_false_not_covered(reference_clock):
    """P7: keyword-miss paraphrase must not produce a false 'not covered'."""
    results = play_conversation(
        "t2-paraphrase",
        ["According to Trendly policy, can I get my money back on a return?"],
    )
    out = last(results)
    assert has_tool(out["trace"], "search_policy")
    lower = out["reply"].lower()
    false_silence = (
        ("not covered" in lower or "doesn't cover" in lower or "does not cover" in lower)
        and "refund" not in lower
        and "return" not in lower
    )
    assert not false_silence, f"false policy silence on refund paraphrase: {out['reply']!r}"
    reply_matches_any(
        out["reply"],
        ["refund", "return", "money", "§3", "3.1", "inspection", "eligible"],
    )


def test_off_topic_policy_silence_offers_human(reference_clock):
    results = play_conversation(
        "t2-silent",
        ["Does Trendly offer crypto payment plans for international shipping tariffs?"],
    )
    out = last(results)
    reply_matches_any(
        out["reply"],
        [
            "don't cover",
            "does not cover",
            "doesn't cover",
            "not cover",
            "does not offer",
            "doesn't offer",
            "do not offer",
            "not in the policy",
            "policy doesn't",
            "no mention",
            "specialist",
            "human",
            "support",
            "agent",
        ],
    )
    # Must not invent a fake clause number for this topic.
    reply_excludes(out["reply"], "§9.", "§10.", "clause 9", "clause 10")
