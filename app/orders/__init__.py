"""Read-only order and customer store."""

from app.orders.store import get_customer, get_order, load_data

__all__ = ["load_data", "get_order", "get_customer"]
