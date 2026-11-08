# Phase 371 — phase log: live Stripe payments and production webhooks

**Status:** In progress

Built by the Chief Engineer in the fleet's fence, on `phase-371-live-stripe-payments-and-production-webhooks`; the plan is `371_implementation.md` v1.0, approved by the Executive Officer on issue #54.

## 2026-11-08: Before item 1

- **Row 398 on master:** `git show master:docs/ROADMAP.md` line 677 reads `| 398 | The two stalls at the Red Team's clear (F251, F252) | ✅ | **CLOSED 2026-11-08.** …`. The hold of K67 is met, so no `fork` stop.
- **The alarm test's timing, the operator's answer (K70), quoted:** "yes (a), test the alarm right after the merge". Applied literally: the stop-and-watch test is a step of the handoff's "After the merge" block (item 10), and to nothing beyond it. This session does not raise the stop.
- **The live account:** not needed by the build (K66); the tests use `stripe_fixtures.TEST_KEY` and a made-up DSN.

## 2026-11-08: Item 1, migration 089, and item 8's full run before its commit

- **Migration 089** `stripe_event_feed` in `src/motodiag/core/migrations.py`: `stripe_event_cursors`, `stripe_feed_notices` and `idx_stripe_feed_notices_line`, with the rollback dropping all three. `SCHEMA_VERSION` in `src/motodiag/core/database.py` moves to 89 (not in the plan; `tests/test_phase240c_severity_ordering.py` holds it equal to the last migration, as 348's log records).
- **`371_deploy_scope.json`** in 348's form: one `schema_version` row; three schema objects added.
- **`tests/test_phase371_migration.py`**, 10 tests on fresh databases, green with 348's migration test and 240c beside it.
- `scripts/code_quality.py counts`: ruff 1108, mypy 202, complex 25, big 5, helpers 19, swallowed 22, each at its pin.
- `wholetree.sh --full`, run on its own on the staged tree, exit code 0: `wholetree full: PASSED — 5085 passed, 36 skipped, 33 warnings in 1020.37s (0:17:00) (1023.0 s wall)`, record `fb4f6773c910…_full.json` for commit `a1d9999`.

## 2026-11-08: Items 2 to 4, the feed, the alarm and the limit check

- **The six settings** on `Settings`, each K65's number, with a comment naming the decision.
- **`src/motodiag/payments/event_feed.py`**: `FEED_TYPES` read from `HANDLERS`; `accounts`; `poll_account` (its paging in `fetch_events`, its dispatch in `_handle`, the place in `_place`, so every function stays under McCabe 20); `poll_once`; `limit_check`; `run_forever` with its state in `_Job`. Decided here:
  - with no cursor row the place is the clock's time, so the first ask is from `now - 300`, the plan's "the clock's time less the overlap";
  - a place older than 30 days is raised to 30 days back plus the overlap, so the ask is from exactly 30 days back and the next round, 20 seconds later, does not report the gap again;
  - a `retry=True` result holds the whole account's place for the round (the other events are still handed on, and come back next round as repeats);
  - the limit check on a new day's first round measures the day just ended, then starts the new day's memory, so the lateness and refusal lines see a whole day;
  - a round's error kinds are the gateway's (`refused`, `busy`, `unreachable`, …), plus `live_event`, `retry` and `gap`; `feed run --once` exits 1 on any of them.
- **`src/motodiag/telemetry/monitor.py`**: `checkin_url`, `checkin_body`, `checkin`; the margin of 10 minutes is `MARGIN_MINUTES`. A failure is logged naming the status and the DSN's host and project (`Dsn.__str__`), never the URL.
- **`message_event`** gains `level`, default `"info"`, so `telemetry check` is unchanged (343's events and sender tests pass).
- **`tests/support/phase371.py`** (not in the plan): the event-list page builder and the started-payment seed, shared by the four new test files. It builds the pages in code, as the plan says, and reads or writes no fixture file; `stripe_fixtures.py` is untouched.
- Tests: `test_phase371_event_feed.py` 21, `test_phase371_monitor.py` 7, `test_phase371_limits.py` 14, all green. Code counts at every pin.

## 2026-11-08: Items 5 to 7, the commands, the mask, the unit, the guide and the ledger

- **`motodiag payments feed run [--once]` and `feed status`** in `src/motodiag/cli/payments.py`, registered inside `register_payments_check`, where `check` is. Neither command calls `init_db`, so no migration ever runs through the feed or its unit; both exit 2 with the gateway's own message before any ask. `status` exits 1 for an account never asked (not in the plan's list; an account with no row cannot have been asked within two intervals), one asked more than two intervals ago, or one whose last error is set. The module docstring and `PAID_BY_EVENT` say "the webhook or the feed".
- **F248:** `SECRET_SETTING_NAMES` gains `"webhook_secret"`. `test_phase02_config.py` and 343's mask tests pass unchanged; the new test's control (the tuple without it) prints the planted secret.
- **`ops/desktop/motodiag-payments.service`** and **`install_payments_unit.sh`**, in the backup unit's form; the installer's `systemctl status` carries `--no-pager` so the paste block does not stop in a pager.
- **`docs/guide/payments.md`**, on `BACKEND_DOCS`. The planted `motodiag payments feed prune` line turned `test_phase208_docs.py::TestDocumentedCommandsExist::test_commands_resolve` red ("`payments feed` has no subcommand 'prune'") and was removed; 20 passed after. The same test file also caught the guide naming `/v1/billing/webhooks/stripe`, which is not in the OpenAPI schema (`include_in_schema=False`); the guide now points to row 401's prompt for the route instead of printing the path. `install.md` gains its one sentence.
- **The ledger:** row 401 ⏸️ after 400 (64 words by `roadmap_words.py`), its prompt `docs/prompts/401_payments_news_by_webhook.txt`; row 371's text says the server asks Stripe (K65) and that the endpoint model is superseded (105 words).
- `tests/test_phase371_cli.py`, 23 tests, green.
