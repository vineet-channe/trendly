"""Tool execution + session side effects for the ReAct loop (FR-5.1, FR-7).

`agent.py` calls `execute_tool` for every Claude `tool_use` block. Business
errors from app.tools.registry (`order_not_found`, `not_eligible`, …) are successful
results; only unknown tools and raised exceptions count toward the
consecutive-error auto-escalate threshold (FR-5.1).
"""

from __future__ import annotations

import json
from typing import Any

from app.tools.escalation import escalate_to_human
from app.session.state import AUTO_ESCALATE_ERROR_THRESHOLD, SessionState
from app.tools.registry import TOOL_REGISTRY

EXCHANGE_INTENTS = frozenset({"exchange_size", "exchange_other"})


def _apply_side_effects(
    name: str, tool_input: dict[str, Any], result: dict[str, Any], state: SessionState
) -> dict[str, Any]:
    """Update session state from a successful tool result; may replace
    `result` when a repeat-exchange must escalate instead (FR-5.1, §4.4).
    """
    if name == "lookup_order" and "error" not in result:
        order_id = result.get("order_id") or tool_input.get("order_id")
        if order_id:
            state.set_active_order(order_id)

    if name == "check_eligibility" and "error" not in result:
        state.record_eligibility_verdict(result)

    if name == "initiate_return" and result.get("initiated"):
        sku = tool_input.get("sku") or result.get("sku")
        intent = tool_input.get("intent", "return")
        if sku and intent in EXCHANGE_INTENTS:
            state.record_exchange(sku)

    if name == "escalate_to_human" and result.get("status") == "escalated":
        state.escalate()

    return result


def _auto_escalate(state: SessionState, detail: str) -> dict[str, Any]:
    """Hand off after repeated unrecoverable tool failures (FR-5.1)."""
    summary = escalate_to_human(
        reason="tool_errors",
        order_id=state.active_order_id,
        customer_id=state.verified_customer_id,
        customer_request="Assistant hit repeated tool failures mid-turn.",
        checks_performed=[detail],
        recommended_action="Retry the customer's request from the transcript.",
    )
    state.escalate()
    return summary


def execute_tool(
    name: str, tool_input: dict[str, Any], state: SessionState
) -> dict[str, Any]:
    """Run one tool, update session state, and handle FR-5.1 error counting."""
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        count = state.record_tool_error()
        err = {
            "error": "unknown_tool", "tool": name,
            "unrecoverable": True,
        }
        if count >= AUTO_ESCALATE_ERROR_THRESHOLD:
            return _auto_escalate(state, f"unknown_tool:{name}")
        return err

    # Repeat-exchange gate before calling the tool (FR-5.1, §4.4).
    if name == "initiate_return":
        sku = tool_input.get("sku")
        intent = tool_input.get("intent", "return")
        if sku and intent in EXCHANGE_INTENTS and state.has_exchanged(sku):
            result = escalate_to_human(
                reason="repeat_exchange",
                order_id=tool_input.get("order_id") or state.active_order_id,
                customer_id=state.verified_customer_id,
                customer_request=f"Second exchange on SKU {sku}",
                checks_performed=[f"has_exchanged({sku}) true"],
                recommended_action="Process per §4.4 one-exchange limit.",
            )
            state.record_tool_success()
            state.escalate()
            return result

    try:
        result = fn(**tool_input)
    except Exception as exc:  # noqa: BLE001 — surface to the model as tool_result
        count = state.record_tool_error()
        detail = f"{name}:{type(exc).__name__}:{exc}"
        if count >= AUTO_ESCALATE_ERROR_THRESHOLD:
            return _auto_escalate(state, detail)
        return {
            "error": "tool_exception", "tool": name,
            "detail": str(exc), "unrecoverable": True,
        }

    if not isinstance(result, dict):
        result = {"result": result}

    state.record_tool_success()
    return _apply_side_effects(name, tool_input, result, state)


def tool_result_content(result: dict[str, Any]) -> str:
    """Serialize a tool result for Anthropic `tool_result` content."""
    return json.dumps(result, default=str)
