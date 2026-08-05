"""Claude tool-use JSON schemas for the three read-only tools (Phase 4).

Pure data — no logic, no imports from the implementation modules — so the
schema Claude sees can never silently drift from what `tools.py` actually
does; a mismatch has to be caught by reading this file, not by tracing
control flow.

The three state-changing tool schemas (`initiate_return`,
`issue_delay_credit`, `escalate_to_human`) live in `action_tool_schemas.py`
— a single 6-schema file ran to ~184 lines, over CURSOR_INSTRUCTIONS.md
§4's ~150-line cap, so it's split the same way the implementations are
(read-only vs state-changing). `tools.py` combines both into the single
`TOOL_SCHEMAS` list `agent.py` (Phase 5) passes to the Anthropic SDK; see
DEV_LOG.md for the full NFR-7 deviation note.
"""

from __future__ import annotations

from typing import Any

READ_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "lookup_order",
        "description": (
            "Look up one order by its exact order ID (FR-1.1). Returns status, "
            "items, dates, carrier, tracking, and payment method. An unknown "
            "order ID returns a clean not-found result rather than a fuzzy "
            "match (FR-1.3); any field that is null in the source data must be "
            "reported as unavailable, never invented (FR-6.6)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Exact order ID, e.g. 'TR-4530'.",
                }
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "search_policy",
        "description": (
            "Search the Trendly shipping/returns policy by keyword (FR-3.1). "
            "Every policy claim made to a customer must be grounded in a "
            "result from this tool, with its clause ID(s) cited (FR-3.2). If "
            "the match is weak, the response also includes the full clause "
            "index so a follow-up call by clause ID can confirm the policy is "
            "genuinely silent before saying so (P7, FR-3.3)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language policy question or keywords.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of matching clauses to return (default 5).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_eligibility",
        "description": (
            "Compute return/exchange/damage-claim eligibility for an order, "
            "purely in code (FR-4, P2). Omitting `sku` returns one verdict "
            "per line item, required for mixed orders (P3, FR-4.1) — never "
            "collapse a mixed order into one verdict. Each verdict carries "
            "the exact clause IDs and reasons behind it (FR-4.2, P4); never "
            "restate or soften the reason yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Exact order ID."},
                "sku": {
                    "type": "string",
                    "description": "Specific line-item SKU. Omit to get every item's verdict.",
                },
                "intent": {
                    "type": "string",
                    "enum": ["return", "exchange_size", "exchange_other", "damage_claim"],
                    "description": "What the customer wants to do with the item.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "verify_customer",
        "description": (
            "Verify the caller's identity with the email or phone on their "
            "account before Tier-1 disclosure or state-changing actions "
            "(FR-2.2). Call this before initiate_return, issue_delay_credit, "
            "or stating customer name/email/phone. Optional order_id also "
            "checks that the contact owns that order. Failures never reveal "
            "who owns an order (FR-2.3, FR-2.5)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Email address to match against the customer record.",
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number to match against the customer record.",
                },
                "order_id": {
                    "type": "string",
                    "description": "Optional order ID — contact must own this order.",
                },
            },
            "required": [],
        },
    },
]
