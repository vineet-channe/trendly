"""ReAct agent loop with Claude tool-use (NFR-2, FR-5.1, P1).

Hand-written loop — no agent framework. Caps tool rounds at
`config.MAX_TOOL_STEPS`. Auto-escalation on repeated tool failures lives in
`agent_dispatch.py`; this module owns the model round-trips and the public
`run_turn` API that Phase 7's `/chat` will call.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import anthropic

from app.agent.dispatch import execute_tool, tool_result_content
from app.config import MAX_TOOL_STEPS, MODEL_NAME, TEMPERATURE
from app.tools.escalation import SUPPORT_HOURS_NOTE
from app.agent.prompts import build_system_prompt
from app.session.store import get_session
from app.session.state import SessionState
from app.tools.registry import TOOL_SCHEMAS

_ESCALATED_REPLY = (
    "Your request is already with a specialist. "
    f"{SUPPORT_HOURS_NOTE}"
)


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _text_from_content(content: list[Any]) -> str:
    parts = []
    for block in content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _state_snapshot(state: SessionState) -> dict[str, Any]:
    return {
        "verified": state.is_verified(),
        "active_order": state.active_order_id,
        "escalated": state.escalated,
    }


def _run_tools(
    content: list[Any], state: SessionState, trace: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Execute every tool_use block; return Anthropic tool_result blocks."""
    results: list[dict[str, Any]] = []
    for block in content:
        if getattr(block, "type", None) != "tool_use":
            continue
        name = block.name
        tool_input = dict(block.input or {})
        output = execute_tool(name, tool_input, state)
        trace.append({"tool": name, "input": tool_input, "output": output})
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": tool_result_content(output),
        })
    return results


def run_turn(
    session_id: str,
    user_message: str,
    *,
    client: Optional[anthropic.Anthropic] = None,
) -> dict[str, Any]:
    """One user turn: ReAct until a text reply, step cap, or escalation.

    `client` is injectable for tests (mock the Anthropic SDK without network).
    """
    state = get_session(session_id)
    if state.escalated:
        return {
            "reply": _ESCALATED_REPLY,
            "trace": [],
            "state": _state_snapshot(state),
        }

    state.add_message("user", user_message)
    messages: list[dict[str, Any]] = list(state.messages)
    trace: list[dict[str, Any]] = []
    api = client or _client()
    system = build_system_prompt()
    reply = ""

    for _step in range(MAX_TOOL_STEPS):
        if state.escalated:
            reply = _ESCALATED_REPLY
            break

        response = api.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            temperature=TEMPERATURE,
            system=system,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        content = list(response.content)
        tool_results = _run_tools(content, state, trace)

        if tool_results:
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": tool_results})
            if state.escalated:
                last = trace[-1]["output"] if trace else {}
                reply = last.get("message") or _ESCALATED_REPLY
                if last.get("support_hours"):
                    reply = f"{reply} {last['support_hours']}"
                break
            continue

        reply = _text_from_content(content)
        break
    else:
        # Step cap reached while tools were still in flight (NFR-2).
        response = api.messages.create(
            model=MODEL_NAME, max_tokens=1024, temperature=TEMPERATURE,
            system=system + (
                "\n\nMaximum tool steps used. Answer from what you have; "
                "do not call tools."
            ),
            messages=messages,
        )
        reply = _text_from_content(list(response.content)) or (
            "I need a specialist for that. " + SUPPORT_HOURS_NOTE
        )

    if reply:
        state.add_message("assistant", reply)

    return {
        "reply": reply,
        "trace": trace,
        "state": _state_snapshot(state),
    }
