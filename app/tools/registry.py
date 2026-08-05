"""Tool dispatch layer for the Claude tool-use loop (SRS §3.1, Phase 4).

Three read-only wrappers (`lookup_order`, `search_policy`,
`check_eligibility`) plus `TOOL_SCHEMAS` and `TOOL_REGISTRY` — this is the
only module `agent.py` (Phase 5) should import tool behaviour from. The
three state-changing tools live in `tool_actions.py` (`initiate_return`)
and `escalation_actions.py` (`issue_delay_credit`, `escalate_to_human`),
and are re-exported here so callers never need to know about the split.

Adding a tool touches this file (or one of the two action files), one of
the two schema files, and `prompts.py` — more than NFR-7's "two-file"
claim, because staying under CURSOR_INSTRUCTIONS.md §4's ~150-line cap
required splitting schema data from implementation, and read-only tools
from state-changing ones (twice over, since the three actions alone still
exceeded the cap in one file). Same precedent as the
`policy_index`/`policy_search` and `eligibility`'s five-way split; see
DEV_LOG.md for the full deviation note.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.tools.action_schemas import ACTION_TOOL_SCHEMAS
from app.eligibility.engine import check_eligibility as _check_eligibility
from app.tools.escalation import escalate_to_human, issue_delay_credit
from app.orders.store import get_order
from app.policy.search import search_policy as _search_policy
from app.tools.actions import initiate_return
from app.tools.schemas import READ_TOOL_SCHEMAS
from app.tools.verify import verify_customer

__all__ = [
    "TOOL_SCHEMAS", "TOOL_REGISTRY", "lookup_order", "search_policy",
    "check_eligibility", "initiate_return", "issue_delay_credit",
    "escalate_to_human", "verify_customer",
]

# The single list `agent.py` (Phase 5) passes to the Anthropic SDK's
# tool-use parameter.
TOOL_SCHEMAS: list[dict[str, Any]] = [*READ_TOOL_SCHEMAS, *ACTION_TOOL_SCHEMAS]


def lookup_order(order_id: str) -> dict[str, Any]:
    """Look up an order by exact ID (FR-1.1). Unknown IDs get a clean
    not-found result, never a fuzzy match (FR-1.3); `null` fields pass
    through untouched rather than being invented (FR-6.6).
    """
    order = get_order(order_id)
    if order is None:
        return {"error": "order_not_found", "order_id": order_id}
    return order


def search_policy(query: str, top_k: int = 5) -> dict[str, Any]:
    """Keyword search over policy clauses (FR-3.1, FR-3.3, P1, P7). Every
    policy claim in a reply must originate here — see `policy_search.py`
    for the weak-match/index-fallback behaviour.
    """
    return _search_policy(query, top_k=top_k)


def check_eligibility(
    order_id: str, sku: Optional[str] = None, intent: str = "return"
) -> dict[str, Any]:
    """Compute return/exchange/damage-claim eligibility in code, never in
    the prompt (FR-4, P2). `sku=None` returns one verdict per line item —
    the only correct shape for a mixed order (P3, FR-4.1).
    """
    return _check_eligibility(order_id, sku=sku, intent=intent)


# What `agent.py` dispatches a Claude tool-use call through, keyed by the
# same `name` each schema in `TOOL_SCHEMAS` declares.
TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "lookup_order": lookup_order,
    "search_policy": search_policy,
    "check_eligibility": check_eligibility,
    "verify_customer": verify_customer,
    "initiate_return": initiate_return,
    "issue_delay_credit": issue_delay_credit,
    "escalate_to_human": escalate_to_human,
}
