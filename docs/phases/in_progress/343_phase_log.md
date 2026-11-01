
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
