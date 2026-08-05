"""Turn-log PII scrubbing tests (NFR-6)."""

from __future__ import annotations

from app.turn_log import scrub_trace, scrub_value


def test_scrub_redacts_pii_keys_keeps_order_id():
    trace = [
        {
            "tool": "verify_customer",
            "input": {
                "email": "priya@example.com",
                "phone": "+91 98765 43210",
                "order_id": "TR-4530",
            },
            "output": {
                "customer_id": "C-101",
                "name": "Priya Sharma",
                "order_id": "TR-4530",
                "ok": True,
            },
        }
    ]
    scrubbed = scrub_trace(trace)
    step = scrubbed[0]
    assert step["input"]["order_id"] == "TR-4530"
    assert step["output"]["order_id"] == "TR-4530"
    assert step["input"]["email"] == "[redacted]"
    assert step["input"]["phone"] == "[redacted]"
    assert step["output"]["customer_id"] == "[redacted]"
    assert step["output"]["name"] == "[redacted]"
    # Original untouched
    assert trace[0]["input"]["email"] == "priya@example.com"


def test_scrub_redacts_email_and_phone_in_strings():
    value = scrub_value(
        "Contact priya@example.com or +91 98765 43210 about TR-4530"
    )
    assert "priya@example.com" not in value
    assert "+91 98765 43210" not in value
    assert "TR-4530" in value
    assert "[redacted]" in value
