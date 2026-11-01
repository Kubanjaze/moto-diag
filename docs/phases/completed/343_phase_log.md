# Phase 343 — phase log: Telemetry + crash reporting (Sentry)

**Status:** Complete

Built 2026-11-01 by the Chief Engineer in a fresh clone of
`phase-343-telemetry-crash-reporting-sentry`, inside the fleet's fence, the
only writer. The plan is `343_implementation.md` v1.0, approved on issue
#50. Fix round 1 (the Red Team's round 1) has two bug fixes.


## 2026-11-01: The operator's answers to the Chief Engineer's stop

> Go with your picks on 2 to 5, plus blank anything that looks like an email address or phone number. The Sentry project motodiag-api exists and the key is in the server's settings file (server.env).

## 2026-11-01: The Chief Engineer reads the answers (item 1)

Read in this session, before any code. The heading "The operator's answers
to the Chief Engineer's stop" is on the branch (`dc0ab5a`), so there is no
second stop. What each part decides, applying the words literally:
- **(a) the account and the key:** confirmed in the operator's words: the
  project `motodiag-api` exists and the key is in `server.env`. No value
  was quoted, and none is written anywhere here.
- **(b) the client:** "go with your picks" kept the Captain's pick, the
  repository's own client over Sentry's envelope protocol. No SDK, no new
  dependency, no new skip.
- **(c) replay and the phone:** kept the pick: no session replay and no
  crash SDK in the phone in this phase; the backend only.
- **(d) what an event carries:** kept the pick, and widened by the
  operator's "plus blank anything that looks like an email address or
  phone number". Written into `redact` as two more patterns beside the
  `mds_` token. The rule as written: an email is `local@domain.tld`; a
  phone number is a run of 7 to 15 digits, optionally led by `+`, whose
  digits are separated by at most one space, dot, dash or bracket each,
  and which does not touch a letter or digit on either side. That also
  blanks a date such as 2026-11-01 inside a message; the operator's
  "anything that looks like" is read as erring on the side of blanking.
- **(e) the numbers:** kept the picks: transactions sampled at 0.1, every
  error sent, a queue of 100 events per worker, a 5-second transport
  timeout, a 2-second flush at exit.

Row 397 checked on master: `**CLOSED 2026-11-01.**` (`git show
master:docs/ROADMAP.md`, line 676). Nothing stands in the way.

## 2026-11-01: Item 2, the DSN, the settings and the mask

`telemetry/dsn.py`, three settings on `Settings` (with the property
`telemetry_environment_name` for the fallback to `env`), and the mask in
`config show` widened to `SECRET_SETTING_NAMES = ("api_key", "sentry_dsn")`.
The `stripe_webhook_secret` gap is filed as F244. `tests/test_phase343_dsn.py`
and `tests/test_phase02_config.py`: 34 passed. The two controls (a repr that
prints the key, a mask bypassed for `sentry_dsn`) each turn the assertion
they control.

The whole-tree command's fast mode on item 2 alone failed one test,
`test_phase209B_integration_gaps.py::test_no_new_unreachable_module`:
`motodiag.telemetry` and `motodiag.telemetry.dsn` reach no entry point
until item 5 wires them. The allowlist was not touched; items 2 to 5 go
in one commit, after the wiring.

## 2026-11-01: Items 3 to 5, the events, the sender and the middleware

- `telemetry/events.py`: `redact` (session token, email, phone, the
  500-character cut), `error_event`, `transaction_event`,
  `message_event`. A frame outside the package keeps only the part after
  `site-packages`, else the bare file name, so no home directory travels.
  `tests/test_phase343_events.py`: 23 passed.
- `telemetry/envelope.py` and `telemetry/sender.py`. The transport
  returns `(status, reason, headers)`, not the plan's `(status,
  reason_text)`: the 429 pause needs the `Retry-After` header, and the
  plan's two-value answer has no way to carry it.
  `tests/test_phase343_sender.py`: 20 passed. In the queue test the
  first capture is taken by the thread and held at the fake, so the
  queue's 100 places are free for the 150 captures that follow: 100
  accepted, 50 dropped, in under 100 ms.
- `api/telemetry.py`, the call in `app.py` before `AuditMiddleware` and
  the ready line's `telemetry=on <host>/<project>` or `telemetry=off`;
  `_unhandled_handler` calls `capture_crash` after its log line. The skip
  rule is one function, `skipped()`, so a test can remove the `OPTIONS`
  skip as a control. `tests/test_phase343_api.py`: 18 passed. It built a
  fresh database per test at first (44 s for 18); it now builds one per
  module and copies it (8.6 s).
- `scripts/code_quality.py counts`: ruff 1108, mypy 202, complex 25,
  big 5, helpers 19, swallowed 22, every one at its pin.

## 2026-11-01: Items 6 and 7, the commands and the documents

- `cli/telemetry.py`, registered before `register_completion`: `status`
  (0 on, 1 off, 2 malformed) and `check` (0 on a 2xx, 1 on another status
  or a transport error, 2 with no DSN or a malformed one). The transport
  seam is the module's `TRANSPORT`. The fast mode run before this item
  failed one more test, `test_no_new_orphan`, on `message_event`, which
  only `check` calls; it is wired now.
- `docs/guide/telemetry.md` (new), the install guide's sentence, the
  launch checklist's note dated 2026-11-01 under the Phase 209B
  correction, and the guide on `BACKEND_DOCS`.
- The planted-command control: with `motodiag telemetry prune` added to
  the guide's `motodiag telemetry status` block,
  `tests/test_phase208_docs.py::TestDocumentedCommandsExist::test_commands_resolve`
  failed ("`telemetry` has no subcommand 'prune'"; 1 failed, 19 passed);
  with it removed, 20 passed. The guide was restored from a copy and
  `git diff` showed it unchanged.
- `tests/test_phase343_cli.py`: 12 passed.
- `COLLECTED_TEST_FLOOR` 12293 → 12387, by a diff of collected ids
  against `dc0ab5a`: +94 -0, all five new files.

## 2026-11-01: The mutations

`docs/phases/in_progress/343_mutate.py`, the thirteen the plan names, each
reverted on its own; the run's output is `343_mutate.out`: **13/13 red**.
M4 (a blocking `put`) is red by timing out at the script's 180-second
limit: with the fake transport held, the 101st capture blocks the test
instead of failing it, and the script counts a run past its limit as red.

## 2026-11-01: The guide's restart command corrected

`docs/guide/telemetry.md` said `systemctl --user restart`; the API's unit
is a system unit (`/etc/systemd/system/motodiag-api.service`, installed
by `install_unit.sh`), restarted with `sudo systemctl restart`, as 345's
handoff does. A document fix, before the regression of record. The first
`wholetree.sh --full` attempt was stopped by the session's 10-minute limit
for a background command, not by a failure; it was started again with a
longer limit.

## 2026-11-01: The regression of record

`wholetree.sh --full` on `198066b`: exit 0, "PASSED — 5057 passed, 36 skipped" (1019.4 s wall), record written for that commit. Then `regression.sh` on the clean tree, its lines as printed:

Regression of record: 12282 passed, 0 failed, 105 skipped, 0 errors at `198066b` (36 min 55 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
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
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
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
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
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
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Line coverage of record: 88.04% at `198066b` (the pin is 87.50%): 0.54 points above it; raise COVERAGE_PERCENT to lock it in

The coverage line suggests raising `COVERAGE_PERCENT`; it is left at 87.5, because raising it now would change code after the regression of record. It is named in the handoff for the next phase.

## 2026-11-01: Close-out

v1.1 written, the phase's files moved to `docs/phases/completed/`, the
ROADMAP row closed, the root `phase_log.md` pointer and the handoff
`docs/handoffs/2026-11-01_343_closed.md` written. The proof against the
real Sentry project is the operator's `motodiag telemetry check` on the
home desktop after the merge, in the handoff; the fence has no network.

## 2026-11-01: Fix round 1, the Red Team's four points

The Red Team sent PR #52 back with two code points and two wording
points. The code points are bug fixes #1 and #2; the wording points are
the entry after them.

Two shell commands were refused by the edit guard in this round, and both
were redone with the Edit tool; the guard was not touched:
- `cp` of the round's `sender.py` back over itself after a control run
  (the guard: "`cp` writes into src/motodiag/telemetry/sender.py");
- an empty `cat >> tests/test_phase343_api.py` heredoc (the guard: "the
  redirect `>>` writes into tests/test_phase343_api.py").

### Bug fix #1 — 2026-11-01 — the sender's send loop caught every exception

- **Issue:** `Sender._post` caught `except Exception` around the transport
  call. A programming error (a `TypeError` from a bad transport or header)
  was counted as a failed send, warned once, then logged at DEBUG for the
  rest of the minute.
- **Root cause:** the handler named no error; the failures plan item 4
  expects are a refused connection and a timeout.
- **Fix:** the handler names `OSError` (which covers `URLError` and
  `socket.timeout`) and `http.client.HTTPException` (a broken answer such
  as `IncompleteRead`, which `urlopen` raises and which is not an
  `OSError`). Anything else raises out of the sender's thread and is
  printed by `threading.excepthook`; `capture` and the API are unaffected,
  and `close` still returns within its flush limit.
- **Files:** `src/motodiag/telemetry/sender.py`,
  `tests/test_phase343_sender.py` (+2:
  `test_a_broken_http_answer_is_a_failed_send`,
  `test_a_programming_error_is_not_swallowed`),
  `tests/test_phase255B_collected_test_floor.py` (12387 → 12389).
- **Verified:** with the handler put back to `except Exception` by a
  temporary edit, `test_a_programming_error_is_not_swallowed` failed (1
  failed, 1 passed); with the fix, `tests/test_phase343_sender.py` 22
  passed.
- **Commit:** this entry's commit.

### Bug fix #2 — 2026-11-01 — the API tests' sender double could drift from the real Sender

- **Issue:** every API test put the hand-written `FakeSender` at
  `app.state.telemetry`. No test ran `TelemetryMiddleware` or
  `capture_crash` against a real `Sender`, and nothing tied
  `FakeSender`'s attributes to `Sender`'s: a renamed attribute on `Sender`
  would have broken production with the API tests green.
- **Root cause:** a self-validating double (the F9 family's
  mock-versus-runtime drift).
- **Fix:** `tests/test_phase343_api.py` gains `TestTheDoubleMatchesTheSender`:
  the names the API module reads from `sender.` are taken from its source
  and pinned; each is present, and callable alike, on `Sender`,
  `NullSender` and `FakeSender`; and a crash goes through a real `Sender`
  with a `FakeTransport`, whose envelopes carry the error event and the
  500 transaction.
- **Files:** `tests/test_phase343_api.py` (+8),
  `tests/test_phase255B_collected_test_floor.py` (12389 → 12397).
- **Verified:** with `Sender.server_name` renamed by a temporary edit, two
  of the new tests failed and the 18 that use `FakeSender` passed (2
  failed, 24 passed); with it put back, 26 passed.
- **Commit:** this entry's commit.

