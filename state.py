"""Per-session conversation state model (SRS §7, FR-2, FR-7).

`SessionState` is built ahead of the agent loop (Phase 5) on purpose: the
loop reads `tool_error_count` to decide when to auto-escalate (FR-5.1), and
building the counter here first means Phase 5 consumes it rather than
stubbing and later rewriting it.

The in-memory, per-`session_id` *store* lives in `session_store.py`, split
out purely to stay under `CURSOR_INSTRUCTIONS.md` §4's ~150-line cap (same
precedent as the Phase 1 `policy_index`/`policy_search` split).

Two things this module deliberately does NOT do:
- Verify that an email/phone actually matches the order's customer — that
  matching logic is Phase 6's (FR-2.2). `verify()` here just records the
  outcome once Phase 6 has decided it.
- Decide *when* to auto-escalate on repeated tool errors — that behaviour
  lives in `agent.py` (Phase 5). This module only carries the counter and
  the threshold constant it should be compared against.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# FR-5.1 — "≥2 consecutive unrecoverable tool errors" auto-escalates. Defined
# here, next to the counter it thresholds, so Phase 5's agent loop imports
# the number instead of re-stating it.
AUTO_ESCALATE_ERROR_THRESHOLD = 2


@dataclass
class SessionState:
    """One conversation's state, exactly the SRS §7 field list plus
    `messages` for the Phase 5 agent loop to accumulate conversation turns.

    `messages` and `exchanged_skus` use `default_factory` rather than a bare
    `[]`/`set()` default — a shared mutable default would leak state between
    sessions, which is precisely the bug the phase's "two different
    `session_id`s cannot see each other's state" done-criterion exists to
    catch.
    """

    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    verified_customer_id: Optional[str] = None
    active_order_id: Optional[str] = None
    last_eligibility_verdict: Optional[dict[str, Any]] = None
    exchanged_skus: set[str] = field(default_factory=set)
    escalated: bool = False
    tool_error_count: int = 0

    def add_message(self, role: str, content: str) -> None:
        """Append one conversation turn, for the Phase 5 agent loop to
        replay back to Claude.
        """
        self.messages.append({"role": role, "content": content})

    def is_verified(self) -> bool:
        """Whether this session has passed Tier-1 disclosure (FR-2.2)."""
        return self.verified_customer_id is not None

    def verify(self, customer_id: str) -> None:
        """Record a passed Tier-1 verification (FR-2.2).

        This only stores the outcome — confirming the supplied email/phone
        actually matches `customer_id` is Phase 6's job, not this module's.
        """
        self.verified_customer_id = customer_id

    def set_active_order(self, order_id: Optional[str]) -> None:
        """Update the order the session is currently talking about (FR-7.1,
        FR-7.3).

        Switching to a genuinely different order clears
        `last_eligibility_verdict` too: a verdict computed for the previous
        order is not a safe answer to "okay, do it" once the topic has moved
        on, and holding onto it is exactly the "mixing contexts" the phase's
        done-criterion rules out. Re-setting the *same* order (or setting it
        for the first time) leaves any existing verdict alone.
        """
        if order_id is not None and order_id != self.active_order_id:
            self.last_eligibility_verdict = None
        self.active_order_id = order_id

    def record_eligibility_verdict(self, verdict: dict[str, Any]) -> None:
        """Store a `check_eligibility` result and sync `active_order_id` to
        it (FR-7.2), so a follow-up like "okay, do it" resolves against the
        right order and item without re-asking.

        `verdict` may be either shape `check_eligibility` returns — a single
        per-SKU verdict or the `{order_id, intent, verdicts: [...]}`
        multi-item wrapper — both carry a top-level `order_id`.
        """
        self.last_eligibility_verdict = verdict
        order_id = verdict.get("order_id")
        if order_id is not None:
            self.active_order_id = order_id

    def record_exchange(self, sku: str) -> None:
        """Track that `sku` has been exchanged this session (§4.4's
        one-exchange-per-item limit, FR-5.1's repeat-exchange trigger).

        Only enforceable within a session — the dataset has no exchange
        history (SRS §10.7), a documented data gap, not an oversight.
        """
        self.exchanged_skus.add(sku)

    def has_exchanged(self, sku: str) -> bool:
        """Whether `sku` was already exchanged this session — a second
        request on it is a mandatory escalation trigger (FR-5.1, §4.4)."""
        return sku in self.exchanged_skus

    def record_tool_error(self) -> int:
        """Increment the consecutive-error counter and return the new
        count, for `agent.py` to compare against
        `AUTO_ESCALATE_ERROR_THRESHOLD` (FR-5.1).
        """
        self.tool_error_count += 1
        return self.tool_error_count

    def record_tool_success(self) -> None:
        """Reset the consecutive-error counter — the threshold is
        consecutive failures, not a lifetime total."""
        self.tool_error_count = 0

    def escalate(self) -> None:
        """Mark this session as handed off to a human (FR-5.4). Once set,
        `agent.py` stops attempting further resolution."""
        self.escalated = True
