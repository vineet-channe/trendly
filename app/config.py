"""Runtime configuration for the Trendly agent.

Centralizes the model name, temperature, and tool-call step cap (NFR-1, NFR-2),
and provides the single injectable clock every date computation in the
codebase must go through instead of calling `datetime.now()` directly
(NFR-3). Tests freeze time via `set_now_override()`.
"""

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# Repo root (parent of the `app/` package) — data files stay at `data/`.
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# NFR-1: Sonnet-class model for quality on guardrail and grounding behaviour.
# Drop to a Haiku-class model only if trial-credit quota forces it; actual
# model, spend, and rationale get disclosed in the README once the agent is
# wired up (Phase 5+).
MODEL_NAME = "claude-sonnet-4-5"

# NFR-3: deterministic outputs across the whole agent loop.
TEMPERATURE = 0

# NFR-2: hard cap on tool-call round-trips per turn.
MAX_TOOL_STEPS = 6

_now_override: Optional[Callable[[], datetime]] = None


def now() -> datetime:
    """Return the current time — the only sanctioned source of "now" (NFR-3).

    `dates.py` and, later, `eligibility.py` must call this instead of
    `datetime.now()` directly, so date-dependent behaviour can be tested
    against a frozen clock rather than depending on wall-clock time.
    """
    if _now_override is not None:
        return _now_override()
    return datetime.now()


def set_now_override(fn: Optional[Callable[[], datetime]]) -> None:
    """Override `now()` for tests. Pass `None` to restore real wall-clock time."""
    global _now_override
    _now_override = fn
