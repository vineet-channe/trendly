"""Drive multi-turn live conversations via run_turn (SRS §8)."""

from __future__ import annotations

from typing import Any, Sequence

from app.agent.loop import run_turn
from app.session.store import reset_all_sessions
from harness.asserts import assert_grounded

TurnResult = dict[str, Any]


def play_conversation(
    session_id: str,
    turns: Sequence[str],
    *,
    reset: bool = True,
    check_grounding: bool = True,
) -> list[TurnResult]:
    """Run each user message through the live agent; assert P1 per turn."""
    if reset:
        reset_all_sessions()
    results: list[TurnResult] = []
    for message in turns:
        out = run_turn(session_id, message)
        if check_grounding:
            assert_grounded(out.get("reply", ""), out.get("trace") or [])
        results.append(out)
    return results


def last(results: Sequence[TurnResult]) -> TurnResult:
    assert results, "expected at least one turn result"
    return results[-1]
