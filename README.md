# Trendly — Agentic Support Assistant

Multi-turn conversational agent for Trendly (D2C fashion) customer support: order status, returns/exchange eligibility, policy Q&A, and escalation to a human.

> **Status:** scaffolding in progress. This README is a placeholder and will be finalized with full run instructions, the deployed base URL, and an AI-usage note.

## Planned layout

```
main.py            FastAPI app — POST /chat, GET /health
agent.py           ReAct agent loop (Claude tool-use)
tools.py           Tool implementations + JSON schemas
eligibility.py      Pure-function eligibility rule chain
policy_index.py     Parses trendly_policy.md into addressable clauses
state.py            Session state model
prompts.py          System prompt + tool descriptions
data/               Fixed dataset (orders.json, trendly_policy.md) — read-only
web/                Next.js chat UI
tests/              Scripted conversation test harness
```

## Running locally

_Filled in once the backend and frontend skeletons exist (this phase) and wired up (Phase 6, Phase 10)._
