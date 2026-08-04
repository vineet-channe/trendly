# Trendly — Agentic Support Assistant

Multi-turn conversational agent for Trendly (D2C fashion) customer support: order status, returns/exchange eligibility, policy Q&A, and escalation to a human — built per `SRS.md`.

> **Status:** scaffolding in progress. This README is a placeholder; it will be finalized in Phase 11 with full run instructions, the deployed base URL, and an AI-usage note (see `CURSOR_BUILD_PLAN.md`).

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

## Docs

- `SRS.md` — full requirements and design principles
- `CURSOR_BUILD_PLAN.md` — phased build plan
- `DEV_LOG.md` — running log of what was built, when, and why
- `PROMPTS.md` — prompt revision history (added from Phase 4 onward)
- `SOLUTION.md` — architecture, trade-offs, limitations (added in Phase 11)

## Running locally

_Filled in once the backend and frontend skeletons exist (this phase) and wired up (Phase 6, Phase 10)._
