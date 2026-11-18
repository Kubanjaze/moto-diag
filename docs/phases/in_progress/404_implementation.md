# Phase 404 — What the plans limit, and a payments status that tells the truth (F270, F271, F272, F274)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-11-18

---

## Goal

The pricing report's step 2, before the first shop pays
(`docs/reports/2026-11-10_mekno_pricing_and_tiers.md`, "What happens next").
Built by the fleet, after 403 and before 334 and 330 (K84). The operator's
words: "yes go with templates, and approve both drafts" (K84), and on the
classification, "A. Let the fleet build 404. I approve the four changes the
survey lists: the Shop plan's bike cap, the Company plan's figures, the plan
names, and the payments status." (K90, quoted in `404_step0.md`).

After this phase:
1. **F270.** A Shop account adds its 51st bike. Individual keeps five.
   Company stays unlimited. The CLI's plan table and the server's limit
   agree, and a test says so.
2. **F271.** Each plan's AI figure is a limit the server keeps, per shop,
   per calendar month: Individual $5, Shop $50, Company $150. Past it, the
   server refuses the next paid AI call with a plain message that names the
   plan and the date the month turns. Every paid AI call the app or the CLI
   can reach is held to it. The server-wide brake,
   `MOTODIAG_COST_CAP_MONTHLY_USD_CENTS` (0, off), is unchanged. Company's
   locations read 3 where the limit is shown; nothing in the code adds a
   location, so nothing keeps it, and a finding says so.
3. **F272.** The plans read "Individual: for your own bikes", "Shop" and
   "Company" in every table that names them, with a test for each.
4. **F274.** The payments feed records each check-in's outcome in the
   database; `payments feed status` names the last check-in's time and
   Sentry's answer, and exits 1 when the last one failed or none succeeded
   within two check-in intervals. A refused check-in turns the status red,
   in a test.

The live step, in the handoff: the server and the payments feed restarted
on the new code, then `motodiag payments feed status` printed and read.

## Logic

Causes and measurements: `404_step0.md`. The Engineer re-measures each
line below before changing it (CLAUDE.md, Step 0), and records the census
in the phase log.

1. **F270, the bike limit** (`src/motodiag/vehicles/registry.py`,
   `src/motodiag/cli/subscription.py`).
   - `TIER_VEHICLE_LIMITS["shop"]` (line 44) becomes `-1`, unlimited, the
     sentinel `check_vehicle_quota` (line 391) and `_quota_for`
     (`src/motodiag/api/routes/vehicles.py` line 197) already read.
     `individual` stays 5 and `company` stays -1. No route changes:
     `POST /v1/vehicles` (line 258) keeps calling the same check.
   - `TIER_LIMITS[SubscriptionTier.SHOP].max_vehicles` (line 92) becomes
     `-1`, so the CLI's "Max vehicles" rows read "Unlimited" for Shop. The
     module's docstring (lines 4 to 6) says what the plans now limit.
   - The two tables may not drift: a test asserts, for each plan, that
     `TIER_LIMITS[plan].max_vehicles == TIER_VEHICLE_LIMITS[plan.value]`
     and `TIER_LIMITS[plan].max_sessions_per_month ==
     TIER_SESSION_MONTHLY_LIMITS[plan.value]`. Whether `TIER_LIMITS` reads
     the server's figures or a test pins them equal is the Engineer's call;
     both tables agreeing is the finish line.
   - **The app's quota wording, checked** (the prompt's item 1).
     `moto-diag-mobile/src/screens/VehiclesScreen.tsx` line 173 hides the
     footer when `quota_limit` is null, which is what the route returns for
     an unlimited plan today for Company and now for Shop; its text names no
     number. `src/screens/NewVehicleScreen.tsx` lines 360 to 366 show the
     402's title and detail with "Upgrade your subscription tier to add more
     bikes, or delete one first.", which a Shop account no longer meets and
     an Individual account still reads truly. `src/screens/HomeScreen.tsx`
     line 507 prints the server's numbers. So no change to the app's own
     text is needed; the Engineer's Step 0 re-measures these three lines
     and names any that disagrees for the app's own session (372B).
   - Finish line: a Shop account's 51st `POST /v1/vehicles` answers 201;
     an Individual account's sixth answers 402 `vehicle-quota-exceeded`;
     the two tables agree in a test; the three app lines are recorded.
2. **F271, the plan's AI figure, kept by the server** (`src/motodiag/shop/cost_cap.py`,
   `src/motodiag/cli/subscription.py`, `src/motodiag/api/errors.py`, and
   each paid call site below).
   - **The figures, in one place on the server:** a table in
     `src/motodiag/shop/cost_cap.py` (or a sibling module under
     `src/motodiag/shop/`, the Engineer's choice) of cents per plan per
     calendar month: individual 500, shop 5000, company 15000. These are
     K84's numbers and no other.
     `TIER_LIMITS[plan].ai_monthly_cost_cap_usd` reads the same figures or
     is pinned equal to them by a test, so the CLI's "AI cost cap / month"
     row (`src/motodiag/cli/main.py` line 198) shows what the server
     enforces: Company's line 125 becomes 150.0.
   - **The shop's plan:** the owner's active subscription,
     `shops.owner_user_id` then
     `motodiag.billing.subscription_repo.get_active_subscription`, the same
     rule `resolve_tier` (`src/motodiag/auth/deps.py` line 129) uses for a
     shop member. A shop whose owner has no active subscription has no plan
     and so no plan figure; the brake alone applies, as it does today
     (a reading, under Rule-1 stops anticipated). A call with no shop
     (`shop_id is None`) is not held to a plan figure, as `check_cost_cap`
     already lets an unattributed call through; attribution is not changed
     here.
   - **The check:** `check_cost_cap(shop_id, db_path)` gains the plan
     figure beside the brake. It reads the shop's spend this UTC calendar
     month through `shop_cost_this_month` (already per shop, already the
     calendar month), and raises before the paid call when the spend is at
     or past the plan's figure, whichever of the plan figure and the brake
     is lower refusing first. The refusal is a subclass of
     `CostCapExceeded`, so every existing handler keeps working
     (`motodiag diagnose` prints it red and exits 1; the analysis worker
     leaves the video pending), and its message names the plan and the
     date the month turns, in plain words, for example: "The Shop plan's
     $50.00 of AI for November is used up. It starts again on 1 December
     2026 (UTC)." The brake's own message and class are unchanged.
   - **The API's answer:** the subclass gets its own row in
     `src/motodiag/api/errors.py`'s table: 402, slug `plan-ai-limit-reached`,
     title "Monthly AI allowance for this plan reached", with the message
     as the detail. The brake's row (`ai-spend-cap-reached`, line 301) stays.
     The app shows a 402's title and detail already (NewVehicleScreen's
     pattern; the video and session screens handle 402 the same way), so
     the new words reach the user without an app change. If this changes
     the API's description so that Gate 11 goes red, the dispatcher's
     app-copy step from Phase 403 refreshes the app's copy; the Engineer
     does not write the app's repository itself.
   - **Every paid AI call the app or the CLI can reach, held to it.** The
     Engineer's Step 0 census is
     `git grep -n -E 'DiagnosticClient\(|get_anthropic_client\(|Anthropic\(|transcribe\(' -- src`,
     each hit traced to the API route or CLI command that reaches it, and
     the list goes in the phase log with the count. What this plan's own
     reading found, to be re-measured:
     - already checked, through `check_cost_cap`: the video question
       (`src/motodiag/api/routes/videos.py` line 541), the video sweep
       (`src/motodiag/media/analysis_worker.py` line 84) and
       `motodiag diagnose` (`src/motodiag/cli/diagnose.py` line 424). These
       gain the plan figure with no change at the call site;
     - not checked today, reached by the app: the voice transcript upload
       (`src/motodiag/api/routes/transcripts.py` line 442 queues
       `run_extraction_pipeline`, which pays Whisper at
       `src/motodiag/media/transcript_pipeline.py` line 123 and Claude at
       line 215). The route is shop-scoped, so it calls `check_cost_cap`
       with its `shop_id` before the audio is stored and the task queued,
       the way the video question checks before the frames are cut;
     - not checked today, reached by the CLI: `motodiag code explain`
       (`src/motodiag/cli/code.py` line 125, no shop), `motodiag intake photo`
       (`src/motodiag/intake/vehicle_identifier.py` line 506, no shop),
       the shop's labor estimate (`src/motodiag/cli/shop.py` line 3131,
       `estimate_labor`, the command's shop), and whatever CLI commands reach
       `parts_sourcing.py` and `priority_scorer.py` through
       `src/motodiag/shop/ai_client.py`. Each calls `check_cost_cap` before
       its paid call; a command with no shop of its own resolves one as
       `motodiag diagnose` does (`_resolve_shop`: `--shop` when given, else
       `only_shop`), and stays unattributed, and unheld, when the database
       runs two shops, as today.
     A paid call the census finds that this list does not name is added the
     same way and said in the log; it is not a stop.
   - **Company's locations.** No code adds a shop location: `max_locations`
     is read only by the CLI's tables (`src/motodiag/cli/main.py` line 196),
     `terminal_locations` is a Stripe Terminal address, and `shops` has no
     parent. So `TIER_LIMITS[SubscriptionTier.COMPANY].max_locations`
     (line 115) becomes 3, the panel's "Physical locations" row reads 3,
     and the Engineer files a finding with the `finding` skill before any
     document cites its number: the location limit is shown and kept
     nowhere, and Company's 3 waits for the code that adds a location. The
     finding may note that `max_users` sits the same way; the people limit
     itself is a non-goal.
   - Finish line: a Company shop with $150.00 of ledger rows this month is
     refused its next paid call, 402 `plan-ai-limit-reached` through the
     API and a red line through the CLI, the message naming "Company" and
     the first of next month; a Shop shop is refused past $50.00 and served
     at $49.99; an Individual past $5.00; the brake at 0 refuses nothing on
     its own; a shop with no plan is held only by the brake; every call
     site in the census has a test that it refuses before paying (the
     stand-in client records no call).
3. **F272, the names** (`src/motodiag/cli/subscription.py`,
   `src/motodiag/cli/main.py`).
   - `display_name` becomes "Individual: for your own bikes" (line 69),
     "Shop" (line 89) and "Company" (line 109). `max_vehicles` for
     Individual stays 5.
   - Every table that names a plan prints `display_name` and no other
     name: the `motodiag tier` panel (`main.py` line 178) already does;
     `format_tier_comparison` (`subscription.py` line 173) names the plans
     in a fixed header today and so prints the three display names, as
     column headers or as a line the table carries, the Engineer's layout,
     with the table still aligned.
   - Finish line: `motodiag tier` on each plan, and `motodiag tier --compare`,
     each print the three names; `git grep -n -F 'Solo Mechanic' -- src`
     and the other two old names find nothing under `src/`.
4. **F274, a payments status that tells the truth**
   (`src/motodiag/telemetry/monitor.py`, `src/motodiag/payments/event_feed.py`,
   `src/motodiag/cli/payments.py`, `src/motodiag/core/migrations.py`,
   `docs/guide/payments.md`).
   - **The answer comes back.** `monitor.checkin` (line 54) returns
     Sentry's answer with the outcome, not only a `bool` and a log line: the
     code and reason ("202 Accepted", "401 Unauthorized") or the exception's
     name on a network failure. The existing callers and their tests
     (`tests/test_phase371_monitor.py`, `tests/test_phase371B_checkin_key_once.py`)
     stay green, by a new return shape they are updated to or a second
     function the job calls; the Engineer's choice, said in the log.
   - **The record.** Migration 090 adds `stripe_feed_checkins` (The
     database step, below). `_Job.checkin` (`event_feed.py` line 418) writes
     one row per check-in it sends: when, whether Sentry accepted it, the
     answer, and the monitor's slug. It never writes when the alarm is off
     (`dsn is None`), as today it never sends. When the day turns, the job
     deletes its own rows older than 30 days from this table only, as
     `limit_check` already runs at the day's turn; nothing else is deleted.
   - **The status.** `feed_status_cmd` (`payments.py` line 170) reads the
     newest row and prints, after the Stripe lines, one line for the alarm
     that names where it checks in, how often, the last check-in's local
     time and how long ago, and Sentry's answer; with no row yet, it says
     so. `_status_problems` (line 130) gains, when the alarm is on: "the
     alarm has never checked in" when no row exists; "the last check-in was
     refused: <answer>" when the newest row was not accepted; "no check-in
     succeeded within two intervals" when the newest accepted row is older
     than `2 * settings.stripe_poll_checkin_s`. Each is a "Not right:" line
     and exit 1, as the Stripe problems are. With the alarm off the line
     reads "Alarm: off: no Sentry DSN" as today and adds no problem.
     `_alarm_line` (line 102) is replaced by, or feeds, the new line; no
     key is ever printed (the 371 mask tests stay).
   - **The guide.** `docs/guide/payments.md`, "Seeing that it is running"
     (lines 52 to 65), describes the new line and the three new reasons for
     exit 1.
   - Finish line: with a stand-in Sentry answering 401 and the job run
     once, `payments feed status` exits 1 and prints the refusal with
     "401"; answering 202, it exits 0 and prints the time and "202"; with
     the newest accepted row planted older than two intervals, exit 1; with
     the alarm off, exit 0 and the old line; the 371 status tests still
     pass; no planted key appears in any output.
5. **Documents.** `docs/FOLLOWUPS.md` gains, at close-out, the closing
   lines for F270, F271, F272 and F274 in the form F273's has, each saying
   "once merged and live" until the handoff records the live step; the
   ROADMAP row moves with the work; the handoff carries the live step as
   one paste block for the home desktop's Ubuntu window, ending in ALL GOOD
   or SOMETHING IS OFF, every `gh` call naming `-R Kubanjaze/moto-diag`
   (R8).
6. **Finish line for the phase:** every test under Tests green and seen
   red on master's code; the mutations red; `COLLECTED_TEST_FLOOR` raised
   by a diff of collected ids; the regression of record inside the fence;
   the database step applied by the operator; `verify_phase.sh`; the
   handoff.

## The change log's three newest entries

- **2026-10-29 — rule 6: the code's counts only improve, and the weekly page (Phase 393, K54).** Became `tests/test_phase393_quality_ratchet.py`: the six measured counts against their pins both ways, and the coverage gate wired into `.claude/skills/closeout/regression.sh`. This phase adds no finding to any count and lowers no pin; the new check at each call site is one function call, not a new `except Exception: pass` block.
- **2026-10-26 — R8: an operator paste block's `gh` names its repository (before Phase 391, F222).** Became R8 in `.claude/skills/closeout/roadmap_check.py`, run with every suite and on every push. The handoff's live-step block carries `-R Kubanjaze/moto-diag` on every `gh` call or makes none.
- **2026-10-22 — `fleet` joins the procedure folders (after Phase 387).** No check: the entry says the row is text only and no check reads the table. This phase changes nothing under `.claude/skills/fleet/`.

## The plan of record

'Next, in order' #16 of `docs/reports/2026-10-12_plan_of_record.md`:
"16. 404 (shop, built by fleet); needs the operator: nothing; from:
2026-11-15 · K84".

The dated entry under "Changes to the order", 2026-11-15: "**2026-11-15:
403, 404 and 334 go after 372 and before 330 (K84).** Phase 372 lost more
than two days to stops that left its commits behind and to two refreshes of
the phone app's copy by hand (F266, F231, F276). The pricing report asks for
its step 2 before the first shop pays (F270, F271, F272, F274). And Mekno
shows a user no terms yet." Its 404 line: "**404, what the plans limit, is
built by the fleet.** Its four plan decisions, and that they change limits,
are in K84 and in its prompt."

K84 (2026-11-15), the operator's words "yes go with templates, and approve
both drafts"; the part on this phase: "(2) 404
(`docs/prompts/404_the_plans_limits_and_the_feed_status.txt`), built by the
fleet: Shop with no bike limit (F270); Company at 3 locations and $150 a
month of AI, and each plan's AI figure, $5, $50 and $150 a month per shop, a
limit the server keeps, with the server-wide brake staying off (F271); the
names "Individual: for your own bikes", "Shop" and "Company" (F272); and the
payments feed's status (F274). These change limits, so the words are the
operator's rule-1 approval of exactly these four, which 404's prompt
carries; the record itself answers no rule-1 stop (K50)."

K90 (2026-11-18) is the classification decision, quoted in `404_step0.md`:
"A. Let the fleet build 404. I approve the four changes the survey lists:
the Shop plan's bike cap, the Company plan's figures, the plan names, and
the payments status. Treat the survey's "reshape" as "extension" with this
decision written beside it, once the plan stage's stop note is on issue 68."
On this branch `docs/decisions.md` ends at K89; K90's row is the Yeoman's,
on master, and this plan cites it from the Step 0 report.

The phase is a shop phase, not fleet-only: it changes `src/motodiag/`,
`tests/` and `docs/`, and nothing under `.claude/skills/fleet/`. No
"Unblocks:" line under K43 applies.

## Rule-1 stops anticipated

- **A real fork: none known.** The Step 0 report leaves no choice between
  two plans that would ship different things. Where this plan leaves a
  build choice (the return shape of `monitor.checkin`, the compare table's
  layout, whether `TIER_LIMITS` reads the server's figures or is pinned
  equal to them), either choice ships the same behaviour.
- **A threshold or a rule's definition: four changes, approved; anything
  else is a stop.** K84 and K90 are the operator's approval of exactly
  these: Shop's bike limit removed; Company at 3 locations and $150 a month
  of AI; each plan's AI figure, $5, $50 and $150, a limit the server keeps,
  the brake left at 0; the three names. The Engineer applies those values
  literally. Foreseeable stops, each with kind `threshold-or-rule`: a
  figure for a shop whose owner has no active subscription; any number for
  the brake; any change to Individual's 5 bikes, Shop's 10 people, 1
  location or 500 diagnoses a month, or Company's unlimited bikes and
  diagnoses; a model-access change; a limit kept on locations or people.
  **Two readings, recorded, told to the operator with the pull request:**
  (1) a shop with no plan is held only by the brake, as an unattributed
  call is today, since K84's figures are per plan; (2) the month is the UTC
  calendar month, as `shop_cost_this_month` already counts it, and the
  date the message names is the first of the next month in UTC.
- **A test that cannot be made green: none known.** Three existing pins
  change with their reason in the commit message:
  `tests/test_phase177_vehicle_api.py` line 239 (shop 50, an `f9-noqa`
  contract pin), `tests/test_phase109_cli_foundation.py` lines 63 (shop
  bikes) and 75 (Company locations). If the SSOT lint
  (`tests/test_phase191d_ssot_constants_lint.py`) or any other test pins a
  behaviour this phase must change and cannot be made green inside K84's
  scope, the Engineer stops.
- **A login or a credential: none.** The Stripe keys and the Sentry DSN
  stay with the operator; every test uses the 371 stand-ins
  (`FakeTransport`, `FixtureHTTP`) and planted values that never print.
- **A live-database change that alters or deletes rows: none planned.**
  Migration 090 adds one empty table and one index (The database step). The
  limits apply at the next call and rewrite no stored row: no
  `subscriptions`, `cost_events`, `vehicles` or `shops` row changes. A
  migration that would alter or delete an existing live row, or any write
  that rewrites stored plan data or a shop's counts, is a stop.

## The database step

- **What the change does to the live database:** migration 090 adds one
  empty table and one index, and records version 90 in `schema_version`.
  The payments feed job writes the table; `payments feed status` reads it;
  nothing else touches it.
- **What it adds:** the table `stripe_feed_checkins`, one row per check-in
  the feed sends to Sentry, with columns `id` (integer primary key,
  autoincrement), `sent_at` (text, not null, UTC), `ok` (integer, not null,
  0 or 1), `answer` (text, not null: the HTTP code and reason, or the
  exception's name) and `slug` (text, not null, the monitor's name); the
  index `idx_stripe_feed_checkins_sent_at` on `sent_at`; and one
  `schema_version` row. Exactly these, as `404_deploy_scope.json` names
  them. The rollback drops the index and the table.
- **What it changes or deletes:** no existing live row is changed or
  deleted, and no existing table, column, index or trigger is rewritten.
  The feed's own 30-day housekeeping deletes only rows this table will
  hold, none of which exist when the migration is applied. So it is not a
  rule-1 stop: the Engineer stops after the regression of record with the
  `deploy` outcome, and the operator applies it from one paste block on the
  home desktop, before the close-out (K18, K58).
- **The one sentence for the operator** (`live_change`): "Adds one new,
  empty table where the payments feed will write each check-in it sends to
  Sentry and the answer it got, and one index; nothing already in the live
  database is changed or removed."
- **After it:** the running feed is still master's code and writes nothing
  to the table until the handoff's live step restarts the server and the
  feed on the merged code; the first check-in after that writes the first
  row, and `payments feed status` reads it.

## Tests

- `tests/test_phase404_bike_limit.py`: a Shop account adds 51 bikes through
  `POST /v1/vehicles`, each 201, and the list shows `quota_limit` null; an
  Individual account's sixth is 402 `vehicle-quota-exceeded` (the control);
  a Company account is unchanged; `TIER_LIMITS` and `TIER_VEHICLE_LIMITS`
  agree for every plan, and so do the session limits.
- `tests/test_phase404_plan_ai_limit.py`: on a fresh database with a shop,
  an owner on each plan and planted `cost_events` rows: Company at $150.00
  refused, at $149.99 served; Shop at $50.00 refused; Individual at $5.00
  refused; the refusal's message names the plan and the first of next
  month; through the API it is 402 `plan-ai-limit-reached` and the brake's
  row is untouched; the brake at 0 alone refuses nothing; a shop with no
  plan is refused only when the brake is set; the lower of plan and brake
  refuses first; each call site in the census refuses before the stand-in
  client is called: the video question, the video sweep (video stays
  pending), the transcript upload (402 before the audio is stored),
  `motodiag diagnose`, `motodiag code explain`, `motodiag intake photo`, the
  labor estimate, and each other site the census finds.
- `tests/test_phase404_plan_names.py`: `motodiag tier` under each plan and
  `motodiag tier --compare` print "Individual: for your own bikes", "Shop"
  and "Company"; the "Physical locations" row reads 3 for Company; the "AI
  cost cap / month" row reads $150.00 for Company and matches the server's
  figure for every plan; none of the three old names appears under `src/`.
- `tests/test_phase404_feed_checkin_status.py`: the job run once with a
  stand-in answering 401, then `payments feed status` exits 1 and names the
  refusal with "401"; answering 202, exit 0 with the time and "202"; the
  newest accepted row planted older than two check-in intervals, exit 1;
  no row with the alarm on, exit 1 "has never checked in"; the alarm off,
  exit 0 and no check-in problem (the control); rows older than 30 days are
  deleted at the day's turn and younger ones kept; no planted key in any
  output; `monitor.checkin` returns the answer for a 2xx, a 4xx and a
  network failure.
- `tests/test_phase404_migration_090.py`: a fresh database migrates to 90
  with the table and index present; the rollback removes both and nothing
  else; the scope file names exactly what the migration adds.
- Existing tests updated with the reason: `tests/test_phase177_vehicle_api.py`
  line 239; `tests/test_phase109_cli_foundation.py` lines 63 and 75;
  `tests/test_phase371_monitor.py` and
  `tests/test_phase371B_checkin_key_once.py` if the return shape changes;
  `tests/test_phase371_cli.py`'s status tests stay as they are.
- Old code: each new test file run against master's `src/`, red, with the
  controls green.
- Mutations, `404_mutate.py`: the plan figure off by one, the shop's plan
  read from the caller instead of the owner, the check after the paid call,
  the 401 recorded as accepted, the stale window at one interval, a name
  left as "Solo Mechanic".
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids; the floor test
  and the quality ratchet both green.
- The regression of record through `regression.sh` inside the fence, with
  `wholetree.sh --full` first (migrations.py changes).

## Non-goals

The people limit (`max_users`), shown and kept nowhere; a finding at most.
The location limit's enforcement, beyond writing 3 where it is shown; the
finding this phase files carries it. The names and prices in Stripe's
dashboard (the operator's). The website's pricing section. The app's
screens and its own text (372B; any disagreement found at Step 0 is named
for that session). The Mekno name in what customers see (K77, later work).
The brake's number (`MOTODIAG_COST_CAP_MONTHLY_USD_CENTS` stays 0). AI
spend attribution (`src/motodiag/shop/attribution.py`) and the F-ticket on
the app sending its active shop. Any change to prices, model access or the
session limits. The payments feed's Stripe rounds and notices (Phase 371).
Any change to `.claude/skills/`, the guards or the fleet. No seed data, no
split and no eval protocol: this phase has none.

## Planned items

- [ ] Step 0 re-measured: the census of paid AI calls with its count and command in the phase log; the three app lines recorded; the `## The database step` scope file `404_deploy_scope.json`
- [ ] F270: Shop's bike limit removed in both tables; the two tables agree in a test; the 51st bike test
- [ ] F271: the plan figures kept by the server; `check_cost_cap` holds the plan figure beside the brake; the refusal names the plan and the date; 402 `plan-ai-limit-reached`; every call site in the census checks before paying; Company's locations read 3 and the finding is filed
- [ ] F272: the three names in every table, with the tests
- [ ] F274: `monitor.checkin` returns the answer; migration 090 and the job's record; `payments feed status`'s line and three reasons for exit 1; the guide
- [ ] Existing pins updated with their reason; new tests red on master's code; mutations red; `COLLECTED_TEST_FLOOR` raised
- [ ] The regression of record; the `deploy` outcome; the operator applies migration 090 from one paste block
- [ ] The close-out: FOLLOWUPS closing lines for F270, F271, F272 and F274; the ROADMAP row ✅ with CLOSED date and regression line; the handoff with the live step (server and feed restarted, `payments feed status` printed and read) as one paste block ending in ALL GOOD or SOMETHING IS OFF
