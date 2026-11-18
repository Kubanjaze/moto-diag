# Phase 404 — phase log: what the plans limit, and a payments status that tells the truth (F270, F271, F272, F274)

**Status:** In progress

**Started 2026-11-18** by the Chief Engineer, in a fresh clone of
`phase-404-what-the-plans-limit-and-a` at `dfdad6b`, inside the fleet's
sandbox. The plan is `404_implementation.md` v1.0, approved by the
Executive Officer on issue #68. The plan has "## The database step", so
this build ends after the regression of record with the `deploy` outcome;
the close-out follows the operator's live apply.

## 2026-11-18 — Step 0, re-measured

**The census of paid AI calls.** Command, as the plan names it:
`git grep -n -E 'DiagnosticClient\(|get_anthropic_client\(|Anthropic\(|transcribe\(' -- src`.
Count: **13** hits. Each traced to what reaches it:

| hit | what it is | reached by | held before this phase |
|---|---|---|---|
| `cli/code.py:125` | `DiagnosticClient` for `FaultCodeInterpreter` | `motodiag code <DTC> --explain` | no |
| `cli/diagnose.py:386` | `DiagnosticClient` | `motodiag diagnose quick` / `start` | yes, `_check_cap` |
| `engine/client.py:285` | the SDK client inside `DiagnosticClient` | every `DiagnosticClient` row here | through its callers |
| `intake/vehicle_identifier.py:506` | `Anthropic()` vision call | `motodiag intake photo`, `motodiag garage add-from-photo` | no |
| `media/sim/vision_analyzer_textsim.py:68` | the superseded text-only analyzer | nothing under `src/` imports it (tests only) | not reachable |
| `media/transcript_pipeline.py:123` | Whisper `transcribe` | `POST /v1/shops/{id}/work-orders/{wo}/transcripts` (background task) | no |
| `media/transcript_pipeline.py:215` | `DiagnosticClient` symptom extraction | the same route | no |
| `media/vision_analysis_pipeline.py:223` | a docstring's usage example | — | not a call |
| `media/vision_analysis_pipeline.py:268` | `DiagnosticClient` inside `VisionAnalyzer` | the video question (`api/routes/videos.py`) and the video sweep (`media/analysis_worker.py`) | yes, both |
| `media/whisper_client.py:104` | the definition of `transcribe` | — | not a call |
| `shop/ai_client.py:136` | the definition of `get_anthropic_client` | — | not a call |
| `shop/ai_client.py:154` | the SDK client inside it | `ShopAIClient.ask` | through its callers |
| `shop/ai_client.py:242` | `ShopAIClient.ask`'s live call | `shop labor estimate` / `bulk` (`estimate_labor`), `shop sourcing recommend` (`recommend_source`), `shop priority score` / `rescore-all` (`score_work_order`) | no |

`engine/parts.py`, `engine/repair.py` and `engine/workflows.py` take a
`DiagnosticClient` but nothing under `src/` constructs one for them, so
they are not reached. No API route reaches `ShopAIClient` or
`VehicleIdentifier`. The paid sites this phase adds a check to: the
transcript upload, `code --explain`, the photo identification (both
commands through `VehicleIdentifier.identify`), and the three
`ShopAIClient` functions. `garage add-from-photo` and `shop priority`,
`shop sourcing` are the sites the plan's list did not name; they are
added the same way (the plan: "a paid call the census finds that this
list does not name is added the same way and said in the log").

**The app's three lines** (`../moto-diag-mobile` at `9045c32`), re-read:
- `src/screens/VehiclesScreen.tsx:173`: `if (!quotaLimit) return null;`
  hides the footer when `quota_limit` is null. Agrees with the plan.
- `src/screens/NewVehicleScreen.tsx:360-366`: a 402 shows the title and
  detail with "Upgrade your subscription tier to add more bikes, or delete
  one first." Agrees: a Shop account no longer meets it.
- `src/screens/HomeScreen.tsx:505-507`: prints the quota line only when
  `quota_limit` is not null. Agrees.
None disagrees; nothing is named for the app's own session.

**The line numbers the plan cites**, re-read at `dfdad6b`: registry.py
line 44 (`"shop": 50`), subscription.py lines 69, 89, 92, 109, 115, 125,
main.py lines 178, 196, 198, errors.py line 301, deps.py lines 147-162,
monitor.py line 54, event_feed.py line 418, payments.py lines 102, 130,
149, 157, 170, 189: each holds.

## 2026-11-18 — the build

**F270, the bike limit.** `TIER_VEHICLE_LIMITS["shop"]` and
`TIER_LIMITS[SHOP].max_vehicles` are -1. The two tables are pinned equal by
a test (`test_phase404_bike_limit.py`), rather than one reading the other:
`cli.subscription` stays free of server imports. The module docstring says
what each plan limits.

**F271, the plan's AI figure.**
- The figures are `PLAN_AI_CENTS` in `src/motodiag/shop/cost_cap.py`:
  individual 500, shop 5000, company 15000. `TIER_LIMITS` keeps its own
  floats (5.0, 50.0, 150.0; Company's was 500.0) and a test pins them equal.
- The owner lookup is lifted, not copied: `shop_owner_ids`,
  `highest_active_tier` and `shop_plan` in
  `src/motodiag/billing/subscription_repo.py`. `resolve_tier` ranks the
  owners it finds through `highest_active_tier`; `check_cost_cap` reads the
  shop's plan through `shop_plan`. Never `shops.owner_user_id`.
- `check_cost_cap` raises `PlanAILimitReached` (a `CostCapExceeded`) at or
  past the plan figure, `CostCapExceeded` at or past the brake, the lower
  first. On a tie the plan's refuses, because its message names the plan
  and the day the month turns. The brake's message and class are unchanged.
- `errors.py` has the row 402 `plan-ai-limit-reached`, "Monthly AI
  allowance for this plan reached"; the brake's row stays.
- The call sites the census found unchecked now check before paying: the
  transcript upload (after the quota check, before the audio is stored);
  `code --explain` (`_run_explain`, the database's only shop, as
  `diagnose`); the photo identification (`VehicleIdentifier.identify`,
  after the cache lookup, before the vision call; this covers `intake
  photo` and `garage add-from-photo`); `estimate_labor`,
  `score_work_order` (the work order's shop) and `recommend_source` (a
  part has no shop: the database's only one), each on its paid branch.
  The five `shop` commands that reach those three print the refusal as one
  red line and exit 1 (`_refused_spend` in `cli/shop.py`); before, a
  `RuntimeError` there would have been a traceback.
- Company's `max_locations` is 3. Filed **F282**: the location limit and
  the people limit are shown and kept nowhere.

**F272, the names.** "Individual: for your own bikes", "Shop", "Company".
`format_tier_comparison` carries the three full names on a line across the
top of the table and heads each column with the name's first part; every
line is 76 characters, as before.

**F274, the feed's status.**
- `monitor.checkin_answer` returns `CheckinAnswer(ok, answer)`;
  `monitor.checkin` is unchanged in shape (a bool) and calls it, so the 371
  callers and tests are untouched.
- Migration 090 adds `stripe_feed_checkins` and
  `idx_stripe_feed_checkins_sent_at`; `SCHEMA_VERSION` is 90. Scope file:
  `404_deploy_scope.json`.
- `_Job.checkin` writes one row per check-in it sends (never with the alarm
  off); at the day's turn the job deletes this table's rows older than 30
  days.
- `payments feed status` prints a "Last check-in:" line after
  `_alarm_line`'s when the alarm is on, and `_status_problems` adds the three
  reasons. `_alarm_line` and `feed run` are unchanged.
- `docs/guide/payments.md`, "Seeing that it is running", describes both.

**Existing pins changed, each with its reason in the commit:**
`test_phase109_cli_foundation.py` (Shop's bikes -1, Company's locations
3); `test_phase177_vehicle_api.py` line 239 (shop -1) and
`test_shop_tier_gets_bigger_quota` (null quota). A fifth, which the plan
did not name: `test_phase177_vehicle_api.py::TestQuota::test_shop_limit_50`
asserted the 51st Shop bike refused; it became `test_shop_has_no_limit`.
It pins the behaviour K84 removes, so it is inside the approved change and
not a stop.

**The quality counts** after the build: ruff 1108, mypy 202, as pinned.
One mypy error the first draft added (`cost_cap.py`, the plan's type) was
fixed before any commit. The F9 lint: clean.

**`COLLECTED_TEST_FLOOR`** 12686 → 12779, by a diff of collected ids
against `dfdad6b` (12687): +93 −1 (the five new files, 92; the renamed
`test_shop_has_no_limit` in, `test_shop_limit_50` out).

**On the old code** (the five new files copied into a worktree at
`dfdad6b`, run with its own `src/`): `test_phase404_plan_ai_limit.py` and
`test_phase404_plan_names.py` fail at import (`PLAN_AI_CENTS` does not
exist); in the other three, 17 failed and 4 errored. What stayed green
there: the Individual and Company bike controls, the two tables agreeing
(they agreed on master too, at 50), `checkin` still returning a bool, the
alarm-off control, the no-key and planted-key controls, the day's turn
leaving other tables alone, and the migration's "before" state.

## 2026-11-18 — committed, then the mutations

- `4b07f31`, the build, after `wholetree.sh` (fast: 2743 passed, 10
  skipped, exit 0) and `wholetree.sh --full` on the staged tree (5212
  passed, 36 skipped, exit 0; record for `dfdad6b`'s tree as staged).
- **Mutations, `404_mutate.py`: 26/26 red** (`404_mutate.out`). The plan's
  seven are P1 (figure off by one), P3 (`shops.owner_user_id`), P4 (every
  member, the caller's own included: the check has no caller, so the
  caller's subscription reaches it only as a member's; the API test with a
  Company technician under an Individual owner goes red), S1 (the check
  after the paid call), F1 (a 401 recorded as accepted), F3 (the stale
  window at one interval) and N1 ("Solo Mechanic"). The other nineteen
  remove each call site's check, the CLI's red line, the error row, the
  housekeeping and the rollback's drop.
- A first run of the script was stopped by the sandbox's ten-minute limit
  on a background command, after nine mutations, all red. It was stopped
  while S4 was applied, and the harness's restore did not run: the photo
  identification's check line was missing from `vehicle_identifier.py`.
  Found by checking that each mutation's original text occurs exactly once,
  restored with the Edit tool before the commit, and the whole run was
  repeated with a longer limit. Not a defect in the shipped code.
