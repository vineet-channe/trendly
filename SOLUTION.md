# Solution — Trendly Agentic Support Assistant

## Architecture

Two Railway services, one repo: a Next.js chat UI (`web/`) talks HTTPS/JSON to FastAPI (`POST /chat`). Each turn runs a hand-written ReAct loop against Claude tool-use (`app/agent/`), capped at six tool steps. Tools call into four deterministic layers — order store, policy index, eligibility engine, and in-memory session state — then the API returns `session_id`, `reply`, `state` (`verified`, `active_order`, `escalated`), and a `trace` of every tool call.

```
Browser  →  POST /chat  →  ReAct loop (Claude)  →  tools
                                        ├─ orders/      (orders.json, read-only)
                                        ├─ policy/      (clause index + keyword search)
                                        ├─ eligibility/ (pure rule chain, per SKU)
                                        └─ session/     (in-memory SessionState)
              ←  reply + state + trace
```

Seven tools: `lookup_order`, `search_policy`, `check_eligibility`, `verify_customer`, `initiate_return`, `issue_delay_credit`, `escalate_to_human`. SRS §3.1’s flat filenames became `app/<area>/` packages for the ~150-line file cap; responsibilities are the same.

Two design constraints shape the whole stack:

- **P1 — Policy is retrieved, never memorised.** The system prompt holds only the clause *index* (IDs + titles). Every customer-facing policy claim must come from a same-turn `search_policy` call. The UI surfaces that trace; the live harness asserts the grounding rule on clause citations.
- **P2 — Deterministic logic lives in code.** Date math, business-day delay, category exclusions, and eligibility precedence run in Python. The model chooses tools and phrases results; it never computes eligibility. ₹250 delay-credit *issuance* is code-gated — `issue_delay_credit` re-checks the business-day threshold before acting.

## Trade-offs

**Tiered disclosure vs hard authentication.** Tier 0 (status, ETA, tracking, item names, policy) answers on `order_id` alone. Tier 1 (personal details, returns, delay credit) requires a matching email or phone, gated in dispatch via `verify_customer` / disclosure helpers — not prompt-only. Gating *all* lookups behind verification would be safer, but would break scripted evaluation turns like “where is TR-4521?” with no identifier available. Ownership and actions stay protected; ordinary status lookup stays answerable (SRS §4.2).

**Keyword retrieval + index fallback vs embeddings.** Policy search is token-overlap over clauses. On a weak match it returns generous top-k *plus* the full clause index (P7) so the model can re-query by ID instead of falsely concluding the policy is silent. At real policy scale this would need embeddings; for this clause set and paraphrases like “can I get my money back?”, the fallback is enough.

**In-memory sessions.** State is keyed by `session_id` in process memory. Restarts lose context; there is no horizontal scaling. Persistence would add deployment surface without adding evaluated capability for this assignment.

**NFR-7 file splits.** The ~150-line cap forced packages (`tools/`, `eligibility/`, `agent/`, plus `contacts` / `disclosure` for Tier-1) instead of single files. Adding a tool can touch more than `tools.py` + `prompts.py` (schemas, registry, dispatch gates). That is a documented deviation from the ideal two-file rule, accepted to keep files reviewable and verification enforceable in code.

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
8. **No stock data** — §4.3’s unavailable-size → automatic refund is stated as a rule, not checked. Final-sale items also conflict here: §2.4 forbids refunds, so an unavailable size needs human confirmation rather than a silent auto-refund.
9. **No public-holiday calendar** — business days are Mon–Fri only, so §1.1 / §1.5 thresholds may be off around holidays.
10. **§6.1 48-hour damage window** has expired for every delivered order on wall-clock dates. CLI and tests freeze `config.now()` at 2026-08-04; **live `/chat` uses wall-clock**, so delay / return / damage behaviour on Railway can drift from the SRS §4.1 matrix (notably TR-4521 becomes delayed once more than three business days have passed — from 2026-08-06 onward).
11. **No delivered footwear order** — TR-4525’s sneakers are `delayed`, so §2.5’s original-box condition and ₹300 deduction never surface through real `check_eligibility` rows.

## Five discovery questions for Trendly ops

*(Q1–Q5 target computable data / policy-resolution gaps — not demo-only limits like #10–#11.)*

1. Will order records include a delivery pincode (or a serviceability flag) so the agent can choose §5.1 reverse pickup vs §5.2 self-ship instead of always offering both?
2. Should lost-parcel detection also use “no tracking movement for 10 consecutive days,” and is a tracking-event feed available to compute that?
3. Is prior exchange history available from OMS so §4.4 can be enforced across sessions, not only within one chat?
4. When a requested size is unavailable, should §4.3’s auto-refund always apply — and if the item is **final sale**, does that override §2.4’s no-refund rule, or should the agent always escalate?
5. Should business-day math for dispatch promises and the §1.5 delay credit include a public-holiday calendar, and who owns that calendar?
