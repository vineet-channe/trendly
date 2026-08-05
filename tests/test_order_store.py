"""Phase 1 tests for the order data layer (NFR-4, FR-1.3)."""

import json

import app.orders.store as order_store


def _all_values(obj):
    """Yield every nested value in a JSON-shaped structure, for a recursive
    "does this key exist anywhere" scan.
    """
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _all_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _all_values(item)
    else:
        yield obj


def test_loading_and_dumping_every_order_has_zero_notes():
    data = order_store.load_data(force_reload=True)
    dumped = json.dumps(data)
    assert "_note_for_designers" not in dumped
    for order in data["orders"]:
        assert "_note_for_designers" not in order


def test_source_file_still_has_notes_untouched():
    # Guards against ever mutating orders.json in place (NFR-4).
    raw_text = order_store.DATA_PATH.read_text(encoding="utf-8")
    assert "_note_for_designers" in raw_text


def test_get_order_exact_match():
    order = order_store.get_order("TR-4530")
    assert order is not None
    assert order["order_id"] == "TR-4530"
    assert order["status"] == "delivered"


def test_get_order_unknown_id_returns_none_not_a_fuzzy_match():
    assert order_store.get_order("TR-9999") is None
    assert order_store.get_order("tr-4530") is None  # case must not fuzzy-match
    assert order_store.get_order("") is None


def test_get_customer_exact_match():
    customer = order_store.get_customer("C-101")
    assert customer is not None
    assert customer["name"] == "Marcus Bell"


def test_get_customer_unknown_id_returns_none():
    assert order_store.get_customer("C-999") is None


def test_get_orders_for_customer():
    orders = order_store.get_orders_for_customer("C-100")
    order_ids = {o["order_id"] for o in orders}
    assert order_ids == {"TR-4521", "TR-4524", "TR-4529"}


def test_all_ten_orders_present():
    orders = order_store.list_orders()
    assert len(orders) == 10
    ids = {o["order_id"] for o in orders}
    assert ids == {
        "TR-4521", "TR-4522", "TR-4523", "TR-4524", "TR-4525",
        "TR-4526", "TR-4527", "TR-4528", "TR-4529", "TR-4530",
    }
