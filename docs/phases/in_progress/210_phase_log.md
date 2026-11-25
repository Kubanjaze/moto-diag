# Phase 210 — phase log

**Status:** In progress

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
