"""In-memory per-session state store (SRS §7).

In-memory, keyed by `session_id` — the persistence trade-off SRS §7 makes
explicitly: the assignment is single-instance and evaluated by scripted
conversations, so a database adds deployment surface without adding
evaluated capability. Restarting the process loses every session; that's a
documented limitation (SRS §10.1), not a bug to fix here.

Split out of `state.py` purely to stay under `CURSOR_INSTRUCTIONS.md` §4's
~150-line cap — the `SessionState` model and the store that holds instances
of it are two different jobs sharing one concern, same precedent as the
Phase 1 `policy_index`/`policy_search` split.
"""

from __future__ import annotations

from typing import Optional

from state import SessionState


class SessionStore:
    """In-memory store of `SessionState`, keyed by `session_id`.

    A plain dict rather than anything fancier: single-process, in-memory
    persistence is the documented trade-off (SRS §7), and this store is the
    one place that trade-off is implemented.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        """Return the existing state for `session_id`, creating a fresh one
        on first use. Idempotent — the same `session_id` always returns the
        same instance, which is what lets verification and other state
        survive across turns (FR-2.2, FR-7)."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionState]:
        """Return the state for `session_id` without creating one, or
        `None` if the session doesn't exist yet."""
        return self._sessions.get(session_id)

    def reset(self, session_id: str) -> None:
        """Drop one session's state. Test-only — production code never
        needs to forget a session mid-process."""
        self._sessions.pop(session_id, None)

    def reset_all(self) -> None:
        """Drop every session's state. Test-only, for isolating test runs
        from each other."""
        self._sessions.clear()


# Module-level singleton, mirroring `order_store.py`'s convention: callers
# (eventually `main.py` in Phase 7) import the functions below rather than
# constructing their own `SessionStore`.
default_store = SessionStore()


def get_session(session_id: str) -> SessionState:
    """Fetch-or-create a session's state from the process-wide store."""
    return default_store.get_or_create(session_id)


def peek_session(session_id: str) -> Optional[SessionState]:
    """Look up a session without creating one, or `None` if it doesn't
    exist yet."""
    return default_store.get(session_id)


def reset_all_sessions() -> None:
    """Clear the process-wide store. Test-only."""
    default_store.reset_all()
