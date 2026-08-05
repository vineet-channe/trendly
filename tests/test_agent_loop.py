"""Agent loop + dispatch tests (Phase 5) — mocked Anthropic client, no network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.agent.loop import run_turn
from app.agent.dispatch import execute_tool
from app.config import MAX_TOOL_STEPS
from app.session.store import get_session, reset_all_sessions
from app.session.state import AUTO_ESCALATE_ERROR_THRESHOLD


@pytest.fixture(autouse=True)
def _clean_sessions():
    reset_all_sessions()
    yield
    reset_all_sessions()


def _tool_use(name: str, tool_input: dict[str, Any], uid: str = "tu_1"):
    return SimpleNamespace(type="tool_use", id=uid, name=name, input=tool_input)


def _text(text: str):
    return SimpleNamespace(type="text", text=text)


class ScriptedClient:
    """Minimal stand-in for `anthropic.Anthropic` with a scripted `messages.create`."""

    def __init__(self, responses: list[list[Any]]):
        self._responses = list(responses)
        self.calls = 0
        self.messages = self

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls += 1
        if not self._responses:
            raise AssertionError(f"unexpected messages.create #{self.calls}")
        content = self._responses.pop(0)
        return SimpleNamespace(content=content)


def test_lookup_order_updates_active_order_id():
    state = get_session("s-lookup")
    result = execute_tool("lookup_order", {"order_id": "TR-4530"}, state)
    assert result["order_id"] == "TR-4530"
    assert state.active_order_id == "TR-4530"
    assert state.tool_error_count == 0


def test_business_error_does_not_count_as_tool_failure():
    state = get_session("s-biz")
    execute_tool("lookup_order", {"order_id": "TR-9999"}, state)
    execute_tool("lookup_order", {"order_id": "TR-9999"}, state)
    assert state.tool_error_count == 0
    assert state.escalated is False


def test_two_consecutive_unrecoverable_errors_auto_escalate():
    state = get_session("s-err")
    r1 = execute_tool("not_a_real_tool", {}, state)
    assert r1.get("unrecoverable") is True
    assert state.escalated is False
    r2 = execute_tool("not_a_real_tool", {}, state)
    assert r2.get("status") == "escalated"
    assert r2.get("reason") == "tool_errors"
    assert state.escalated is True
    assert state.tool_error_count >= AUTO_ESCALATE_ERROR_THRESHOLD


def test_repeat_exchange_escalates(reference_clock):
    state = get_session("s-ex")
    # TR-4528 belongs to C-103 — Tier-1 initiate_return needs verification (FR-2.2).
    verify = execute_tool(
        "verify_customer",
        {"email": "diego.ramos@example.com", "order_id": "TR-4528"},
        state,
    )
    assert verify.get("verified") is True
    sku = "TR-SHR-009"  # TR-4528 final-sale → size exchange only
    first = execute_tool(
        "initiate_return",
        {"order_id": "TR-4528", "sku": sku, "intent": "exchange_size"},
        state,
    )
    assert first.get("initiated") is True
    assert state.has_exchanged(sku)
    second = execute_tool(
        "initiate_return",
        {"order_id": "TR-4528", "sku": sku, "intent": "exchange_size"},
        state,
    )
    assert second.get("status") == "escalated"
    assert second.get("reason") == "repeat_exchange"
    assert state.escalated is True


def test_run_turn_text_only_reply():
    client = ScriptedClient([[_text("Hello from Trendly.")]])
    out = run_turn("s-text", "hi", client=client)
    assert out["reply"] == "Hello from Trendly."
    assert out["trace"] == []
    assert out["state"]["escalated"] is False
    assert client.calls == 1


def test_run_turn_tool_then_text_and_trace(reference_clock):
    client = ScriptedClient([
        [_tool_use("lookup_order", {"order_id": "TR-4530"})],
        [_text("TR-4530 was delivered.")],
    ])
    out = run_turn("s-tool", "where is TR-4530?", client=client)
    assert "delivered" in out["reply"].lower() or out["reply"]
    assert len(out["trace"]) == 1
    assert out["trace"][0]["tool"] == "lookup_order"
    assert out["state"]["active_order"] == "TR-4530"
    assert client.calls == 2


def test_step_cap_forces_final_text_without_infinite_tools():
    # Every model turn requests a tool until the cap; then final no-tool call.
    looping = [
        [_tool_use("search_policy", {"query": "returns"}, uid=f"tu_{i}")]
        for i in range(MAX_TOOL_STEPS)
    ]
    looping.append([_text("Wrapping up from the step cap.")])
    client = ScriptedClient(looping)
    out = run_turn("s-cap", "tell me about returns", client=client)
    assert out["reply"] == "Wrapping up from the step cap."
    assert len(out["trace"]) == MAX_TOOL_STEPS
    # MAX_TOOL_STEPS tool rounds + 1 final text-only create
    assert client.calls == MAX_TOOL_STEPS + 1


def test_already_escalated_short_circuits():
    state = get_session("s-done")
    state.escalate()
    client = ScriptedClient([])  # must not be called
    out = run_turn("s-done", "anything else?", client=client)
    assert "specialist" in out["reply"].lower() or "support" in out["reply"].lower()
    assert client.calls == 0


def test_system_prompt_has_index_not_clause_bodies():
    from app.agent.prompts import build_system_prompt

    prompt = build_system_prompt()
    assert "§2.3" in prompt or "2.3" in prompt
    assert "Non-returnable categories" in prompt
    # Clause body from policy must not be memorised into the system prompt (P1).
    assert "Jewellery, including imitation jewellery" not in prompt
