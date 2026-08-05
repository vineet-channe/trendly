"""Phase 0 sanity tests for the injectable clock (NFR-3) and business-day math
(FR-1.8).

This is deliberately minimal — the full scripted-conversation harness is
Phase 10 (SRS §8). This file only proves the seam every later date-dependent
feature depends on actually works before anything is built on top of it.
"""

from datetime import date, datetime

import app.config as config
import app.dates as dates


def test_now_can_be_overridden_and_restored():
    frozen = datetime(2026, 8, 4, 12, 0, 0)
    config.set_now_override(lambda: frozen)
    assert config.now() == frozen
    config.set_now_override(None)
    assert config.now() != frozen  # back to real wall-clock time


def test_business_days_since_excludes_weekends():
    # 2026-08-04 is a Tuesday; 2026-07-31 is the preceding Friday.
    config.set_now_override(lambda: datetime(2026, 8, 4))
    try:
        # Only Mon 8/3 and Tue 8/4 count as business days in between (FR-1.8);
        # this is the TR-4521 case from the SRS status matrix (2 business
        # days, not the 4 calendar days) — the exact trap FR-1.8 exists for.
        assert dates.business_days_since(date(2026, 7, 31)) == 2
    finally:
        config.set_now_override(None)


def test_calendar_days_since_counts_every_day():
    config.set_now_override(lambda: datetime(2026, 8, 4))
    try:
        assert dates.calendar_days_since(date(2026, 7, 31)) == 4
    finally:
        config.set_now_override(None)


def test_business_days_since_is_zero_for_future_dates():
    config.set_now_override(lambda: datetime(2026, 8, 4))
    try:
        assert dates.business_days_since(date(2026, 8, 9)) == 0
    finally:
        config.set_now_override(None)
