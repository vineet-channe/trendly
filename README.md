# Trendly — Agentic Support Assistant

Multi-turn conversational agent for Trendly (D2C fashion) customer support: order status, returns/exchange eligibility, policy Q&A, and escalation to a human.

**Live backend:** https://trendly-production.up.railway.app  
**Live frontend:** https://trendly-web-production.up.railway.app

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
web/              Next.js chat UI (message list + collapsible tool trace)
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

# FastAPI (CORS uses FRONTEND_ORIGIN from .env)
uvicorn app.main:app --reload

# Frontend
cd web
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000

# Smoke-check API
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-1","message":"Where is TR-4525?"}'

# Tests
pytest
```

## Railway (two services, one repo)

| Service | Root directory | Public URL role |
|---|---|---|
| Backend | repo root | FastAPI `/health`, `/chat` |
| Frontend (`trendly-web`) | `web` | Next.js chat UI |

**Backend env:** `ANTHROPIC_API_KEY`, `FRONTEND_ORIGIN` (comma-separated, e.g. `https://trendly-web-production.up.railway.app,http://localhost:3000`)

**Frontend env (set before first build):** `NEXT_PUBLIC_API_BASE_URL=https://trendly-production.up.railway.app`

Backend start command (`railway.toml` / `Procfile` at repo root):

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Frontend start command (`web/railway.toml`):

```text
npx next start -H 0.0.0.0 -p $PORT
```
