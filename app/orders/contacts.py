"""Email/phone → customer matching for Tier-1 verification (FR-2.2).

Exact match only — never fuzzy onto another customer (mirrors FR-1.3).
Matching lives here so `SessionState.verify()` stays a pure outcome recorder.
"""

from __future__ import annotations

from typing import Any, Optional

from app.orders.store import list_customers


def _digits_only(value: str) -> str:
    """Strip everything except digits for phone comparison."""
    return "".join(ch for ch in value if ch.isdigit())


def find_customer_by_contact(
    email: Optional[str] = None, phone: Optional[str] = None
) -> Optional[dict[str, Any]]:
    """Resolve a customer by email and/or phone (FR-2.2).

    Email is case-insensitive exact match. Phone compares digit-only forms
    so ``+91-98765-10001`` matches ``9876510001``. At least one identifier
    is required; both may be supplied and either may match. Returns the
    first matching customer record, or ``None`` on a miss.
    """
    email_key = email.strip().lower() if email and email.strip() else None
    phone_key = _digits_only(phone) if phone and phone.strip() else None
    if not email_key and not phone_key:
        return None

    for customer in list_customers():
        if email_key and customer.get("email", "").strip().lower() == email_key:
            return customer
        stored_phone = customer.get("phone") or ""
        if phone_key and _digits_only(stored_phone) == phone_key:
            return customer
    return None
