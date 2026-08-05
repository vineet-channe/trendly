# Trendly — Agentic Support Assistant

Multi-turn conversational agent for Trendly (D2C fashion) customer support: order status, returns/exchange eligibility, policy Q&A, and escalation to a human.

> **Status:** backend through Phase 5 (agent loop + CLI). API wiring, frontend, and deploy follow in later phases.

## Layout

```
app/
  config.py, dates.py, main.py, cli.py
  agent/          ReAct loop, tool dispatch, system prompt
  tools/          Claude tool schemas + implementations + registry
  eligibility/    Pure-function eligibility chain (no LLM)
  policy/         Clause index + keyword search
  orders/         Read-only orders.json loader
  session/        In-memory SessionState store
data/             Fixed dataset (orders.json, trendly_policy.md) — read-only
web/              Next.js chat UI
tests/            Unit tests + (later) scripted conversation harness
```

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY

# Agent CLI (clock frozen to 2026-08-04 by default)
python -m app.cli
python -m app.cli -m "where is TR-4525?" --trace

# FastAPI skeleton
uvicorn app.main:app --reload

# Tests
pytest
```
