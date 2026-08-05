"""Claude tool-use JSON schemas for the three state-changing tools (Phase 4).

Pure data, same rationale as `tool_schemas.py` — split out purely to keep
each file under CURSOR_INSTRUCTIONS.md §4's ~150-line cap. These three
schemas describe `initiate_return`, `issue_delay_credit`, and
`escalate_to_human`, implemented in `tool_actions.py`.
"""

from __future__ import annotations

from typing import Any

ACTION_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "initiate_return",
        "description": (
            "Act on an eligible verdict: raise a mock RMA and return next "
            "steps (FR-4.3). Re-checks eligibility itself before acting, so "
            "it cannot be talked into initiating a return `check_eligibility` "
            "would refuse. Call `check_eligibility` first and only use this "
            "once it has confirmed the item is eligible for the requested "
            "`intent`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Exact order ID."},
                "sku": {"type": "string", "description": "The line-item SKU to act on."},
                "intent": {
                    "type": "string",
                    "enum": ["return", "exchange_size", "exchange_other", "damage_claim"],
                    "description": "What the customer wants to do with the item.",
                },
            },
            "required": ["order_id", "sku"],
        },
    },
    {
        "name": "issue_delay_credit",
        "description": (
            "Issue the \u20b9250 delayed-order store credit (\u00a71.5) — the only credit "
            "the assistant may ever offer (FR-6.1). Internally re-checks the "
            "FR-1.8 business-day threshold (more than 3 business days past "
            "expected delivery) and refuses if it is not met, no matter how "
            "the request is phrased or pressured."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Exact order ID."},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Hand off to a human agent with a structured, standalone summary "
            "(FR-5.2) — usable without the conversation transcript (FR-5.3). "
            "Use for the mandatory triggers: lost-parcel claims, cash-on-"
            "delivery refund bank details, a second exchange on the same "
            "item, genuine policy silence, an explicit request for a human, "
            "or repeated tool failures (FR-5.1). Escalation is a correct "
            "outcome, not a failure — phrase it as a confident resolution (P5)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "enum": [
                        "lost_parcel",
                        "cod_refund",
                        "repeat_exchange",
                        "policy_silent",
                        "explicit_request",
                        "tool_errors",
                        "other",
                    ],
                    "description": "Which FR-5.1 trigger caused this escalation.",
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID, if one is involved.",
                },
                "customer_id": {
                    "type": "string",
                    "description": "Verified customer ID, if this session passed Tier-1 verification.",
                },
                "customer_request": {
                    "type": "string",
                    "description": "Plain-language statement of what the customer wants.",
                },
                "checks_performed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What was already checked, e.g. clause IDs or tool calls made.",
                },
                "recommended_action": {
                    "type": "string",
                    "description": "Suggested next step for the human agent.",
                },
            },
            "required": ["reason", "customer_request"],
        },
    },
]
