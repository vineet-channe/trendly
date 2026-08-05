"""Phase 2 tests for the three policy time windows (FR-1.8, FR-4.6, §2.1).

The delay threshold is the one the SRS calls out as a trap: TR-4521 is 4
calendar days past its expected delivery but only 2 business days, so it is
not delayed and the ₹250 credit is not authorised for it (FR-6.1).
"""

from datetime import date, datetime

import app.orders.store as order_store
from app.eligibility.windows import check_damage_window, check_return_window, is_delayed


def _expected(order_id):
    return order_store.get_order(order_id)["expected_delivery"]


def _delivered(order_id):
    return order_store.get_order(order_id)["delivered_at"]


def test_tr4521_is_not_delayed_despite_four_calendar_days(reference_clock):
    # 2026-07-31 is a Friday; only Mon 8/3 and Tue 8/4 are business days since.
    assert is_delayed(_expected("TR-4521")) is False


def test_tr4524_partially_shipped_is_not_delayed(reference_clock):
    assert is_delayed(_expected("TR-4524")) is False


def test_tr4525_is_delayed(reference_clock):
    # 14 business days past 2026-07-15 — this is the order that earns §1.5.
    assert is_delayed(_expected("TR-4525")) is True


def test_delay_threshold_boundary_is_strictly_more_than_three(frozen_clock):
    # Wed 2026-07-29 expected: Thu, Fri, Mon = 3 business days by Mon 8/3.
    frozen_clock(datetime(2026, 8, 3, 12, 0))
    assert is_delayed("2026-07-29") is False
    frozen_clock(datetime(2026, 8, 4, 12, 0))  # a 4th business day
    assert is_delayed("2026-07-29") is True


def test_missing_expected_delivery_is_not_delayed(reference_clock):
    # TR-4529 is cancelled and carries a null expected_delivery (FR-6.6).
    assert _expected("TR-4529") is None
    assert is_delayed(None) is False


def test_damage_window_expired_for_every_delivered_order(reference_clock):
    # FR-4.6 / SRS §10.10 — as of the reference date this path is closed for
    # the whole dataset, and the agent has to say so rather than accept it.
    delivered = [o for o in order_store.list_orders() if o["delivered_at"]]
    assert len(delivered) == 5
    for order in delivered:
        result = check_damage_window(order["delivered_at"])
        assert result["within_window"] is False
        assert result["clause_ids"] == ["6.1"]


def test_damage_window_open_within_48_hours(frozen_clock):
    # TR-4522 was delivered 2026-07-14T09:20Z; freeze just under a day later.
    frozen_clock(datetime(2026, 7, 15, 9, 0))
    result = check_damage_window(_delivered("TR-4522"))
    assert result["within_window"] is True
    assert result["hours_since"] < 48


def test_damage_window_closes_just_past_48_hours(frozen_clock):
    frozen_clock(datetime(2026, 7, 16, 9, 0))  # 47.7h — still inside
    assert check_damage_window(_delivered("TR-4522"))["within_window"] is True
    frozen_clock(datetime(2026, 7, 16, 10, 0))  # 48.7h — outside
    assert check_damage_window(_delivered("TR-4522"))["within_window"] is False


def test_damage_window_on_undelivered_order(reference_clock):
    result = check_damage_window(_delivered("TR-4521"))
    assert result["within_window"] is False
    assert result["hours_since"] is None


def test_return_window_open_and_closed(reference_clock):
    assert check_return_window(_delivered("TR-4530"))["days_since"] == 9
    assert check_return_window(_delivered("TR-4530"))["within_window"] is True
    assert check_return_window(_delivered("TR-4522"))["days_since"] == 21
    assert check_return_window(_delivered("TR-4523"))["days_since"] == 60
    assert check_return_window(_delivered("TR-4523"))["within_window"] is False


def test_return_window_boundary_is_thirty_calendar_days(frozen_clock):
    frozen_clock(datetime(2026, 8, 25, 12, 0))  # 30 days after 2026-07-26
    assert check_return_window("2026-07-26T11:00:00Z")["within_window"] is True
    frozen_clock(datetime(2026, 8, 26, 12, 0))  # 31 days
    assert check_return_window("2026-07-26T11:00:00Z")["within_window"] is False


def test_return_window_not_started_when_undelivered(reference_clock):
    result = check_return_window(None)
    assert result["within_window"] is False
    assert result["days_since"] is None
    assert result["clause_ids"] == ["2.1"]


def test_windows_accept_date_objects_as_well_as_strings(reference_clock):
    assert is_delayed(date(2026, 7, 15)) is True
