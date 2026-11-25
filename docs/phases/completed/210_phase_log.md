# Phase 210 — phase log

**Status:** Complete (closed 2026-11-25; no database step, nothing changed on live)

## 2026-11-25 — Step 0, re-measured by the Engineer

On this branch at `4baeec5` (v1.0 as revised for K139, master merged in).

- **The schema and the gate:** `SCHEMA_VERSION = 92` (`core/database.py`
  line 10); `TERMS_VERSION = "1.1"`, `TERMS_DATE = "2026-11-23"` and the four
  `TERMS_EXEMPT_PATHS` (`auth/terms_acceptance.py` lines 20 to 28); the gate
  in `require_api_key` (`auth/deps.py`); `terms_required` defaults to False
  (`core/config.py` line 281). All as the plan reads.
- **The counts, moved since the plan was written:** `COLLECTED_TEST_FLOOR =
  13266` at line 672 (the plan read 13264 at line 667; master moved it).
  Unchanged: ruff 1108, mypy 202, complex 25, big files 5, private helpers
  19, swallowed 22, coverage 88.0; `UNREACHABLE_COUNT = 23`,
  `MODULE_ISLAND_COUNT = 10`, `ORPHAN_COUNT = 127`; the root
  `implementation.md` at 0.13.146.
- **The PDF libraries in the fence's venv:** `pypdfium2` 5.15.2 and
  `reportlab` 4.5.1 import.
- **A fresh database** (`init_db` on a temporary path): schema 92; no shop,
  no labour rate, no catalogue part, no subscription; one user (`system`,
  id 1), one customer (`Unassigned`, id 1), one tax jurisdiction (`US-MA`),
  and 44 bulletins in `technical_service_bulletins` (F292's load). So the
  day's shop is in Texas and adds `US-TX`, and the launch check's stand-in
  empties the bulletins table for F292's control.
- **The wizard on a fresh database, in order:** step 1 asks the shop's name,
  address, city, state, zip, phone and email; step 2 a username, full name,
  email and the password twice; step 3 repeats "Add a staff member?" with
  username, full name, email, role and the password twice; step 4 which
  owner is at the keyboard and whether they accept; step 5 a CSV or one bike
  by hand (make, model, year, VIN, powertrain, the customer's name and
  phone); then the walkthrough offer. The scripted answers follow
  `happy_input`'s form.
- **Errors as the app sees them** (`api/errors.py`): no labour rate is
  `InvoiceGenerationError`, **422** `invoice-generation-failed` (the plan
  says "refused"; the step asserts 422 and its detail); no tax on record is
  409 `tax-not-on-record`; a `draft` order started is 409
  `invalid-transition`; no plan is 402 `subscription-required`; the gate is
  403 `terms-not-accepted`; a wrong password is 401 `login-failed`.
- **How live receives Stripe's subscription events** (402's handoff, step 3,
  and `payments/event_feed.py`): through the payments feed, not the webhook.
  The server is tailnet-only (K74), so Stripe cannot reach
  `/v1/billing/webhooks/stripe`; `motodiag-payments.service` asks Stripe's
  `/v1/events` for the platform account every interval, and `FEED_TYPES` is
  every key of `HANDLERS`, among them `customer.subscription.created`,
  `.updated` and `.deleted`. So on the onboarding day the owner's Shop plan
  reaches live within one feed interval of the checkout, by the same handler
  the webhook calls. The day's test records the plan through the webhook
  route, as the plan says; both paths end in `dispatch_event`.
- **`take_snapshot`'s `runs.log` line** (`backup/snapshot.py` lines 149 to
  220): one JSON object per line, `sort_keys`, with `time` (the snapshot's
  ISO time), `label`, `snapshot`, `outcome` (`ok` or `failed`) and the
  counts. The launch check reads the last line's `outcome` and `time`.
- **`current_terms`'s fields:** `version`, `date`, `terms_url`,
  `privacy_url`, `accepted`, `accepted_at`.
- **The server's loopback address:** `ops/desktop/motodiag-api.service`
  runs `motodiag serve --host 127.0.0.1 --port 8000`, so the check reads
  `http://127.0.0.1:8000`.
- **The disk floor:** `SPACE_FLOOR_GB = {"C:": 50, "Ubuntu": 50}`
  (`.claude/skills/fleet/dispatcher.py` line 172), read at `/mnt/c` and `/`
  (`DISKS`, line 175).
- **"Needs the operator: nothing" against K134.** The plan of record's #24
  says the phase needs nothing from the operator; K134's scope names live
  steps the operator runs. K136's answer 1 reconciles them, and this build
  takes it: the build needs nothing from the operator, and every live step
  comes after the close-out, the operator's, from the handoff.
- **The finding for the two conditions the scope does not name** is F301,
  filed with the `finding` skill before this entry cites it.

## 2026-11-25 — the launch check (Logic item 2)

- **`src/motodiag/launch/check.py`:** `Condition` and the eight conditions,
  each a function, in the scope's order; `open_read_only` (`mode=ro`
  through a `file:` URI, never `init_db`); `run_conditions`.
  `DISK_FLOOR_GB = 50` (390's floor) and `BACKUP_MAX_AGE_H = 25` (the
  03:00 timer plus one hour of slack, the plan's reading, applied as it
  stands); `LAUNCH_TERMS_VERSION = "1.1"`; `SERVER_URL =
  "http://127.0.0.1:8000"`, the service's own address.
- **`src/motodiag/cli/launch.py`** with `launch check [--db]`, and the two
  lines in `cli/main.py`.
- **Condition 3, as built.** `_status_problems(settings, db_path,
  cursor_rows(db_path), now)` from `motodiag.cli.payments`, called as
  `payments feed status` calls it, then the check's own test that
  `alarm_dsn(settings)` is not None. The feed's readers open the database
  through `get_connection`, as the command does, not through the check's
  read-only connection; none calls `init_db`, and the write test (below)
  holds that the database's bytes and `PRAGMA data_version` do not move.
  The command and the check differ on a missing DSN on purpose: the
  command describes the feed and prints the alarm as off; the check says
  not ready, because at launch the alarm must be on (K65, K72).
- **Condition 4 reads `work_dir()`**, which creates the working folder
  when it is missing (mode 700). On the server it exists since 345; the
  check writes nothing else.
- **Condition 5's read** is `loopback_json`: it refuses any host but
  `127.0.0.1`, `localhost` and `::1` (`NotLoopback`) and opens with no
  proxy, so a proxy setting in the environment cannot send it elsewhere.
- **Not in the plan, decided here:** a detail on a `ready:` line, in
  brackets (`ready: … (env=prod, provider=stripe, …)`), so a ready line
  says what it saw; the provider's word is `stripe` or `not stripe`, never
  the setting's own text; an unreadable table is that condition's
  `NOT READY:` line rather than a traceback (a database that is not
  live's).
- **Tests:** `tests/test_phase210_launch_check.py`, 32: the passing
  stand-in (eight `ready:` lines and ALL GOOD, exit 0); the backup line as
  `take_snapshot` writes it; the twenty breaks the plan lists, each alone,
  each with its `NOT READY:` line, SOMETHING IS OFF, exit 1 and the other
  seven ready; the no-DSN control (`_status_problems` alone finds nothing
  on the same stand-in); `init_db` replaced by a raising function; the
  empty bulletins table stays empty (F292); the bytes and `data_version`
  unchanged; no planted key, DSN or passphrase printed, with the control
  that the settings read held the planted key; loopback only; exit 2; the
  disk floor read from the dispatcher's text; the 25 hours.
  `tests/test_phase210_wiring.py`, 7. The stand-in's backup line is
  written by `take_snapshot` itself, so the parser is held to the writer.
  A template database is made once per module and copied (79 s to 10 s).
- **`docs/launch-checklist.md`:** the status paragraph replaced.
- **Gates:** `test_phase209B_integration_gaps.py` and
  `test_phase244U_gate_blind_spot.py` green with no allowlist change; the
  quality ratchet and the one-pin test green.
- **`COLLECTED_TEST_FLOOR`** 13266 to 13305, by a diff of collected ids
  against `4baeec5`: +39 -0, all in the two new files.
- `wholetree.sh` (fast): exit 0, 3049 passed, 10 skipped.

## 2026-11-25 — the first shop's day (Logic item 1)

`tests/test_phase210_first_shops_day.py`, 16 tests, nothing under `src/`.

- **The shape.** The module-scoped `day` fixture runs the fourteen steps in
  order inside one `MonkeyPatch` context, undone before any test reads the
  results, so no setting of the day reaches another file's test on the same
  worker. Each step's assertions run in the step; a failing step is
  recorded with the note "the shop's day stopped at: <step>", and the
  steps after it are not run. Each test names one step: it passes, re-raises
  that step's own failure, or fails saying where the day stopped. The
  fifteenth test holds that every step ran and that the network guard
  refused nothing (its `_refuse` is wrapped to record each host); the
  sixteenth builds the day again in a second folder and holds the ids equal.
  Measured: alone 22.8 s; in one process after 303's, 334's and 372's files
  and under `-n 4` with the launch check and 303's file, all green.
- **The settings:** `STRIPE_ENV` (provider `stripe`, `TEST_KEY`, the test
  webhook secret and prices), `MOTODIAG_TERMS_REQUIRED=true`,
  `MOTODIAG_ENV=dev`, `MOTODIAG_DATA_DIR` under the day's folder, the stub
  scanner on PATH; the database from `phase303.new_db` at schema 92.
- **Reading 2, as built: the signed webhook round completes offline.** The
  owner's `POST /v1/billing/checkout-session` (Stripe answers the recorded
  `checkout_session_subscription`, and the request carries
  `subscription_data[metadata][user_id]` = the owner and the shop price),
  then a `customer.subscription.created` signed with `signed` under
  `freeze_webhook_clock`, posted to `/v1/billing/webhooks/stripe`; the
  handler re-read `GET /v1/subscriptions/sub_test_fixture273` from the
  stand-in (the recorded `subscription_active` body, its `metadata.user_id`
  the owner's), and `GET /v1/billing/subscription` says `shop`, `active`.
  `make_sub` was not needed for the owner. The add-member call is 402
  before and 201 after; the shop then has four members.
- **Which refusal a mechanic without the terms meets first:** 403
  `terms-not-accepted` on the work orders list, as the plan reads; never a
  402, since the owner's plan covers the mechanic.
- **Reading 4, as built: the mechanic's own adjust is admitted, and the
  fill gives 1.0.** Clock-in 201, clock-out 200 with `duration_seconds` 0,
  the mechanic's `PATCH /v1/shop/{id}/time-entries/{entry}` 200 with 3600,
  and `complete` with no `actual_hours` returns `actual_hours` 1.0. Neither
  fallback was used.
- **The invoice's refusals as the app sees them:** 422 with "no labor rate
  available" before `shop labor-rate set`; 409 `tax-not-on-record` naming
  "shop 1 has no tax jurisdiction"; with the `labor` rule alone, 409 naming
  `--line-type parts` and not `labor` (the installed part reached the
  invoice); 201 after both rules. Labour 9500 cents an hour, the part 4500,
  8.25 %: subtotal 14000, tax 1155, total 15155 cents, `sent`.
- **The payment:** the account connected (`CREATE`, `LINK`: `restricted`),
  refreshed (`READ_ACTIVE`: `active`); the mechanic's checkout 403 with no
  request to Stripe; the owner's 201 for 15155 cents; then
  `event_feed.poll_once` at `FROZEN_AT + 10`, the platform asked with no
  `Stripe-Account` header and the shop's page with it, the shop's page
  answering `succeeded` at 15155 cents. The invoice is `paid` and the list
  says `succeeded`, `paid_invoice`.
- **Found while building, recorded here, no change to `src/`:**
  - the symptom and fault-code routes answer 200, not 201;
  - the invoice's body is in cents (`subtotal_cents`, `tax_cents`,
    `total_cents`, `unit_price_cents`);
  - search hits carry `page_number` and `snippet`;
  - the Shop plan's 20 GB of manuals is `20 * 1024**3` bytes
    (21474836480);
  - the fresh database's first shop is id 1, as live's test shop is.
- **The 51st bike:** the owner's garage is filled to 50 through
  `POST /v1/vehicles`, and the 51st is 201; the list says total 51, tier
  `shop`, no quota limit.
- **The audit step:** 28 writes to the shop's routes by the owner and the
  mechanic, every one in `GET /v1/shop/{id}/audit` with the same method,
  path, username and status, the mechanic's refused member-add with 403
  among them.
- **The backup step:** `take_snapshot` into a `MemoryStore`, label
  `nightly`; the manifest lists the manual's PDF under `manuals/`;
  `restore` into an empty folder gives the same row count in every table
  `sqlite_master` names (`restore._rows`, over all of them), each of the
  plan's 28 tables non-empty, and the PDF byte for byte; `runs.log` has one
  line, `ok`.
- **Not in the plan, decided here:** a second shop's member, on a Shop plan
  of their own, is refused (403) a customer at the day's shop, the control
  mutation 2 needs; the mechanic signs in a second session and signs it out
  (204), so all four exempt paths are walked.

## 2026-11-25 — the mutations and the old code

- `docs/phases/in_progress/210_mutate.py`, eighteen mutations in 388's
  harness: **18/18 red** (`210_mutate.out`). Each names the test that went
  red: the day's step for M1 to M8 and M18, the launch check's cases for M9
  to M17. The launch check's twenty breaks were given ids without spaces so
  `-k` can name them.
- **Old code** (the three files run with `PYTHONPATH` at a worktree of
  `master`, whose `motodiag` was the one imported):
  `test_phase210_launch_check.py` 1 error at import;
  `test_phase210_wiring.py` 3 failed, 4 passed (the four read this branch's
  files); `test_phase210_first_shops_day.py` 16 passed, by design.
- **Controls, unchanged and green** (one run, `-n auto`): 676 passed, 1
  skipped, over `test_phase303_auth_api.py`, `test_phase330_onboarding.py`,
  `test_phase334_terms_routes.py`, `test_phase293_terms.py`,
  `test_phase293_manuals_api.py`, `test_phase293_review.py`,
  `test_phase345_snapshot_restore.py`, `test_phase348_audit_middleware.py`,
  `test_phase348_audit_api.py`, `test_phase371_event_feed.py`,
  `test_phase372_payment_routes.py`, `test_phase273_subscriptions.py`,
  `test_phase201_parts_api.py`, `test_phase202_time_tracking.py`,
  `test_phase169_invoicing.py`, `test_phase281_tax.py`,
  `test_phase404_bike_limit.py`, `test_phase404_feed_checkin_status.py`,
  `test_phase402_share_links_off.py`, `test_phase209B_integration_gaps.py`
  and `test_phase244H_test_db_isolation.py`.
- **`COLLECTED_TEST_FLOOR`** 13305 to 13321, by a diff of collected ids
  against `f1ab603`: +35 -19 (16 new in the day's file; 19 of the launch
  check's breaks renamed).
- **The clock census (K19) caught the day's first form.** The tax records
  were dated from `date.today()`, which `test_phase378_test_clock_census.py`
  counts as a test reading the clock (three new lines; the census failed in
  `wholetree.sh`). The records now carry fixed dates that span every day the
  test can run on (effective 2026-01-01, valid until 2099-12-31, checked
  2026-11-25), since the invoice is dated by `tax.today()`; the test reads
  no clock, and the census is unchanged. Not a bug in the shipped code: the
  test was never committed in the first form. M3 re-run on the new form:
  red. `wholetree.sh` (fast): exit 0, 3049 passed, 10 skipped.

## 2026-11-25 — the full whole-tree, before the regression of record

`wholetree.sh --full` at `5642729`: 5518 passed, 36 skipped (1032.6 s
wall), exit 0, record written.

## 2026-11-25 — the first regression run, not of record

`regression.sh` at `5642729`, inside the fence: `Regression run FAILED (not
of record): 13215 passed, 1 failed, 105 skipped, 0 errors` (38 min 44 s
wall). The one failure is Bug fix #1, below; not F300.

### Bug fix #1 — 2026-11-25 — 293's scanner test met a real ClamAV on the build machine

- **Issue:** `tests/test_phase293_checks.py::test_clamscan_is_used_when_the_daemon_is_absent`
  failed: `scan._command` returned `/usr/bin/clamdscan`, not the stub's
  `clamscan`. It fails alone, every time, on this branch and on master's
  code; nothing of this phase is in its path.
- **Root cause:** the test puts its stub folder on PATH through
  `use_path`, which adds `/usr/bin` and `/bin` for the stub's own tools.
  When 293 was built, this machine had no virus scanner; 293's live step 4
  has since installed ClamAV on the home desktop, where the fence runs, so
  `/usr/bin/clamdscan` exists and `_command` rightly prefers the daemon.
  The test assumed the machine had no scanner, and never said so.
- **Fix:** that test's PATH is the stub folder and a folder holding only a
  link to `grep`, the one tool the stub runs (its shebang is `/bin/sh` by
  path); it asserts `_command` names the stub's own `clamscan`. `use_path`
  and every other test are unchanged.
- **Files:** `tests/test_phase293_checks.py`.
- **Verified:** red before the fix, alone (1 failed); after it,
  `tests/test_phase293_checks.py` 17 passed. With `_command`'s fallback to
  `clamscan` removed the test is red (it returns None).

**Commit.** `c80082a` ("Phase 210, bug fix #1: 293's scanner test met a real ClamAV").

`c80082a` was committed before `wholetree.sh` ran on it, against rule 3;
it ran straight after, on that commit, clean: exit 0, 3049 passed, 10
skipped, record written. Nothing changed between.

## 2026-11-25 — the regression of record, at `847c1c2`

`wholetree.sh --full` at `847c1c2` passed first: 5518 passed, 36 skipped
(1079.0 s wall). Then `regression.sh` on the clean tree, its record exactly
as it printed it:

Regression of record: 13216 passed, 0 failed, 105 skipped, 0 errors at `847c1c2` (36 min 49 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:104: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:121: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:137: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:145: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:153: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:162: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:175: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:185: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:218: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:223: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:248: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:259: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:272: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: inside the fleet's fence: its boundary is proven from the host, not from inside
Line coverage of record: 88.60% at `847c1c2` (the pin is 88.00%): 0.60 points above it; raise COVERAGE_PERCENT to lock it in

The 105 skips are the fence's, the same files and reasons as 293's run in
the fence. F300 did not bite. Coverage 88.60%, the pin 88.00%; the pin is
left as it is, as no rule asks this phase to raise it.

## 2026-11-25 — the handoff's blocks, tested against a stand-in desktop

Each paste block was written to a file under `/fleet/run/s210/blocks/`
and run from there, in a clean environment (`env -i`, as a new terminal
has), with `HOME` at a stand-in desktop built by a script under
`/fleet/run`: a local clone of this branch as the server's checkout with
the clone's venv, a settings file with planted values (mode 600), a live
database at 92 with shop 1 inactive, a reviewer, the feed asked and the
alarm checked in, a backup log, and the real API server
(`motodiag serve --host 127.0.0.1 --port 8000`) on the stand-in database.
`sudo` and `systemctl` were stand-ins that do nothing, and so was the
backup call in the tax block.

- Every block passes `bash -n`, before and after the regression commit was
  filled in.
- **Live payments check:** ALL GOOD on a fresh stand-in; SOMETHING IS OFF
  with a settings line missing, and with the feed not asked for a minute.
- **The terms switch:** added once with its dated comment and ALL GOOD; a
  second paste added nothing and ALL GOOD; a conflicting line and two lines
  each refused, nothing changed.
- **The launch check on the stand-in live:** before the switch, seven
  `ready:` lines and NOT READY on the terms switch only, SOMETHING IS OFF,
  exit 1; after it, eight `ready:` lines and ALL GOOD, against the real
  server on loopback.
- **The plan check:** an empty name and a shop with no plan each refused
  with the plan's words; ALL GOOD once the owner held an active Shop plan.
- **The labour-rate and tax block:** an empty line and a bad state each
  refused, nothing changed; filled in, it recorded the rate, the
  jurisdiction, the link, the shop's rate and both rules, printed `shop tax
  status` and ALL GOOD; a second paste recorded the same again and ALL
  GOOD (the newest labour rate is the one used).
- **Found by it:** the fence's shell has an HTTP proxy, and `curl` to
  `127.0.0.1` went through it (403) until the environment was cleaned; the
  launch check's own read opens with no proxy (Deviation 6). The stand-in's
  first form linked only `python` into a folder, which is not a venv; it
  linked the whole venv after.
- Not run: anything that reads GitHub, the Mac's app folder, the desktop's
  real services, or a real backup of live.

## 2026-11-25 — the close-out

- `210_implementation.md` v1.1: an "As built" line in every section,
  Deviations (seventeen), Results, no open boxes, its history row.
- The phase's files moved to `docs/phases/completed/` with `git mv`.
- The ROADMAP row ✅, **CLOSED 2026-11-25**, with the regression line.
- The root `implementation.md` 0.13.146 to 0.13.147 and its history row;
  the root `phase_log.md`'s pointer.
- F301 marked closed by this phase's launch check.
- The handoff: `docs/handoffs/2026-11-25_210_closed.md`.
