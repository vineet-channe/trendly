"""Trendly FastAPI app — /chat, /health, CORS (SRS §5.1, NFR-5, NFR-6)."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.loop import run_turn
from app.api_models import ChatRequest, ChatResponse, SessionStateView
from app.turn_log import log_turn

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(
    title="Trendly Support Assistant",
    description="Agentic support assistant for order status, returns "
    "eligibility, policy Q&A, and escalation.",
    version="0.1.0",
)

# Comma-separated so localhost and the live frontend can both work (Phase 9).
_origins = [
    o.strip()
    for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    result = run_turn(body.session_id, body.message)
    state = result["state"]
    log_turn(
        body.session_id,
        trace=result["trace"],
        escalated=bool(state.get("escalated")),
    )
    return ChatResponse(
        session_id=body.session_id,
        reply=result["reply"],
        state=SessionStateView(**state),
        trace=result["trace"],
    )
