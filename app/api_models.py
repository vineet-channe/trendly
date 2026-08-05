"""Pydantic request/response models for the chat API (SRS §5.1)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class SessionStateView(BaseModel):
    verified: bool
    active_order: Optional[str] = None
    escalated: bool


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    state: SessionStateView
    trace: list[dict[str, Any]]
