"""Calendar-day, business-day and hour arithmetic (SRS §1.4 Definitions, FR-1.8).

Every "how long has it been" question in `eligibility.py` and the delay check
goes through these functions, and they all go through `config.now()` rather
than `datetime.now()`, so they're deterministic under test (NFR-3).

No public-holiday calendar is modelled — Mon-Fri counts as a business day
unconditionally. This is a documented data gap (SRS §10.9), not an oversight:
it can make §1.1 dispatch timing and §1.5 delay thresholds slightly optimistic
around real holidays.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Union

from app.config import now

DateLike = Union[date, datetime, str]


def parse_timestamp(value: DateLike) -> datetime:
    """Parse an `orders.json` timestamp into a naive-UTC `datetime`.

    Timestamps in the dataset are UTC-suffixed (`2026-07-14T09:20:00Z`) while
    `config.now()` is naive, and comparing the two directly raises
    `TypeError`. Everything is therefore normalised to naive UTC here, at the
    one boundary where the string enters date arithmetic, rather than at every
    call site. Date-only strings (`expected_delivery`) become midnight.
    """
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        value = datetime.fromisoformat(text)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    return datetime(value.year, value.month, value.day)


def _to_date(value: DateLike) -> date:
    if isinstance(value, (str, datetime)):
        return parse_timestamp(value).date()
    return value


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


def hours_since(when: DateLike) -> float:
    """Hours elapsed since `when`, fractional.

    The §6.1 damage-reporting window is 48 *hours*, not two days, so it needs
    the time component that `calendar_days_since` throws away.
    """
    return (parse_timestamp(now()) - parse_timestamp(when)).total_seconds() / 3600
