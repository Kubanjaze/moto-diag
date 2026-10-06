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
