# Phase 209D — Whose spend is it

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-17

---

## Goal

F78, as the operator revised it on 2026-09-17 after looking at the ledger:
**build the instrument, don't ship the number.**

Total spend to date is **32¢ across 4 calls**. At measured prices $25/month
is ~2,500 text diagnoses, ~500 sweeps (~17/day) or ~190 video questions
(~6/day) — not a limit a one-person shop reaches by working, which makes a
cap a brake on a runaway (a leaked key, a retry loop) rather than a budget.
A number chosen from four samples would be a guess presented as a safeguard.

So this phase makes spend attributable and visible per shop, builds the
block, and leaves it **off by default**. The number gets chosen later, from
real months.

Numbered **209D**, after 209C. Phase 210 stays gated on the operator.

## Step 0 — findings

**S0-1. 🚨 The cap the ticket described would have been a silent no-op.**
All four `cost_events` rows have `shop_id = NULL`, so
`shop_cost_this_month(shop)` reads $0 for every shop and a cap enforced
through it could never trigger. This is the precondition F78 recorded, and
it's the real work of the phase.

**S0-2. `cost_cap_monthly_usd_cents` is a server setting, not a per-shop
column.** It lives in `core/config.py` (`Settings`), defaults to **0**, and
`shop_cost_this_month`'s docstring describes a soft warning: *"the cap does
NOT block"*. The ticket, and the 209B decisions table, described it as a
per-shop value. Recorded and corrected; 0 keeps its meaning as off.

**S0-3. A session has no shop, and no link to a work order.**
`diagnostic_sessions` carries `user_id` (Phase 178) and `customer_id`
(migration 046) and nothing else that resolves an owner. Migration 046 is
the pattern to copy: `ALTER TABLE ... ADD COLUMN` with a `DROP COLUMN`
rollback.

**S0-4. Two of the four kinds already attribute.** `transcript_pipeline`
passes `shop_id` for `whisper` and `claude_extraction`, because voice lives
under a shop-scoped work-order route. The gap is vision and text.

**S0-5. The vision pipeline already accepts `shop_id`; nothing passes it.**
`VisionAnalyzer.analyze_video_frames` and `answer_question_about_frames`
take the parameter and forward it to `record_vision_cost`. Their two callers
— `media/analysis_worker.py` (the automatic sweep) and the ask route in
`api/routes/videos.py` — both hold the video's row, which carries
`session_id`. So the chain is video → session → shop.

**S0-6. Text diagnosis is CLI-only.** There is no diagnosis route in the
API: the phone cannot run one. `record_diagnosis_cost` is called inside
`DiagnosticClient`, which knows nothing about sessions, so the shop has to be
threaded in from the CLI, which does know.

**S0-7. Per-shop reporting already exists.** `motodiag costs report` takes
`--shop` and `--this-month`, and `--this-month` is documented as matching
what the cap measures. It has nothing to report only because the rows carry
no shop.

**S0-8. Each user belongs to exactly one shop today** (`shop_members`:
user 1 → 1 shop, user 2 → 1 shop), and `list_shops_for_user` exists in
`shop/rbac.py`. A single membership is what makes stamping a session
unambiguous now, without the app having to send anything.

## Scope

1. **Migration 061** — `diagnostic_sessions.shop_id`, nullable, referencing
   `shops(id) ON DELETE SET NULL`, with an index. Rollback drops both, as
   migration 046 does. **No backfill:** attributing past sessions from the
   owner's membership would be a guess about work already done, and it
   changes no ledger row (those are NULL regardless).
2. **Sessions get stamped when created.**
   - API: `SessionCreateRequest` accepts an optional `shop_id`. If given,
     the caller must be an active member (403 otherwise). If omitted, it
     resolves to the user's single active membership, or stays NULL when
     they have none or several.
   - CLI: `diagnose start|quick --shop ID`; when omitted, the one shop in
     the database if there is exactly one, else NULL.
3. **Every AI call records the shop.**
   - Sweep and guidance: resolve video → session → `shop_id` and pass the
     parameter the pipeline already has.
   - Text diagnosis: thread `shop_id` from the CLI's session through
     `DiagnosticClient.diagnose` into `record_diagnosis_cost`.
   - Voice: already attributed; a test pins that it stays so.
4. **The brake, off by default.** New `shop/cost_cap.py`:
   `cap_cents()` (0 = off) and `check_cost_cap(shop_id)` raising
   `CostCapExceeded`. Checked before each paid call:
   - the ask route → a ProblemDetail the app can show;
   - the sweep worker → skips the call, leaves the video retryable;
   - the CLI diagnose → a clear error instead of a charge.
   With the default 0, nothing blocks — pinned by a test that spends past
   any plausible cap and still succeeds.
5. **`motodiag costs report`** names the cap when one is set (`cap $25.00,
   spent $3.12, remaining $21.88`) and says `no cap set` when it isn't, so
   the number is visible where the spend is.

## Non-goals

- **Choosing the number.** That is the point of the phase: it waits for
  real months.
- **A per-day brake.** Offered and not chosen; revisit with the number.
- **The app sending its active shop.** Server-side resolution covers
  today's single-membership reality. File as an F-ticket for when a
  technician belongs to two shops.
- **Backfilling old sessions or old cost rows.**
- **Per-session cost attribution.** Migration 060 already recorded why
  `cost_events` has no `session_id`, and nothing here needs one.

## Verification Checklist

- [ ] Migration 061 applies and rolls back; the column is gone after rollback
- [ ] A session created over the API is stamped with the caller's single shop
- [ ] An explicit `shop_id` the caller is not a member of is refused (403)
- [ ] An explicit `shop_id` the caller is a member of is stamped
- [ ] A user with no membership creates a session with no shop, and it still works
- [ ] `diagnose quick --shop` stamps; without it, a single-shop database resolves
- [ ] A video question records a `vision_guidance` row carrying the shop
- [ ] An automatic sweep records a `vision_sweep` row carrying the shop
- [ ] A CLI diagnosis records a `text_diagnosis` row carrying the shop
- [ ] Voice rows still carry the shop (whisper + claude_extraction)
- [ ] **With the default setting, nothing is ever blocked**, even past $25
- [ ] With a cap set and exceeded: the ask route refuses before paying
- [ ] With a cap set and exceeded: the sweep is skipped, the video stays retryable
- [ ] With a cap set and exceeded: the CLI refuses before paying
- [ ] Under the cap, everything proceeds
- [ ] `costs report` shows the cap, the spend and the remainder; says so when no cap is set
- [ ] `shop_cost_this_month` returns a real number for a shop that spent
- [ ] Mutations: drop each stamp; drop each `shop_id` pass-through; make the cap default non-zero; check the cap after the call instead of before; ignore the membership check — each caught
- [ ] The 209B reachability gate still passes
- [ ] Full regression green; production DB untouched

## Risks

- **A new column on a hot table.** Nullable and indexed, no backfill, and
  the rollback is the documented `DROP COLUMN` form from migration 046.
- **The block is code nobody runs by default.** That's the decision, so it
  is tested on both sides: off means never blocks, on means blocks before
  paying. Without both, "off by default" would be indistinguishable from
  "doesn't work".
- **Threading `shop_id` through `DiagnosticClient`** touches the AI client's
  signature. It stays optional, and the existing test doubles take
  `**kwargs`.
