"""Per-turn server logging with PII scrubbing (NFR-6).

Client responses keep the full trace (Phase 9 UI). Server logs scrub
identity fields down to order ID only — no name, email, or phone.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any

logger = logging.getLogger("trendly.turn")

_PII_KEYS = frozenset({
    "email",
    "phone",
    "name",
    "customer_id",
    "customer_name",
    "verified_customer_id",
})

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{8,}\d)")


def _scrub_string(value: str) -> str:
    scrubbed = _EMAIL_RE.sub("[redacted]", value)
    return _PHONE_RE.sub("[redacted]", scrubbed)


def scrub_value(value: Any) -> Any:
    """Recursively redact PII keys and email/phone-shaped strings."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key in _PII_KEYS:
                out[key] = "[redacted]"
            else:
                out[key] = scrub_value(item)
        return out
    if isinstance(value, list):
        return [scrub_value(item) for item in value]
    if isinstance(value, str):
        return _scrub_string(value)
    return value


def scrub_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a deep-copied, PII-scrubbed trace safe for server logs."""
    return scrub_value(copy.deepcopy(trace))


def log_turn(
    session_id: str,
    *,
    trace: list[dict[str, Any]],
    escalated: bool,
) -> None:
    """Log one turn's scrubbed trace (NFR-6)."""
    logger.info(
        "turn session_id=%s escalated=%s trace=%s",
        session_id,
        escalated,
        scrub_trace(trace),
    )
