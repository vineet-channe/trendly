"""Policy time-window checks (FR-1.8, FR-4.6, §2.1).

Three thresholds the policy states in three different units — business days
for delays (§1.5), hours for damage reports (§6.1), calendar days for the
return window (§2.1). Mixing those units up is the single most likely way to
produce a confidently wrong verdict, so each one is its own named function
with the unit in its docstring, and each returns the measured value alongside
the boolean so a caller (and a trace) can show its work.

Pure functions, no LLM, no I/O — the model never computes these (P2). Split
out of `eligibility.py` to keep both files under NFR-7's ~150-line cap.
"""

from __future__ import annotations

from typing import Any, Optional

from dates import business_days_since, calendar_days_since, hours_since

# §1.5 — "more than 3 business days past its expected delivery date".
DELAY_THRESHOLD_BUSINESS_DAYS = 3

# §6.1 — damaged/defective/incorrect items reported within 48 hours of delivery.
DAMAGE_WINDOW_HOURS = 48

# §2.1 — 30 calendar days from delivery, not from the order date.
RETURN_WINDOW_DAYS = 30


def is_delayed(expected_delivery: Optional[str]) -> bool:
    """True only when an order is more than 3 *business* days past its
    expected delivery date (FR-1.8, §1.5).

    Business days, not calendar days: TR-4521 is 4 calendar days but only 2
    business days past expectation, so it is not delayed and the §1.5 ₹250
    credit is not authorised for it. Offering that credit early is an
    unauthorised credit under FR-6.1, which is why this is a code-side
    threshold and not something the model is asked to eyeball.

    A missing `expected_delivery` (cancelled orders carry `null`) is not
    delayed — it has no date to be late against (FR-6.6).
    """
    if not expected_delivery:
        return False
    return business_days_since(expected_delivery) > DELAY_THRESHOLD_BUSINESS_DAYS


def check_damage_window(delivered_at: Optional[str]) -> dict[str, Any]:
    """Whether a damage/wrong-item claim is still inside the §6.1 48-hour
    reporting window (FR-4.6).

    Returns `{within_window, hours_since, threshold_hours, clause_ids}`.
    Nothing delivered means nothing to report damage on, so an undelivered
    order is outside the window rather than an error.

    As of 2026-08-04 this has expired for every delivered order in the
    dataset (SRS §10.10); the agent has to say so rather than accept the
    claim, and the eligible path is only reachable with an injected clock.
    """
    if not delivered_at:
        return {
            "within_window": False,
            "hours_since": None,
            "threshold_hours": DAMAGE_WINDOW_HOURS,
            "clause_ids": ["6.1"],
        }
    elapsed = hours_since(delivered_at)
    return {
        "within_window": elapsed <= DAMAGE_WINDOW_HOURS,
        "hours_since": round(elapsed, 1),
        "threshold_hours": DAMAGE_WINDOW_HOURS,
        "clause_ids": ["6.1"],
    }


def check_return_window(delivered_at: Optional[str]) -> dict[str, Any]:
    """Whether the §2.1 30-calendar-day return window is still open.

    Returns `{within_window, days_since, threshold_days, clause_ids}`.
    Counted from delivery, never from `placed_at` (§2.1 is explicit about
    this). An undelivered order has not started its window — the caller
    distinguishes "not started" from "expired", since they are different
    answers to the customer even though both block a return.
    """
    if not delivered_at:
        return {
            "within_window": False,
            "days_since": None,
            "threshold_days": RETURN_WINDOW_DAYS,
            "clause_ids": ["2.1"],
        }
    days = calendar_days_since(delivered_at)
    return {
        "within_window": days <= RETURN_WINDOW_DAYS,
        "days_since": days,
        "threshold_days": RETURN_WINDOW_DAYS,
        "clause_ids": ["2.1"],
    }
