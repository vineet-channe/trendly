"""Deterministic eligibility engine (no LLM)."""

from app.eligibility.engine import check_eligibility
from app.eligibility.windows import check_damage_window, check_return_window, is_delayed

__all__ = [
    "check_eligibility",
    "is_delayed",
    "check_damage_window",
    "check_return_window",
]
