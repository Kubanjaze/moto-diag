# Phase 371 — phase log: live Stripe payments and production webhooks

**Status:** Complete

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

## 2026-11-08: The mutations, 15/15 red, and the floor

- **`371_mutate.py`**, 348's harness, the plan's fifteen mutations. The first run was **14/15**: F6 (a `retry=True` result advancing the cursor) stayed green, because the retry test's round held only the retried event, so nothing could carry the place forward whether or not the hold was honoured. The test now has a later event handled cleanly in the same round, and asserts the place stays put and one event was handled. The code was right; the test could not fail. Then `371_mutate.py F` 8/8 and the full run **15/15 red**, recorded in `371_mutate.out`.
- **`COLLECTED_TEST_FLOOR` 12416 → 12492**, by a diff of collected ids against master at `3bf657e` (12417 collected in a worktree of master, removed after): +75 −0, all in the five `test_phase371_*` files (cli 23, event_feed 21, limits 14, migration 10, monitor 7).

## 2026-11-08: Item 9, the regression of record

- `wholetree.sh --full` on its own at `6286d9c`, clean tree, exit code 0: `wholetree full: PASSED — 5085 passed, 36 skipped, 33 warnings in 1020.24s (0:17:00) (1022.8 s wall)`, record `2336f2bba0e5…_full.json` for commit `6286d9c`.
- `regression.sh`, exit code 0, the lines as printed:

Regression of record: 12387 passed, 0 failed, 105 skipped, 0 errors at `6286d9c` (35 min 34 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Line coverage of record: 88.12% at `6286d9c` (the pin is 87.50%): 0.62 points above it; raise COVERAGE_PERCENT to lock it in

- The coverage line's suggestion to raise `COVERAGE_PERCENT` is not taken here: the plan does not name it, the pin is a floor that 88.12% clears, and a change to `tests/support/quality_counts.py` now would change the tree after the regression of record.
- Next, the database step: the operator applies migration 089 to live from the dispatcher's paste block; this session does not close out.

## 2026-11-08: The regression of record's skip lines, added by the operator

The entry above copied the regression of record's first line and its coverage line, but not the 81 lines `regression.sh` printed between them, naming each skip. The live apply reads those lines too, so at 12:46 EST the dispatcher refused the database step. The operator added them by hand, here: `closeout_check.format_regression` printed them again from that run's own pytest log, `6286d9c_parallel_20261108_111323.log`, kept in the run's folder on the home desktop, and the first line it printed equals the record line above, character for character. No code changed. That run's lines, as `regression.sh` printed them:

Regression of record: 12387 passed, 0 failed, 105 skipped, 0 errors at `6286d9c` (35 min 34 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
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
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
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
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
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
Line coverage of record: 88.12% at `6286d9c` (the pin is 87.50%): 0.62 points above it; raise COVERAGE_PERCENT to lock it in

A later regression of record is copied with every line `regression.sh` prints, the skip lines included.

## 2026-11-08: The branch read at `594062e`, before the database step (K71)

- **The operator's answer (K71), quoted:** "Go with A." Applied literally: this session builds nothing more, appends this one entry, commits it, and ends with the outcome `deploy`.
- **No code since the record:** `git diff --name-only 6286d9c 594062e -- src tests` prints nothing; only `371_implementation.md` and this log changed since `6286d9c`, so the regression of record at `6286d9c`, held in the entry above with every line `regression.sh` printed, stands and is not run again.
- **Migration 089:** `Migration(version=89, …)` is in `src/motodiag/core/migrations.py` at line 7817; `371_deploy_scope.json` names the two tables `stripe_event_cursors` and `stripe_feed_notices`, the index `idx_stripe_feed_notices_line` and one added `schema_version` row, and no existing row changes.
- Next, the database step, as before: the operator applies migration 089 to live; this session does not close out.

## 2026-11-08: The database step, and the close-out

- **The operator's answer to the dry run**, from `371_deploy_answer.md`, on the dry-run diff whose sha256 is `93bff975e2b0f207652c110b9749a1b466fea9eae018cf62f475250680c84360` (`sha256sum 371_dryrun_diff.md` prints the same), quoted:

> yes

- **The dry run on a copy** (`371_dryrun_diff.md`, backup `motodiag_pre371_20261108_185806.db`): migrations applied `[89]`, scope problems none, F158 census 41.
- **Live after the apply** (`371_live_diff.md`): scope problems none; equal to the approved exact diff: yes; 0 rows set aside as the running API's; F158 census 41. Live gained `stripe_event_cursors`, `stripe_feed_notices`, `idx_stripe_feed_notices_line` and `schema_version` 89 (rowid 88); no existing row changed. The dispatcher checked it again with `verify-live`.
- **No code since the record:** `git diff --name-only 6286d9c HEAD -- src tests scripts .claude` prints nothing; this close-out changes documents only.
- **K70's words on the alarm test's timing**, quoted again for the handoff: "yes (a), test the alarm right after the merge".
- **F256 filed** with the `finding` skill, as item 10 asks: the feed writes `stripe_event_cursors`, `stripe_feed_notices`, `stripe_webhook_events`, `invoice_payments` and `invoices` while the server runs, and `SERVER_WRITES` names none of them, so the next deploy after the unit is installed meets them as drift.
- **F248 marked closed by this phase** in `docs/FOLLOWUPS.md` (item 6, `4448850`).
- **Decided here, F257 filed:** writing item 10's live switch-on block found that it cannot succeed as planned. A live key needs `MOTODIAG_ENV=prod`; the API reads the same `server.env`; and in prod `motodiag serve` refuses to start unless `MOTODIAG_PUBLIC_BASE_URL` is a public https address (`src/motodiag/cli/serve.py` line 218). Measured in this clone's venv under `Environment.PROD`: empty, `http://localhost:3000` and a `*.ts.net` name each block. So the block as planned would leave live without its API. The handoff's live step therefore runs the same start-up check on the settings file first, and stops with SOMETHING IS OFF before restarting anything when it would refuse; the alarm's test follows that step. The reason: an operator block must not be able to take live down, and the public address is the operator's open question (K65), not this phase's to answer. Recorded in v1.1's Deviations.
- **F238** (Q12 and the size of `migrations.py`) is open and the operator's choice; Q12's verdict lands on the pull request, after this close-out, where the Quartermaster records it.
- **The reclaim line:** this session runs in the fence and cannot run `reclaim`; the fleet's pull request carries the dispatcher's own close-out line.

## 2026-11-08: K71 brought onto the branch (a citation fix)

- **What was wrong:** v1.1 and the entry above cite K71, the operator's "Go with A.", but `docs/decisions.md` on this branch ended at K70. K71 was recorded on `master` (`333d5c4`) after the branch was cut, so on the branch the citation resolved nowhere.
- **Fix:** `333d5c4` cherry-picked onto the branch as `22bb923`, its one line in `docs/decisions.md` unchanged, so `| K71 |` now resolves here and the merge to `master` meets an identical line. No sentence of v1.1, this log or the handoff was changed.
- **No code changed:** `git diff --name-only 13542ae HEAD -- src tests scripts .claude` prints nothing, so the regression of record above stands.

## 2026-11-08: The Red Team's round 2

- **The alarm test's timing.** Two sentences of v1.1 read K70 as met by a test that now waits on the public address (F257): the Deviations' "so K70's "right after the merge" is met once the live step can run" and the close-out line's "no stop was raised in the build beyond K70's and K71's answers". Both deleted. K70 approves a test right after the merge; a test behind an undecided address, with no date, is a timing K70 did not approve, so it goes to the operator as a stop. The handoff's "What is open" says it is put to the operator.
- **A retry on an account with no place yet.** The finding says the next round asks from its own clock less 300 seconds. Measured: on a hold the round writes the place it asked around, the clock's time on a first round, and the next round reads that row and asks from the same second. `test_a_retry_on_the_first_round_is_asked_for_again` plants no place, holds the event at the window's first second, runs a second round 20 seconds later, and sees both asks at `created[gte]` = the first round's clock less 300 and the event handed on twice. Seen red: with `_place` taking the clock always (the behaviour the finding describes), the second ask is 20 seconds later and the test fails. The code was right, so this is a test, not a bug fix.
- **The floor**, 12492 → 12495, by a diff of collected ids against `bcc303f`: +3 −0.

### Bug fix #1 — 2026-11-08 — the feed kept its own time helpers and compared stored times as text

- **Issue:** `event_feed.stamp` and `event_feed.utc_day` re-made the stored UTC format outside `core/timestamps.py`, which owns it; `already_sent` compared `substr(sent_at, 1, 10)` and `notices_since` compared `sent_at >= ?` as text, against that module's rule that a stored time is compared parsed.
- **Root cause:** the helpers were written beside their first caller, and the two queries read the column as the feed itself writes it.
- **Fix:** `utc_at(seconds)` and `utc_day(seconds)` are in `core/timestamps.py`; the feed, `motodiag payments feed status` and the tests call them. `already_sent` compares `date(sent_at) = ?`; `notices_since` compares `datetime(sent_at) >= ?` against `utc_cutoff(since)`.
- **Files:** `src/motodiag/core/timestamps.py`, `src/motodiag/payments/event_feed.py`, `src/motodiag/cli/payments.py`, `tests/test_phase371_cli.py`, `tests/test_phase371_event_feed.py`, `tests/test_phase371_limits.py`.
- **Verified:** `TestStoredTimesCompareParsed` plants a notice at a −05:00 offset whose text date is the day before its UTC date, and one in SQLite's space shape inside the window; both tests fail on the text comparisons and pass on the parsed ones. The phase's tests with 370's and 377's: 129 passed.

**Commit.** `94e11f1`.

## 2026-11-08: The regression of record, again, after the round 2 fix
- `wholetree.sh --full` on its own at `94e11f1`, clean tree, exit code 0: `wholetree full: PASSED — 5085 passed, 36 skipped, 33 warnings in 1141.81s (0:19:01) (1144.8 s wall)`, record `52842ee026c2…_full.json` for commit `94e11f1`.
- `regression.sh`, exit code 0, the lines as printed:

Regression of record: 12390 passed, 0 failed, 105 skipped, 0 errors at `94e11f1` (37 min 9 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
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
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
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
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
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
Line coverage of record: 88.15% at `94e11f1` (the pin is 87.50%): 0.65 points above it; raise COVERAGE_PERCENT to lock it in

- `COVERAGE_PERCENT` is not raised, for the reason the first record gives.
- The alarm test's timing goes to the operator as a stop after this commit; the close-out documents carry this record.

## 2026-11-08: The close-out documents carry the new record

- v1.1's Deviations and Results, its history row, the handoff and row 371 now name `94e11f1`'s record and the one bug fix. No code changed after `94e11f1`.
- **A guard blocked a command:** a Python heredoc that edited v1.1 and the handoff was refused by the edit guard, because its body named `src/` and wrote to a path the guard could not resolve. The guard is unchanged; the same edits were made one at a time with the Edit tool.

## 2026-11-09: K72 brought onto the branch, and the wording to match (the advisor, for the operator)

- **What happened:** the Engineer's round-2 stage stopped at 23:48 EST on 2026-11-08 (issue #54, `threshold-or-rule`): K70's "right after the merge" cannot hold for the alarm's test, since live Stripe waits on the public address (F257) and on the live key, which is not set up yet. The stop left `94e11f1` and `9bf93ea` only in the stage's run folder; the operator sent them to GitHub from it, once the fleet's own push checks passed on them (all but its full test run, which the fleet makes next).
- **The operator's answer, 2026-11-08 (K72), quoted character for character:** "Right after live payments go on. Merge 371 once the builder's fixes pass round 3; the alarm test runs the moment I switch live Stripe on, whenever the public address is ready. Stripe is still "open, key not set up", so that is also why it can't be right after the merge."
- **Brought onto the branch:** K72's row, cherry-picked from `master`'s `fa7e221` as `76691b1`, its one line in `docs/decisions.md` unchanged, so `| K72 |` resolves here and the merge to `master` meets an identical line.
- **The wording to match:** v1.1's paragraph before item 1 (a dated note for the Engineer), the plan of record's close-out line, "Rule-1 stops anticipated", a Deviations bullet, Results and the history row; the handoff's alarm item and step 4. The two sentences `9bf93ea` deleted stay deleted.
- **No code changed:** `git diff --name-only 94e11f1 HEAD -- src tests scripts .claude` prints nothing, so the regression of record at `94e11f1` stands.

## 2026-11-09: The Red Team's round 2, checked at `b08a4ce` (the Engineer, fix round 2)

- **The alarm test's timing:** answered by the operator's K72 (`docs/decisions.md`, on the branch as `76691b1`), quoted character for character: "Right after live payments go on. Merge 371 once the builder's fixes pass round 3; the alarm test runs the moment I switch live Stripe on, whenever the public address is ready. Stripe is still "open, key not set up", so that is also why it can't be right after the merge." The two sentences the finding named are gone from v1.1 and the handoff (a search for each finds 0 lines). No new stop: K72 answers it.
- **A retry with no place yet:** `tests/test_phase371_event_feed.py::TestThePlace::test_a_retry_on_the_first_round_is_asked_for_again` shows the second round asks from the same second as the first (`created[gte]` is `NOW - 300` both times) and the event is handed on again. The hold writes the place as the first round's `now`, and the next round asks from that place less 300 seconds, not from its own `now`. `tests/test_phase371_event_feed.py` at `b08a4ce`: 22 passed.
- **The time helpers and the text comparisons:** fixed by bug fix #1 at `94e11f1`. `stamp` is gone; `utc_day`, `utc_at` and `utc_cutoff` are imported from `core/timestamps.py`; stored times are compared as `date(sent_at)` and `datetime(sent_at)`.
- **No code changed:** `git diff --name-only 94e11f1 HEAD -- src tests scripts .claude` prints nothing, so the record at `94e11f1` stands.
- **A guard blocked a command:** a `sed -i` correcting a test-class name in this entry was refused by the edit guard, which blocks `sed -i` wherever it points. The guard is unchanged; the correction was made with the Edit tool.

## 2026-11-09: The Red Team's round 3, its two findings fixed (the advisor, for the operator)

- **What the round found** (PR #58, 01:30 EST): a factual defect, v1.1's Tests close-out line still giving 75 new tests and the floor 12492 where Results gives 78 and 12495; and a wording defect, "(K72)" in the handoff's step 4, an internal label in an operator step (rule 6), which the dispatcher filed as F258. Round 3 is K9's last, so the fleet held issue #54 for the operator (01:32 EST): "under K9 the phase does not ship as it stands. The operator decides."
- **The fixes:** the Tests line now gives 78 new tests (cli 23, event_feed 22, limits 16, migration 10, monitor 7, each file's collected ids) and the floor 12495, as Results does and as `tests/test_phase255B_collected_test_floor.py` holds; "(K72)" is deleted from step 4, whose reason is already under "What is open"; F258 is closed by that deletion.
- **No code changed:** `git diff --name-only 94e11f1 HEAD -- src tests scripts .claude` prints nothing, so the record at `94e11f1` stands.
