"""Phase 3 tests for session state (SRS §7, FR-2, FR-7)."""

import pytest

import app.session.store as session_store
from app.session.state import AUTO_ESCALATE_ERROR_THRESHOLD, SessionState


@pytest.fixture(autouse=True)
def _isolated_store():
    """Every test gets a clean process-wide store, so ordering between
    tests can never leak a session from one test into another."""
    session_store.reset_all_sessions()
    yield
    session_store.reset_all_sessions()


def test_two_sessions_do_not_see_each_others_state():
    a = session_store.get_session("session-a")
    b = session_store.get_session("session-b")

    a.add_message("user", "where is TR-4530?")
    a.verify("C-101")
    a.record_exchange("TR-KRT-033")

    assert b.messages == []
    assert b.verified_customer_id is None
    assert b.exchanged_skus == set()


def test_fresh_session_states_do_not_share_mutable_defaults():
    # Guards against the classic dataclass bug: a bare `[]`/`set()` default
    # being the *same* object across instances.
    first = SessionState(session_id="x")
    second = SessionState(session_id="y")

    first.messages.append({"role": "user", "content": "hi"})
    first.exchanged_skus.add("TR-TSH-002")

    assert second.messages == []
    assert second.exchanged_skus == set()


def test_verification_survives_across_turns():
    session_id = "session-c"
    turn_one = session_store.get_session(session_id)
    turn_one.verify("C-100")

    # Simulate a later turn re-fetching the same session.
    turn_two = session_store.get_session(session_id)
    assert turn_two.is_verified()
    assert turn_two.verified_customer_id == "C-100"


def test_get_or_create_returns_the_same_instance():
    first = session_store.get_session("session-d")
    second = session_store.get_session("session-d")
    assert first is second


def test_peek_returns_none_for_unknown_session_without_creating_it():
    assert session_store.peek_session("never-seen") is None
    assert session_store.peek_session("never-seen") is None  # no side effect


def test_switching_active_order_clears_stale_eligibility_verdict():
    state = SessionState(session_id="session-e")
    state.set_active_order("TR-4530")
    state.record_eligibility_verdict({"order_id": "TR-4530", "eligible": True})

    state.set_active_order("TR-4523")

    assert state.active_order_id == "TR-4523"
    assert state.last_eligibility_verdict is None


def test_resetting_the_same_active_order_keeps_the_verdict():
    state = SessionState(session_id="session-f")
    state.set_active_order("TR-4530")
    verdict = {"order_id": "TR-4530", "eligible": True}
    state.record_eligibility_verdict(verdict)

    state.set_active_order("TR-4530")

    assert state.last_eligibility_verdict == verdict


def test_record_eligibility_verdict_syncs_active_order():
    state = SessionState(session_id="session-g")
    # No prior active order — "okay, do it" after a single lookup should
    # still resolve against the order the verdict was computed for.
    state.record_eligibility_verdict({"order_id": "TR-4522", "eligible": False})

    assert state.active_order_id == "TR-4522"


def test_record_eligibility_verdict_handles_multi_item_shape():
    # check_eligibility(sku=None) returns {order_id, intent, verdicts: [...]}
    # rather than a single verdict — both shapes carry a top-level order_id.
    multi_item_result = {
        "order_id": "TR-4522",
        "intent": "return",
        "verdicts": [
            {"sku": "TR-TSH-002", "eligible": True},
            {"sku": "TR-SOK-031", "eligible": False},
        ],
    }
    state = SessionState(session_id="session-h")
    state.record_eligibility_verdict(multi_item_result)

    assert state.active_order_id == "TR-4522"
    assert state.last_eligibility_verdict == multi_item_result


def test_exchanged_skus_tracks_repeat_exchange_trigger():
    # A second exchange on the same SKU is the FR-5.1 trigger; the state
    # just needs to keep reporting "yes, already exchanged" idempotently.
    state = SessionState(session_id="session-i")
    assert not state.has_exchanged("TR-SNK-017")

    state.record_exchange("TR-SNK-017")
    state.record_exchange("TR-SNK-017")

    assert state.has_exchanged("TR-SNK-017")
    assert state.exchanged_skus == {"TR-SNK-017"}


def test_tool_error_count_increments_and_resets():
    state = SessionState(session_id="session-j")
    assert state.tool_error_count == 0

    first = state.record_tool_error()
    second = state.record_tool_error()

    assert first == 1
    assert second == 2
    assert state.tool_error_count == AUTO_ESCALATE_ERROR_THRESHOLD

    state.record_tool_success()
    assert state.tool_error_count == 0


def test_escalate_sets_flag():
    # Nothing in this module un-escalates a session, intentionally — once
    # set, `agent.py` stops attempting resolution (FR-5.4).
    state = SessionState(session_id="session-k")
    assert not state.escalated

    state.escalate()

    assert state.escalated
