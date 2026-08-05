# Solution — Trendly Agentic Support Assistant

## Architecture

Two Railway services, one repo: a Next.js chat UI (`web/`) talks HTTPS/JSON to FastAPI (`POST /chat`). Each turn runs a hand-written ReAct loop against Claude tool-use (`app/agent/`), capped at six tool steps. Tools call into four deterministic layers — order store, policy index, eligibility engine, and in-memory session state — then the API returns `reply`, `state`, and a `trace` of every tool call.

```
Browser  →  POST /chat  →  ReAct loop (Claude)  →  tools
                                        ├─ orders/      (orders.json, read-only)
                                        ├─ policy/      (clause index + keyword search)
                                        ├─ eligibility/ (pure rule chain)
                                        └─ session/     (in-memory SessionState)
              ←  reply + state + trace
```

Two design constraints shape the whole stack:

- **P1 — Policy is retrieved, never memorised.** The system prompt holds only the clause *index* (IDs + titles). Every customer-facing policy claim must come from a same-turn `search_policy` call, which the UI and the live harness verify from the trace.
- **P2 — Deterministic logic lives in code.** Date math, business-day delay, category exclusions, and eligibility precedence run in Python. The model chooses tools and phrases results; it never computes eligibility or invents a ₹250 credit.

## Trade-offs

**Tiered disclosure vs hard authentication.** Tier 0 (status, ETA, tracking, item names, policy) answers on `order_id` alone. Tier 1 (personal details, returns, delay credit) requires a matching email or phone. Gating *all* lookups behind verification would be safer, but would break scripted evaluation turns like “where is TR-4521?” with no identifier available. Ownership and actions stay protected; ordinary status lookup stays answerable (SRS §4.2).

**Keyword retrieval + index fallback vs embeddings.** Policy search is token-overlap over clauses. On a weak match it returns generous top-k *plus* the full clause index (P7) so the model can re-query by ID instead of falsely concluding the policy is silent. At real policy scale this would need embeddings; for ten clauses and paraphrases like “can I get my money back?”, the fallback is enough.

**In-memory sessions.** State is keyed by `session_id` in process memory. Restarts lose context; there is no horizontal scaling. Persistence would add deployment surface without adding evaluated capability for this assignment.

**NFR-7 file splits.** The ~150-line cap forced packages (`tools/`, `eligibility/`, `agent/`) instead of single files. Adding a tool can touch more than `tools.py` + `prompts.py` (schemas, registry, dispatch gates). That is a documented deviation from the ideal two-file rule, accepted to keep files reviewable.

**Mocked actions.** `initiate_return`, `issue_delay_credit`, and `escalate_to_human` return structured mocks — no real RMA, carrier booking, or ticketing.

## Limitations and data gaps

**Design limitations**
1. In-memory session state — no durability or multi-instance sharing.
2. Keyword retrieval — mitigated by P7; would need embeddings at scale.
3. Tiered disclosure is an ownership check, not authentication.
4. Actions are mocked.

**Gaps in the provided data** *(each forces a stated assumption rather than a computed answer)*
5. **No pincode** — only `shipping_city`, so §5.1 pickup vs §5.2 self-ship cannot be determined. Every eligible return offers standard free reverse pickup and mentions self-ship reimbursement (up to ₹150) as the alternative.
6. **No tracking event history** — §1.6’s “no movement for 10 consecutive days” branch is uncomputable; only the carrier-marked `lost_in_transit` status is handled.
7. **No exchange history** — §4.4’s one-exchange-per-item rule is enforced only within a single session (`exchanged_skus`).
8. **No stock data** — §4.3’s unavailable-size → automatic refund is stated as a rule, not checked.
9. **No public-holiday calendar** — business days are Mon–Fri only, so §1.1 / §1.5 thresholds may be off around holidays.
10. **§6.1 48-hour damage window** has expired for every delivered order on wall-clock dates; the eligible damage path is demonstrable only with an injected clock (CLI defaults to 2026-08-04).
11. **No delivered footwear order** — TR-4525’s sneakers are `delayed`, so §2.5’s original-box condition and ₹300 deduction never surface through real `check_eligibility` rows.

## Five discovery questions for Trendly ops

1. Will order records include a delivery pincode (or a serviceability flag) so the agent can choose §5.1 reverse pickup vs §5.2 self-ship instead of always offering both?
2. Should lost-parcel detection also use “no tracking movement for 10 consecutive days,” and is a tracking-event feed available to compute that?
3. Is prior exchange history available from OMS so §4.4 can be enforced across sessions, not only within one chat?
4. How should an unavailable-size exchange auto-convert to a refund (§4.3) when live stock isn’t queryable — poll inventory, always convert, or hand off?
5. Should business-day math for dispatch promises and the §1.5 delay credit include a public-holiday calendar, and who owns that calendar?
