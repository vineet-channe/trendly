# Trendly — Agentic Support Assistant

Multi-turn conversational agent for Trendly (D2C fashion) customer support: order status, returns/exchange eligibility, policy Q&A, and escalation to a human.

**Live backend:** https://trendly-production.up.railway.app  
**Live frontend:** https://trendly-web-production.up.railway.app

See also: [SOLUTION.md](SOLUTION.md) (architecture, trade-offs, limitations) · [PROMPTS.md](PROMPTS.md) (prompt revision history)

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
tests/            Unit tests + live scripted harness (T1–T6)
```

## Quickest local smoke (one command after setup)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY

python -m app.cli -m "where is TR-4525?" --trace
```

CLI freezes the clock to 2026-08-04 by default so delay / return-window behaviour matches the dataset.

## Running locally (full stack)

```bash
# Backend API (CORS uses FRONTEND_ORIGIN from .env)
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd web
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000

# Smoke-check API
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-1","message":"Where is TR-4525?"}'

# Tests — unit always; live harness needs ANTHROPIC_API_KEY
pytest
pytest -m live
```

Interactive CLI: `python -m app.cli`

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

## AI usage and cost (NFR-1)

**Runtime model.** The agent calls Anthropic’s API with `claude-sonnet-4-5`, `temperature=0`, and a hard cap of 6 tool steps per turn (`app/config.py`). This uses Anthropic API / trial credit — **not** free-tier-only hosting. The assignment brief’s “free tiers only” line does not match this choice: Sonnet-class quality was kept for guardrail and policy-grounding behaviour; Haiku would be the fallback only if quota forced it.

**What was hand-designed vs assisted.** Architecture, requirements (`SRS.md`), eligibility rule order, and the design principles (P1–P7) were written by hand. Implementation and prompt iteration were assisted by Cursor. Every change to the system prompt is logged in [PROMPTS.md](PROMPTS.md) with before/after text and the failure that triggered it. Deterministic logic (dates, eligibility, disclosure gates) is plain Python — not delegated to the model.

**Secrets.** Set `ANTHROPIC_API_KEY` in `.env` locally and as a Railway backend variable. It is never committed (`.env` is gitignored).
