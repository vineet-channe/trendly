"""Calendar-day and business-day arithmetic (SRS §1.4 Definitions, FR-1.8).

Every "how long has it been" question in `eligibility.py` and the delay check
goes through these two functions, and both go through `config.now()` rather
than `datetime.now()`, so they're deterministic under test (NFR-3).

No public-holiday calendar is modelled — Mon-Fri counts as a business day
unconditionally. This is a documented data gap (SRS §10.9), not an oversight:
it can make §1.1 dispatch timing and §1.5 delay thresholds slightly optimistic
around real holidays.
"""

from datetime import date, datetime, timedelta
from typing import Union

from config import now

DateLike = Union[date, datetime]


def _to_date(value: DateLike) -> date:
    return value.date() if isinstance(value, datetime) else value


def calendar_days_since(when: DateLike) -> int:
    """Whole calendar days between `when` and now.

    Used for the 30-day return window (§2.1); the 48-hour damage window
    (§6.1) is checked in hours, not here.
    """
    return (_to_date(now()) - _to_date(when)).days


def business_days_since(when: DateLike) -> int:
    """Whole business days (Mon-Fri) strictly after `when`, up to and
    including now, per FR-1.8.

    Weekends are excluded; public holidays are not (SRS §10.9). This decides
    whether an order is "delayed" under §1.5 (>3 business days past
    `expected_delivery`) — calendar days would over-count and risk the agent
    offering the ₹250 credit before it's actually earned (FR-6.1).
    """
    start = _to_date(when)
    end = _to_date(now())
    if end <= start:
        return 0
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon=0 .. Fri=4
            days += 1
    return days
