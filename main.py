"""Trendly Agentic Support Assistant — FastAPI application entrypoint.

Scaffolded in Phase 0 (see CURSOR_BUILD_PLAN.md). This is deliberately a
skeleton: the `POST /chat` and `GET /health` routes, CORS configuration, and
the wiring to `agent.py` are added in Phase 6 ("API wiring", SRS §5.1), once
the data layer, eligibility engine, tools, and agent loop exist.

SRS refs: §3.1, §3.2
"""

from fastapi import FastAPI

app = FastAPI(
    title="Trendly Support Assistant",
    description="Agentic support assistant for order status, returns "
    "eligibility, policy Q&A, and escalation.",
    version="0.1.0",
)
