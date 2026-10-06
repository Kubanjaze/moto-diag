# Phase 370 — F10: session times stored in UTC

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-06

## Goal

Row 370. F10 (moto-diag-mobile `docs/FOLLOWUPS.md`, open since 2026-05-01):
`core/session_repo.py` stamps diagnostic sessions with naive local
`datetime.now().isoformat()`, while `_month_start_iso()` returns the UTC
month start. On a month's last evening in a US timezone, after UTC midnight,
a new session counts toward neither month. Gate 9's lifecycle and six Phase
178 quota tests fail in that window. It next bites on 2026-10-31.

Every session time is written in UTC, in one format that compares
correctly with the month start. Every reader handles the new format. The 10
live fields are converted by migration 079, under the operator's scoped
approval. Proven on a frozen clock at 2026-10-31 21:42 EDT, with a planted
return to local time that turns the proof red.

Out of scope: F186 (work-order and other shop times; the operator: "separate
phase; 370 ships F10 only"). No API schema change.

## Step 0 — summary

The full record is in `370_step0.md`.
- **The prompt's facts hold:** the nine stamps, the minute stamp at 340, the
  UTC month start, the other counters UTC, and the live rows.
- **Reproduced:** with the clock frozen at 2026-11-01 01:42:07 UTC under
  `TZ=America/New_York`, 7 failed and 3 passed. The 7 are gate 9's
  lifecycle and the six 178 quota tests. On the real clock, 10 passed.
- **Readers:** the API's `since`, its session responses, the CLI's `show`,
  `list` and filters, the report Timeline, client memory's dates, and the
  app's `formatTimestamp`. The predictor reads none.
- **Greenfield / extension / reshape:** extension.

**The operator's decisions (2026-10-06), verbatim:**

> Q1: A. Apply 079 live only if the dry-run diff changes exactly the 10 fields in the 7 sessions your preview shows, each to the preview's value, and nothing else. Anything else, stop and show me.
> Q2: (a), local time with its offset.
> Q3: separate phase; 370 ships F10 only.

## The format

`YYYY-MM-DDTHH:MM:SS.mmm+00:00`, for example `2026-10-06T19:42:07.123+00:00`.
It is `datetime.now(timezone.utc).isoformat(timespec="milliseconds")`: fixed
width, 29 characters. The month start is `2026-10-01T00:00:00.000+00:00`.

The reasons are in S0-4:
- the month start, the API's `since` and the CLI's filters already compare
  in the `T` shape;
- the offset is in the string;
- three fraction digits make it ECMAScript's own date-time format, which
  every JavaScript engine must parse.

## Logic

1. **`src/motodiag/core/timestamps.py` (new):**
   - `utc_now() -> str`: the format above.
   - `to_utc(value) -> str`: one rule for a stored value.
     - A naive value with a `T` is local time, written by the old
       `datetime.now().isoformat()`.
     - A naive value with a space is SQLite's `CURRENT_TIMESTAMP`, so UTC.
     - An aware value is converted.

     The result is the format above. Used by migration 079.
   - `local_display(value) -> str`: an aware value becomes local
     `YYYY-MM-DDTHH:MM:SS`. Any other value is returned as given. The old
     rows were already local, and nothing here may guess at a string it
     cannot parse.
   - `convert_session_times_079(conn) -> int`: migration 079's
     `post_apply`. It applies `to_utc` to `created_at`, `updated_at` and
     `closed_at` of every `diagnostic_sessions` row, returns the number of
     fields changed, and is idempotent.
2. **`core/session_repo.py`:**
   - all nine stamps call `utc_now()`;
   - `_month_start_iso()` returns the UTC month start in the same format,
     and its 191B note is replaced by a statement of the format;
   - `append_note`'s in-text stamp is local time with its offset,
     `datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")`,
     for example `[2026-10-06T15:42-04:00]` (Q2a).
3. **`api/routes/sessions.py:_parse_since`:** the cutoff is written in the
   session format, and an ISO cutoff with any offset is converted to UTC. A
   naive ISO cutoff is read as UTC, as `shop/analytics.py` reads one.
4. **`cli/diagnose.py`:**
   - `_short_ts` goes through `local_display`;
   - `diagnose list`'s Created column uses `_short_ts`;
   - `--since` and `--until` are the user's local day or time, converted to
     UTC in the session format. `--until DATE` is inclusive through
     23:59:59.999 local.
5. **`reporting/builders.py`:** the Timeline rows (Created, Updated, Closed)
   go through `local_display`.
6. **`memory/compile.py:_date_of`:** `local_display(value)[:10]`, so an
   evening session is dated by the local day.
7. **Migration 079** (`session_times_utc`):
   - `upgrade_sql` is a comment;
   - `post_apply` is `motodiag.core.timestamps:convert_session_times_079`;
   - `rollback_sql` turns each `+00:00` value back into naive local
     `YYYY-MM-DDTHH:MM:SS.SSS` with SQLite's `'localtime'` modifier, the
     shape the code before 079 writes;
   - `SCHEMA_VERSION` 78 → 79.
8. **The deploy:**
   - `370_deploy_scope.json` names `diagnostic_sessions` and the ten fields,
     each with its `to` value from `370_live_rows_preview.out`;
   - `deploy.py dryrun 370`, then the committed exact diff;
   - `apply-live` only if that diff changes exactly the ten fields to the
     preview's values and nothing else. Otherwise stop and show the
     operator.

   Every migration also adds one `schema_version` row. If the dry run shows
   it, that row is not one of the ten fields, so it is shown to the
   operator before `apply-live`.

## Key Concepts

- The SQL comparison `created_at >= month_start` is a text comparison; both
  sides must share a shape and a clock.
- The clock seam: `session_repo` and `timestamps` each import `datetime`,
  and a test replaces that name with a frozen subclass under
  `TZ=America/New_York` (`time.tzset()`), restored afterwards.
- Legacy naive values in tests (and anywhere else) still read as before;
  only aware values are converted for display.

## Verification Checklist

- [ ] `tests/test_phase370_session_utc.py`, with the clock frozen at
      2026-10-31 21:42:07 EDT (2026-11-01 01:42:07 UTC):
  - [ ] the moment straddles (local the 31st, UTC the 1st), and a naive
        local stamp written then is not counted: the window is live
  - [ ] a session created then counts toward November; one created at
        2026-10-31 19:30 EDT counts toward October, not November
  - [ ] every writer stamps the format: create (both), update, symptom,
        fault code, diagnosis, close, reopen, note's `updated_at`
  - [ ] the note's in-text stamp is `[2026-10-31T21:42-04:00]`
  - [ ] gate 9's `test_full_lifecycle` and the six 178 quota tests pass at
        that moment, in a spawned pytest with `tests/support/frozen_clock.py`
  - [ ] readers: `_short_ts`, `diagnose list` and its `--since`/`--until`,
        the report Timeline, `_date_of`, and the API's `since` with an
        offset
  - [ ] migration 079: the three shapes are converted, `None` is untouched,
        a second run changes nothing, and rollback returns naive local
- [ ] `370_mutate.py`: every mutation red. The first is the planted return
      to local time in `create_session_for_owner`.
- [ ] 244G's scanner over the new test files
- [ ] `wholetree.sh --full` on the committed HEAD; the regression of record
- [ ] deploy: dryrun diff committed, operator scope met, `apply-live`, live
      diff
- [ ] `verify_phase.sh`

## Risks

- **Hermes on a device is not tested here.** The format is the
  ECMAScript-specified one, which removes the implementation-defined case
  (six fraction digits) the app parses today.
- **TZ changes inside an xdist worker** affect the whole process: the
  fixture restores `TZ` and calls `time.tzset()` in teardown.
- **Rollback is lossy in microseconds** (milliseconds are kept). Only tests
  and emergencies roll back.
- **Existing tests may assert the old naive shape.** The related suites run
  before the regression, and any that change are listed in Results.

## Results

(v1.1)
