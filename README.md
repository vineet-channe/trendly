# Trendly — Agentic Support Assistant

<p align="center">
  <img src="assets/trendly-logo.png" alt="Trendly" width="280" />
</p>

Multi-turn conversational agent for Trendly (D2C fashion) customer support: order status, returns/exchange eligibility, policy Q&A, and escalation to a human.

**Live backend:** https://trendly-production.up.railway.app  
**Live frontend:** https://trendly-web-production.up.railway.app

See also: [SOLUTION.md](SOLUTION.md) (architecture, trade-offs, limitations, discovery questions) · [PROMPTS.md](PROMPTS.md) (prompt revision history)

---

## What is Trendly?

Trendly is a **fictional D2C fashion brand** used for this assignment — apparel, accessories, footwear, jewellery, and similar categories sold online in India-oriented logistics (carriers, IST support hours, UPI/COD/card).

Customers place orders, track shipments, and ask about returns, exchanges, refunds, and shipping rules. Most of that volume is repetitive. This repository is the **agentic support assistant** for that brand: it answers from a fixed sample order book and a written shipping/returns policy, acts on eligible returns with mock RMAs, and hands harder cases to a human with a structured summary.

---

## What the assistant does

| Capability | Behaviour |
|---|---|
| Order status | Looks up `TR-4521`…`TR-4530` by exact ID; explains status, ETA, tracking, items in plain language |
| Policy Q&A | Answers only from `data/trendly_policy.md`, retrieved per turn — never from memorised clause text in the prompt |
| Returns / exchanges / damage | Eligibility is computed in Python per line item; the model phrases the result and cites clause IDs |
| Actions | Mock `initiate_return` (RMA + next steps), guarded `issue_delay_credit` (₹250 only when business-day delay threshold is met), `escalate_to_human` |
| Safety | Refuses invented discounts, payment-detail collection, cross-customer leakage, and injection-style “ignore your policy” prompts |

**Out of scope:** real payments, real carrier APIs, real ticketing, full login/auth, durable multi-instance session storage, multilingual support.

---

## How a conversation works

```
Browser (Next.js)  →  POST /chat  →  ReAct agent loop (Claude tool-use)
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              orders/              policy/              eligibility/
           (orders.json)      (clause search)        (pure rules)
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                         ▼
                              session/ (in-memory state)
                                         │
              ←  { reply, state, trace[] }  ──────────────────┘
```

1. The UI sends `{ session_id, message }` to FastAPI.
2. `run_turn` loads or creates in-memory `SessionState`, appends the user message, and enters a ReAct loop: Claude may call tools; each call is executed in Python and appended to a **trace**.
3. Deterministic layers do the hard work (dates, eligibility, disclosure gates). The model chooses tools and writes the customer-facing reply.
4. The response includes `reply`, a small `state` snapshot (`verified`, `active_order`, `escalated`), and the full `trace` for the UI panel and logging.
5. Loop stops on a text answer, escalation, or a hard cap of **6 tool steps** per turn (`temperature=0`).

---

## Design rules (short)

- **Retrieve, don’t memorise.** The system prompt holds only a clause *index* (IDs + titles). Every policy claim in a reply must be backed by a same-turn `search_policy` in the trace.
- **Logic in code.** Business days, the 30-day return window, the 48-hour damage window, category bans, and rule order live in Python — not in the prompt.
- **Per line item.** Mixed orders (e.g. TR-4522 tee + socks) get separate verdicts.
- **Escalation is success when required.** Lost parcels and similar cases must hand off; that is not a failure mode.

Trade-offs, full limitation list, and five ops discovery questions: [SOLUTION.md](SOLUTION.md).

---

## Data

| File | Role |
|---|---|
| `data/orders.json` | Four customers (`C-100`…`C-103`) and ten orders (`TR-4521`…`TR-4530`). Loaded read-only. `_note_for_designers` fields are stripped at load and never reach replies, traces, or logs. |
| `data/trendly_policy.md` | Sole policy source of truth. Parsed into addressable clauses (e.g. `2.3`). Keyword search returns generous top-k; on a weak match it also returns the full clause index so the model can re-query by ID instead of falsely saying “not covered.” |

Unknown order IDs return “not found” — never a fuzzy match to a real order. `null` fields are reported as unavailable, never invented.

---

## Eligibility (deterministic)

`check_eligibility(order_id, sku, intent)` with `intent` in `{return, exchange_size, exchange_other, damage_claim}` runs this chain **in order**, short-circuiting on the first blocker:

| Step | Check | Idea |
|---|---|---|
| 0 | Order state | Cancelled → no. Lost in transit → escalate (not a return). Not delivered → window not started |
| 1 | Damage claim | Within 48h of delivery → eligible under damage rules even for non-returnable categories; past 48h → refuse (may offer human review) |
| 2 | Return window | More than 30 calendar days since delivery → refuse |
| 3 | Category | Innerwear/socks, jewellery, beauty, masks, gift cards → refuse for normal return |
| 4 | Final sale | Size exchange only |
| 5 | Exchange type | Colour/style exchanges refused; size only |
| 6 | Footwear | Eligible with original-box caveat and ₹300 deduction note |

**Delay credit (separate from returns):** an order is “delayed” only when more than **3 business days** (Mon–Fri) past `expected_delivery`. Offering the ₹250 store credit earlier is an unauthorised credit. That check is re-enforced inside `issue_delay_credit`, not only in the prompt.

**Clock:** all date math goes through `config.now()`. The CLI and tests default to a frozen clock at **2026-08-04** so behaviour matches the dataset matrix. The live `/chat` API uses wall-clock time unless overridden in-process.

---

## Tools

| Tool | Purpose |
|---|---|
| `lookup_order` | Exact order fetch; Tier-0 fields without verification |
| `search_policy` | Keyword clause retrieval (+ index fallback on weak match) |
| `check_eligibility` | Per-SKU verdict with clause IDs, reasons, refund route |
| `verify_customer` | Match email or phone to the order’s customer (Tier 1) |
| `initiate_return` | Mock RMA + pickup / self-ship next steps (re-checks eligibility) |
| `issue_delay_credit` | ₹250 credit only if business-day delay threshold is met |
| `escalate_to_human` | Structured handoff summary; session marked escalated |

Adding a new tool is meant to stay local to the tools package and prompt wiring; see SOLUTION.md for the NFR-7 packaging note.

---

## Tiered disclosure

| Tier | Without verification | Needs matching email or phone |
|---|---|---|
| **0** | Status, ETA, tracking number, item names, policy answers | — |
| **1** | — | Customer name/email/phone; `initiate_return`, exchange, delay credit |

Failed verification refuses the Tier-1 step without revealing who owns the order; Tier 0 still works. Once a session is verified as customer X, other customers’ orders are refused.

---

## API

**`GET /health`** → `{"status": "ok"}`

**`POST /chat`**

```json
Request:  { "session_id": "uuid", "message": "string" }
Response: {
  "session_id": "uuid",
  "reply": "string",
  "state": { "verified": true, "active_order": "TR-4530", "escalated": false },
  "trace": [ { "tool": "check_eligibility", "input": {}, "output": {} } ]
}
```

Server-side turn logs keep the tool trace but scrub PII down to order ID (no name, email, or phone in logs).

---

## Frontend

Single-page Next.js chat (`web/`): message list, composer, suggestion chips, status strip (active order / verified / escalated), and a collapsible **tool trace** under each assistant message showing tool order and §clause chips. The browser calls the FastAPI origin directly via `NEXT_PUBLIC_API_BASE_URL` (CORS allowlist on the backend).

---

## Repo layout

```
app/
  config.py, dates.py, main.py, cli.py, api_models.py, turn_log.py
  agent/          ReAct loop, dispatch, system prompt
  tools/          Schemas, registry, lookup/policy/eligibility/actions/escalation
  eligibility/    Pure-function rule chain (no LLM)
  policy/         Clause parse + keyword search
  orders/         Read-only orders.json loader + contact match
  session/        In-memory SessionState + disclosure gates
data/             orders.json, trendly_policy.md — read-only
web/              Next.js chat UI
tests/            Unit tests + live scripted harness (T1–T6)
```

---

## Quickest local smoke

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY

python -m app.cli -m "where is TR-4525?" --trace
```

CLI freezes the clock to 2026-08-04 by default so delay / return-window behaviour matches the dataset. Pass `--live-clock` for wall time. Interactive: `python -m app.cli`.

---

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
```

**Env (backend `.env`):** `ANTHROPIC_API_KEY`, `FRONTEND_ORIGIN` (comma-separated origins).  
**Env (frontend `.env.local`):** `NEXT_PUBLIC_API_BASE_URL`.

---

## Tests

```bash
pytest           # unit + harness; live tests skip without ANTHROPIC_API_KEY
pytest -m live   # scripted multi-turn conversations against the real model
```

The live harness asserts on reply *and* trace — including that policy claims are preceded by `search_policy` in the same turn.

---

## Railway (two services, one repo)

| Service | Root directory | Public URL role |
|---|---|---|
| Backend | repo root | FastAPI `/health`, `/chat` |
| Frontend (`trendly-web`) | `web` | Next.js chat UI |

**Backend env:** `ANTHROPIC_API_KEY`, `FRONTEND_ORIGIN` (e.g. `https://trendly-web-production.up.railway.app,http://localhost:3000`)

**Frontend env (set before first build):** `NEXT_PUBLIC_API_BASE_URL=https://trendly-production.up.railway.app`

Backend start (`railway.toml` / `Procfile`):

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Frontend start (`web/railway.toml`):

```text
npx next start -H 0.0.0.0 -p $PORT
```

---

## Known limits (summary)

- Sessions are **in-memory** — process restart clears chat context.
- Actions are **mocked** (no real RMA, carrier booking, or credit issuance).
- Orders have **city but no pincode** — pickup vs self-ship cannot be decided; both paths are offered.
- **No stock feed** — unavailable-size → refund is stated as a rule, not checked.
- Wall-clock **48-hour damage** path is expired for all delivered sample orders; the eligible path is shown under a frozen clock in tests/CLI.

Full list, trade-offs, and five questions for Trendly ops: [SOLUTION.md](SOLUTION.md).

---

## AI usage and cost (NFR-1)

**Runtime model.** The agent calls Anthropic’s API with `claude-sonnet-4-5`, `temperature=0`, and a hard cap of 6 tool steps per turn (`app/config.py`). This uses Anthropic API / trial credit — **not** free-tier-only hosting. The assignment brief’s “free tiers only” line does not match this choice: Sonnet-class quality was kept for guardrail and policy-grounding behaviour; Haiku would be the fallback only if quota forced it.

**What was hand-designed vs assisted.** Architecture, requirements, eligibility rule order, and the design principles were written by hand. Implementation and prompt iteration were assisted by Cursor. Every change to the system prompt is logged in [PROMPTS.md](PROMPTS.md) with before/after text and the failure that triggered it. Deterministic logic (dates, eligibility, disclosure gates) is plain Python — not delegated to the model.

**Secrets.** Set `ANTHROPIC_API_KEY` in `.env` locally and as a Railway backend variable. It is never committed (`.env` is gitignored).

---

## Further reading

| Doc | Contents |
|---|---|
| [SOLUTION.md](SOLUTION.md) | Architecture, trade-offs, limitations, five ops discovery questions |
| [PROMPTS.md](PROMPTS.md) | Prompt versions and the failure each revision fixed |
| `data/trendly_policy.md` | Policy source of truth |
| `data/orders.json` | Fixed evaluation dataset |

Local working notes such as `SRS.md` / `DEV_LOG.md` may exist in a clone but are gitignored and are not part of the pushed deliverable.
