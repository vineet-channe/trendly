"""Read-only order and customer data access (SRS §3.1, NFR-4).

Loads `data/orders.json` exactly once, strips every `_note_for_designers`
field recursively before the data is exposed anywhere else in the app, and
never mutates the source file. `_note_for_designers` is internal assignment
scaffolding (hints about what a test case is checking) and must never reach
a user-facing reply, an agent trace, or a log line (CURSOR_INSTRUCTIONS.md
§6).

Lookups are exact-match only (FR-1.3): an unknown `order_id` returns `None`
rather than a fuzzy/partial match onto a real order.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

DATA_PATH = Path(__file__).resolve().parent / "data" / "orders.json"

_NOTE_KEY = "_note_for_designers"

_cache: Optional[dict[str, Any]] = None


def _strip_notes(value: Any) -> Any:
    """Recursively remove `_note_for_designers` keys at any nesting depth
    (NFR-4). Applied once, at load time, so nothing downstream — tools,
    traces, logs — can ever see them.
    """
    if isinstance(value, dict):
        return {k: _strip_notes(v) for k, v in value.items() if k != _NOTE_KEY}
    if isinstance(value, list):
        return [_strip_notes(v) for v in value]
    return value


def load_data(force_reload: bool = False) -> dict[str, Any]:
    """Load and cache `orders.json`, read-only, notes stripped (NFR-4).

    `force_reload` exists only for tests; production code never needs it
    since the source file is fixed for the process lifetime.
    """
    global _cache
    if _cache is None or force_reload:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        _cache = _strip_notes(raw)
    return _cache


def list_orders() -> list[dict[str, Any]]:
    """Every order in the fixed dataset, notes stripped."""
    return list(load_data()["orders"])


def get_order(order_id: str) -> Optional[dict[str, Any]]:
    """Exact-match order lookup. Unknown IDs return `None`, never a fuzzy
    or partial match onto a real order (FR-1.3).
    """
    for order in list_orders():
        if order["order_id"] == order_id:
            return order
    return None


def list_customers() -> list[dict[str, Any]]:
    """Every customer record in the fixed dataset."""
    return list(load_data()["customers"])


def get_customer(customer_id: str) -> Optional[dict[str, Any]]:
    """Exact-match customer lookup by `customer_id`."""
    for customer in list_customers():
        if customer["customer_id"] == customer_id:
            return customer
    return None


def get_orders_for_customer(customer_id: str) -> list[dict[str, Any]]:
    """All orders belonging to one customer — used later for cross-customer
    protection (FR-2.4): confirming an order does *not* belong to the
    verified session's customer.
    """
    return [order for order in list_orders() if order["customer_id"] == customer_id]
