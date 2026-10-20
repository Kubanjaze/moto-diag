# Phase 383 — 382's follow-ups: the live gates, then media paths

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-19

---

## Goal

Close the three findings Phase 382 filed, in the prompt's order: F206 (a
failing regression line passes A5 and K18), F208 (an always-on API breaks
the exact live comparisons), then F205 (media rows store the receiving
machine's absolute path), whose migration 087 then goes through both new
gates.

The operator's picks (verbatim in the log): **1C, 2A with apply-live
following it, check 8 unchanged, 3A**; each expected skip is pinned by its
test file and its reason, held by an equality test, and adding to it is
the operator's call; F210 filed for the column list's limit before row 330.

## Logic

### F206, 1C: only a passing run is of record

- **One writer, one reader, one file.** `closeout_check.py` gains
  `format_regression(log_text, commit, wall_s, command, rc)`, which
  `regression.sh` calls to print its lines, beside the parser that reads
  them. They cannot drift: a test feeds the writer's output to the reader.
- **The line** keeps regression.sh's shape. It is printed with the prefix
  `Regression of record:` only when the run exits 0 with 0 failed and 0
  errors; otherwise `Regression run FAILED (not of record):`.
- **Each skip is named** on its own line under it, from the run's `-rA`
  summary: `Skipped in the regression of record: [N] <file>:<line>: <reason>`.
- **The parser** (`regression_line`, A5 and K18 both) takes the last line
  carrying the prefix, as since 359, and requires the whole shape:
  `N passed, F failed, S skipped, E errors at `HASH` (… `… pytest …`, exit
  RC)` with F, E and RC all 0. The skip lines are the contiguous lines that
  follow it; their counts must sum to S, and each `(file, reason)` must be
  in `EXPECTED_SKIPS`.
- **`EXPECTED_SKIPS`** = `{("tests/test_phase244H_test_db_isolation.py",
  "no production database on this machine")}`, pinned by an equality test;
  adding to it is the operator's call.
- **`A5_UNNAMED_SKIP_EXEMPT` = `{"382"}`**: the one closed log with a skip
  and no reason line, recomputed from the closed logs and held to equality,
  as `A5_COMMAND_EXEMPT` is.
- **The legacy path** for the ten in `A5_COMMAND_EXEMPT` also refuses a
  line recording a failure (a nonzero "N failed" or "N errors").
- A5's and K18's messages say which part failed.

### F208, 2A: a named list of columns the running API writes

- `deploy.py` holds `SERVER_WRITES = {"api_keys": {"last_used_at"}}`.
- **Where it applies:** every comparison of live with a backup:
  apply-live's drift check ("changed since the dry run"), its after-apply
  comparison, and verify-live. A change confined to a listed column of an
  existing row is dropped; a row with other changes still shows, without
  the listed field. The output names how many changes were set aside, so
  nothing is silent.
- **Where it does not:** the dry run and apply-live's fresh run, both on
  copies no server writes, so a migration that writes a listed column
  shows in its diff. A field the approved exact diff names is never
  masked.
- **Check 8 is unchanged:** it fails where live is not (exit 4), and the
  close-out's `verify_phase.sh` of record runs on the desktop.

### F205: media paths relative to the data folder

- `motodiag/media/paths.py`: `stored_media_path(path, data_dir)` (the path
  relative to `data_dir`, POSIX form; an absolute path outside it is kept
  whole) and `resolve_media_path(stored, data_dir)` (`Path(data_dir) /
  stored`; an absolute stored path resolves to itself).
- **Writers:** the three upload routes store `stored_media_path(…)`.
- **Readers:** the three routes' file endpoints, the video analysis route,
  `analysis_worker`, `audio_sweep` and `transcript_pipeline` resolve with
  the settings' `data_dir` (the routes by their settings dependency; the
  rest by `get_settings()`). No route docstring that feeds the OpenAPI
  descriptions changes.
- **Migration 087** (`media_paths_relative`): for `videos.file_path`,
  `work_order_photos.file_path` and `voice_transcripts.audio_path`, a value
  starting `/` and containing `/videos/shop_`, `/photos/shop_` or
  `/audio/shop_` (its own table's segment) becomes its suffix from that
  segment. Anything else is left. No other column (no `updated_at`) moves.
  Rollback: none possible without the machine's data folder; the rollback
  SQL is a no-op and the description says so, since the new reader reads
  both forms.
- **The deploy, 3A:** on the desktop, the dry run and the approved diff;
  then `systemctl stop` just before `apply-live`; verify-live; the
  close-out commit; the merge; the server's pull; `systemctl start`.

## Tests

- **F206:** the writer's line parses (a passing run with 244H's skip); a
  failing run's line, a passing-looking line with "5 failed" or "exit 1"
  under the old prefix (382's desktop line verbatim), an unnamed skip, an
  unexpected skip and a miscounted skip are each refused by A5 and by
  `regression_problem`; the closed logs: every post-K6 log still passes,
  `A5_UNNAMED_SKIP_EXEMPT` equals what the rule refuses, `EXPECTED_SKIPS`
  equals its literal and each entry's file holds its reason; `regression.sh`
  calls the writer. Known-bad fixtures in `fixtures/k6_k7/` and
  `deploy/fixtures/k18/`.
- **F208:** on fixture databases: a `last_used_at` write between the dry
  run and the apply no longer refuses, and after the apply verify-live
  exits 0; the controls: a change to `api_keys.name` on the same row, an
  added `api_keys` row, and `last_used_at` in another table each still
  refuse and exit 3; a migration that writes `last_used_at` shows in the
  dry run's diff.
- **F205:** a row written by the upload route under one `data_dir` reads
  back through the route under another; the stored value is relative;
  an absolute value still reads; 087 on a fixture rewrites exactly the
  layout-shaped rows, leaves the rest, and moves no other column.
- Mutations in `383_mutate.py`; the floor raised by the diff of collected
  ids.

## Non-goals

- F207 (mobile), F209;
- F210's rule (option 2C), before row 330;
- `MOTODIAG_PUBLIC_BASE_URL`; a regression on the desktop.

## Planned items

- [ ] F206: writer, parser, regression.sh, fixtures, tests
- [ ] F208: the list, the three comparisons, tests
- [ ] F205: paths module, writers, readers, migration 087, tests
- [ ] mutations, the floor
- [ ] `wholetree.sh --full`, the regression of record (Mac)
- [ ] 087's dry run on the desktop, shown to the operator; the apply on
      their words, with the API stopped (3A)
- [ ] F205, F206, F208 closed or narrowed; the close-out, the handoff
