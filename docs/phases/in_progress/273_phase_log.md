# Phase 273 — Track O batch 4: payments through Stripe — phase log

**Status:** 🚧 In progress
**Branch:** `phase-273` (Opus session, main checkout, the only writer)

---

### 2026-10-06 — Opened: Track O batch 4

The prompt is `docs/prompts/273_track_o_batch4_stripe.txt` (merged in
`78c79ed`). Row 273 reads "Stripe Connect, card terminals, invoicing,
subscription billing". It carries this batch and folds no other row. It
is the last batch before Gate 16 (292).

The operator's earlier words the prompt carries, from the triage report
(`docs/reports/2026-09-28_track_o_triage.md`, decision 3, verbatim in
the report): the backend stays tailnet-only, so in development Stripe's
webhooks reach it through `stripe listen`. And, from 281's prompt, the
rules for outbound calls: "tests use recorded fixtures, never live
endpoints; the app degrades cleanly when a service is down (shown to the
user, never silently empty); no live API call during the build except one
smoke call per service, logged."

Read first: the 370 handoff (`docs/handoffs/2026-10-06_370_closed.md`),
the 281 handoff, 281's Step 0, the triage report, and 176's and 169's
documents in `docs/phases/completed/`.

The first commit: **row 273 🚧**. Step 0 next, then a stop for the
operator's forks (Connect, the tier prices, routes or CLI only).

### 2026-10-06 — Step 0: F187 filed, row 371 paused, stop for the operator

The record is `273_step0.md`; Stripe's pages are quoted in
`273_sources.md`. Every measured fact in the prompt re-verified (S0-1),
on code at `78c79ed` and a read-only copy of live (schema 79).

- **F187 filed:** 176's subscription webhook path would not change a tier
  against the API version the SDK pins (`2026-09-30.endive`,
  `stripe==16.0.0`). This phase fixes it.
- **Row 371 ⏸️:** live payments and production webhooks (decision 3).
- **Decided, with the reason in S0-4:** the SDK pin and the API version
  sent; the money columns (invoices' REAL columns stay, read through one
  cents function and a round-trip test; `payments` unused); webhooks
  idempotent and order-independent (subscriptions re-read from Stripe,
  invoice payments one-way); an invoice paid only on the verified
  `payment_intent.succeeded` from the shop's own account with the exact
  amount; Terminal server-driven with automatic capture; live keys and
  live events refused unless prod; keys outside the repo, never in
  `.env`, and the test session proven blind to them; migration 080 new
  tables and two columns on a 0-row table.
- **Stripe's docs were read by this session directly** (about 30 pages,
  fetched as Markdown; 15 of them quoted), following 281's sources
  practice. This was reading for a judgement (the Connect options), not a
  census or an extraction, so it was not routed through Subconscious
  (rule 2).

**Stop (rule 1, real forks):** question 1, Connect (A each shop a
connected account, Stripe carries fees and losses, recommended; B the
platform carries them; C one account, Connect later); question 2, the tier
prices; question 3, CLI only now (recommended, row 372 ⏸️) or routes now
(a planned mobile stop).

### 2026-10-06 — The operator's pick, and v1.0

The operator, verbatim:

> 1A, 2 placeholders, 3A

- **1A:** each shop a connected account (Accounts v2, `merchant`,
  `dashboard: full`, Stripe collects fees and carries losses), direct
  charges, Stripe-hosted onboarding, no application fee.
- **2:** test-mode placeholder prices, marked as placeholders wherever a
  price shows.
- **3A:** CLI only; no route, no snapshot change, no mobile session. Row
  372 ⏸️ takes the payment routes and the app's payment screens.

v1.0 is `273_implementation.md`. Decided while writing it, with the reason:
- **The SDK goes in a `payments` extra,** pinned `stripe==16.0.0`, and
  `server` includes it. The same pattern as `api`: the dev venv has it,
  and 209's no-extras packaging test holds the lazy import.
- **No fake gateway for shop payments.** Tests run the real gateway code
  through the SDK's own `http_client` hook with recorded or built
  responses, so the request shapes are tested, not a stand-in's. With the
  provider set to `fake`, the shop payment commands refuse and say Stripe
  is not configured, rather than pretending money moved.
