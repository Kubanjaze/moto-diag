# Phase 209D — Whose spend is it

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-17 (built 2026-09-17)

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

- [x] Migration 061 applies and rolls back; the column is gone after rollback
- [x] A session created over the API is stamped with the caller's single shop
- [x] An explicit `shop_id` the caller is not a member of is refused (403)
- [x] An explicit `shop_id` the caller is a member of is stamped
- [x] A user with no membership creates a session with no shop, and it still works
- [x] `diagnose quick --shop` stamps; without it, a single-shop database resolves
- [x] A video question records a `vision_guidance` row carrying the shop
- [x] An automatic sweep records a `vision_sweep` row carrying the shop
- [x] A CLI diagnosis records a `text_diagnosis` row carrying the shop
- [x] Voice rows still carry the shop (whisper + claude_extraction)
- [x] **With the default setting, nothing is ever blocked**, even past $25
- [x] With a cap set and exceeded: the ask route refuses before paying
- [x] With a cap set and exceeded: the sweep is skipped, the video stays retryable
- [x] With a cap set and exceeded: the CLI refuses before paying
- [x] Under the cap, everything proceeds
- [x] `costs report` shows the cap, the spend and the remainder; says so when no cap is set
- [x] `shop_cost_this_month` returns a real number for a shop that spent
- [x] Mutations: drop each stamp; drop each `shop_id` pass-through; make the cap default non-zero; check the cap after the call instead of before; ignore the membership check — each caught
- [x] The 209B reachability gate still passes
- [x] Full regression green; production DB untouched

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

## Deviations from v1.0

**1. The API does not take a `shop_id`.** v1.0 had the create-session request
accept one, membership-checked. Gate 11 compares the running contract against
the app's committed OpenAPI snapshot, so adding the field means a snapshot
refresh and regenerated types in the mobile repo — for a field the app does
not send and, with one membership each, does not need. The server resolves
the shop instead. When a technician belongs to two shops, the app will have
to say which: **F84**, filed in the mobile tracker.

**2. A capped sweep leaves the video `pending`, not `analysis_failed`.**
v1.0 said "leaves the video retryable" without choosing. `analysis_failed` is
the retryable state, but nothing failed and nothing was attempted; `pending`
is what is true, and it is what a retry would look for. Pinned by a test.

**3. `CostCapExceeded` is a `RuntimeError`.** `motodiag diagnose` already
turns a RuntimeError into a red line and exit 1 — the offline cache-miss
surface — so refusing to spend arrives the same way as any other reason the
command cannot produce a diagnosis, with no new CLI wiring.

**4. Ten schema pins, not the two a grep finds.** Bumping SCHEMA_VERSION to
61 had to touch every `== 60` pin, and they are spelled two ways: the note
inside the 244L pin warns that `test_phase191b_serve_migrations.py` writes
`get_current_version(db_path) == N`. A file-by-file scan found **ten**, in
suites from 184 to 244N. Each carries the 60→61 reason now.

## Results

| | |
|---|---|
| The precondition | closed: a session carries a shop (migration 061), and vision + text spend record it |
| Attribution paths | 4 of 4 kinds: `whisper` and `claude_extraction` already did; `vision_sweep`, `vision_guidance` and `text_diagnosis` do now |
| Who resolves it | API: the caller's single active membership. CLI: `--shop`, else the one shop the database runs. Two of anything → unattributed, never guessed |
| The cap | built, **off by default** (`MOTODIAG_COST_CAP_MONTHLY_USD_CENTS=0`), checked **before** the paid call at all three paid paths |
| Refusal | 402 `ai-spend-cap-reached` on the ask route; the sweep is skipped and the video stays `pending`; the CLI exits 1 without calling the SDK |
| Unattributed work | never refused — a call with no shop cannot be measured against a per-shop ceiling |
| Visibility | `motodiag costs report` names the cap, the spend and the remainder, and says `none set` when there is none |
| 209B gate | caught the wiring: `shop_cost_this_month` was orphan #28 and now has callers, so its allowlist entry was stale and had to go |
| Schema | 60 → **61**; applied to a copy of production: integrity ok, 6 sessions unstamped (no backfill, by design), 37 facts untouched |
| Tests added | **31** |
| Mutations | **16 of 16 caught** |
| Regression | **6,687 passed, 0 failed, 26:19** |

**Mutations**

| | mutation | caught by |
|---|---|---|
| M1 | API sessions are not stamped | `test_the_api_stamps_the_callers_only_shop` |
| M2 | a second membership is guessed at | `test_two_memberships_stay_unattributed` |
| M3 | an inactive membership counts | `test_an_inactive_membership_does_not_count` |
| M4 | two shops in the database get a guess | `test_two_shops_in_the_database_get_no_guess` |
| M5 | the ask route drops the shop | `test_a_video_question_says_who_pays` |
| M6 | the sweep drops the shop | `test_the_sweep_says_who_pays` |
| M7 | the ledger row drops the shop | `test_a_cli_diagnosis_lands_on_the_shops_ledger` |
| M8 | the CLI does not carry the shop into the client | same test, through the real client |
| M9 | the cap defaults to $25 instead of off | `test_the_default_setting_is_no_cap` |
| M10 | the cap is checked after the call | `test_the_video_question_is_refused_before_it_pays` |
| M11 | the sweep ignores the cap | `test_the_sweep_is_skipped_and_the_video_stays_pending` |
| M12 | the CLI ignores the cap | `test_the_cli_refuses_before_it_pays` |
| M13 | the cap fires below the limit | `test_under_the_cap_nothing_happens` |
| M14 | unattributed work is refused | `test_unattributed_work_is_not_refused` |
| M15 | the report hides the cap | `test_it_says_when_no_cap_is_set` |
| M16 | the report shows the wrong remainder | `test_it_shows_the_spend_against_the_cap` |

**What the operator still has to decide:** the number. The ledger can now
answer "what did this shop spend this month" per shop; a few real months are
what should set it. Until then the brake is off and says so.
