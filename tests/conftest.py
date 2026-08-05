"""Shared clock fixtures (NFR-3).

Every date-dependent assertion in the suite runs against a frozen
`config.now()`, so the tests keep meaning the same thing next week. The SRS
status matrix in §4.1 is stated "as of 2026-08-04", so that is the reference
instant the whole eligibility suite uses.
"""

from datetime import datetime

import pytest

import config

# The instant the SRS §4.1 status matrix was verified against the dataset.
REFERENCE_NOW = datetime(2026, 8, 4, 12, 0, 0)


@pytest.fixture
def frozen_clock():
    """Freeze `config.now()`, restoring the real clock on teardown.

    Yields a setter so a test can move the clock deliberately — the §6.1
    48-hour damage window has expired for every delivered order as of the
    reference date (SRS §10.10), so proving the eligible branch exists at all
    requires stepping back in time.
    """
    def freeze(when: datetime = REFERENCE_NOW) -> datetime:
        config.set_now_override(lambda: when)
        return when

    yield freeze
    config.set_now_override(None)


@pytest.fixture
def reference_clock(frozen_clock):
    """Clock frozen at 2026-08-04, the SRS §4.1 reference date."""
    return frozen_clock()
