# Phase 371B — The payments alarm's check-in sends its key once (F273)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-11-11

---

## Goal

A follow-on of 371. The operator, 2026-11-11: "give me either a code fix
as a PR or a one-line settings change", and later the same night, "Go
ahead and build 371B." Since live payments went on, Sentry has refused
every check-in, so the payments alarm (K65 (1)) has never worked.

After this phase:
1. the check-in sends the DSN's key once, in the address, as Sentry's
   HTTP check-in page shows, so Sentry accepts it;
2. a test's stand-in refuses a key sent twice, as Sentry's ingest server
   does, so the mistake cannot come back unseen;
3. after the merge, one desktop block updates the server, restarts the
   payments feed and checks its log for refused check-ins.

## The plan of record

Not in "Next, in order". It repairs 371, row 13 there, which is closed.
K80 (2026-11-11) records the operator's words, "Go ahead and build
371B.", and puts it before 372, the next entry.

## Logic

The causes and measurements are in `371B_step0.md`, S0-1 to S0-7.

1. **`src/motodiag/telemetry/monitor.py`.** `checkin` sends one header,
   `Content-Type: application/json`, and the `X-Sentry-Auth` header goes.
   The module docstring says the key goes once, in the path, because
   Sentry's ingest server refuses a key sent twice (F273). Nothing else
   changes: the address, the body, the transport, the logging, and the
   return value.
2. **`tests/test_phase371_monitor.py`.**
   - `test_the_post_carries_the_url_the_header_and_the_schedule` becomes
     `test_the_post_carries_the_key_once_and_the_schedule`. It asserts
     that the headers are exactly `{"Content-Type": "application/json"}`.
     The rest of the test is unchanged.
   - The docstring's "the auth header" becomes "the key once, in the
     address".
3. **`tests/test_phase371B_checkin_key_once.py`**, new.
   - **The stand-in.** It runs on loopback with Relay's rule for the cron
     route, in Relay's order: `X-Sentry-Auth` beginning "Sentry ", then
     `Authorization` with the Sentry scheme, then a query holding
     `sentry_`, then the key in the path.
     - A second source gives 401 with
       `{"detail": "multiple authorization payloads detected"}`.
     - No source gives 401, "missing authorization information".
     - One source gives 202.
     - The envelope route takes the header alone and answers 200.
   - **The tests.**
     - The check-in, through the real `urllib_transport`, returns True,
       and the stand-in saw the key once, in the path, with no auth
       header.
     - The known-bad: 371's request, with the key in the path and in
       `X-Sentry-Auth`, gets 401 with Relay's words.
     - A request with no key gets 401.
     - The error reports, `Sender` to the envelope route, are still
       accepted.
4. **Finish line.**
   - `371B_mutate.py` turns the new tests red on each of four mutations.
     Each change is made in a copy, never the checkout:
     - M1: the `X-Sentry-Auth` header comes back;
     - M2: an `Authorization: Sentry` header is added;
     - M3: `?sentry_key=` is added to the address;
     - M4: the key is left out of the address.
   - With no mutation, the copy is green.
   - Master's `monitor.py` fails the new check-in test, which is the
     operator's 401 on the desktop.
5. **The record.**
   - `COLLECTED_TEST_FLOOR` is raised by a diff of collected ids.
   - The regression of record runs on the Mac.
   - v1.1 and the phase log are written.
   - The handoff carries the desktop block, tested first on the Mac
     against stand-ins with planted faults.
   - F273 closes when the desktop's check-in is accepted after the merge,
     recorded in the handoff's "After the merge".

No migration. The phase adds no table, column or index, and changes no
row.

## The change log's three newest entries

- **2026-10-29 — rule 6: the code's counts only improve, and the weekly
  page (Phase 393, K54).** This became
  `tests/test_phase393_quality_ratchet.py`: the six measured counts are
  held against their pins both ways, and the coverage gate is wired into
  `.claude/skills/closeout/regression.sh`. This phase removes one header
  and adds one test file. It must add no finding to any count, and lowers
  a pin only if a count falls.
- **2026-10-26 — R8: an operator paste block's `gh` names its repository
  (before Phase 391, F222).** This became R8 in
  `.claude/skills/closeout/roadmap_check.py`, run with every suite and on
  every push. The handoff's desktop block calls no `gh`.
- **2026-10-22 — `fleet` joins the procedure folders (after Phase 387).**
  No check: the entry says the row is text only and no check reads the
  table.

## Rule-1 stops anticipated

- **A real fork: none.** There is one choice, the key in the path or the
  key in the header. Both ship the same behaviour, and Step 0, S0-6,
  decides it.
- **A threshold or a rule's definition: none.** The check-in's interval,
  margin and body are unchanged.
- **A test that cannot be made green: none known.** One existing test's
  assertion is turned around (S0-4). If any other test pins the header,
  that is a stop.
- **A login or a credential: the operator's Ubuntu password**, after the
  merge, for the desktop block's restart of the payments feed. No test
  and no step of the build reads a key.
- **A live-database change that alters or deletes rows: none.** No
  migration.

## Tests

- `tests/test_phase371_monitor.py`: one test renamed and its header
  assertion turned around; the docstring.
- `tests/test_phase371B_checkin_key_once.py`: the stand-in, and four
  tests: the check-in accepted, the known-bad refused, no key refused,
  and the error reports accepted.
- Mutations, `371B_mutate.py`: M1 to M4, red; the copy green without them.

## Non-goals

- F274, the status that hid the refusals: what `feed status` says about
  the check-ins is a later phase.
- Logging Sentry's answer body.
- `Sender`, the error reports.
- The check-in's body, interval and margin.
- The guide's Sentry steps.
- Restarting the API service after the merge: it does not use the
  check-in.

## Planned items

- [ ] the header goes; the docstring
- [ ] the 371 test turned around; the new stand-in and its four tests
- [ ] the mutations red, the copy green, master's code red
- [ ] the floor, the regression of record, the close-out, the handoff with
  the desktop block

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-11-11 | the plan |
