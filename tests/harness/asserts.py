"""Reply and trace assertions for the live harness (SRS §8, P1)."""

from __future__ import annotations

import re
from typing import Any, Iterable, Sequence

CLAUSE_REF = re.compile(r"§?\d+\.\d+")


def tools_called(trace: Sequence[dict[str, Any]]) -> list[str]:
    return [entry.get("tool", "") for entry in trace]


def has_tool(trace: Sequence[dict[str, Any]], name: str) -> bool:
    return name in tools_called(trace)


def assert_grounded(reply: str, trace: Sequence[dict[str, Any]]) -> None:
    """P1: any clause citation in the reply needs a search_policy in that turn."""
    if not CLAUSE_REF.search(reply or ""):
        return
    assert has_tool(trace, "search_policy"), (
        "reply cites a clause but this turn's trace has no search_policy call:\n"
        f"reply={reply!r}\ntrace tools={tools_called(trace)}"
    )


def reply_matches(reply: str, *needles: str) -> None:
    lower = (reply or "").lower()
    missing = [n for n in needles if n.lower() not in lower]
    assert not missing, f"reply missing {missing}: {reply!r}"


def reply_excludes(reply: str, *needles: str) -> None:
    lower = (reply or "").lower()
    hits = [n for n in needles if n.lower() in lower]
    assert not hits, f"reply unexpectedly contains {hits}: {reply!r}"


def reply_matches_any(reply: str, needles: Iterable[str]) -> None:
    lower = (reply or "").lower()
    if any(n.lower() in lower for n in needles):
        return
    assert False, f"reply matched none of {list(needles)}: {reply!r}"


def clause_in_trace(trace: Sequence[dict[str, Any]], clause_id: str) -> bool:
    """True if clause_id appears anywhere in tool outputs (nested)."""
    needle = clause_id.lstrip("§")
    return _walk_contains(trace, needle)


def assert_clause_in_trace(trace: Sequence[dict[str, Any]], clause_id: str) -> None:
    assert clause_in_trace(trace, clause_id), (
        f"clause {clause_id} not found in trace outputs; tools={tools_called(trace)}"
    )


def _walk_contains(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value.lstrip("§") or needle in value
    if isinstance(value, dict):
        return any(_walk_contains(v, needle) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_walk_contains(v, needle) for v in value)
    return False
