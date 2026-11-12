# Phase 371B — Step 0: the payments alarm's check-in sends its key once (F273)

**Written 2026-11-11** on the Mac, by the advisor session, the only writer,
on `phase-371B-the-alarm-sends-its-key-once` from `master` at `17e4692`
(F273 and F274 filed). The prompt is
`docs/prompts/371B_the_alarm_sends_its_key_once.txt`, the operator's two
messages word for word.

Classification: **extension.** One function's request headers change
(`monitor.checkin`). There is no new module, setting, migration or table,
and the server's error reports (`Sender`) are not touched.

## S0-1. The failure, live

- **The operator's report** (2026-11-11). Sentry's list of cron monitors
  is empty. The payments feed's log has one line every 5 minutes since
  21:09:56 EST, when the feed started: "payments feed: the check-in to
  (the project's Sentry address) answered 401 Unauthorized". The desktop
  reaches the host.
- **The desktop test block** (the advisor's, run by the operator the same
  night, ALL GOOD). It used the code at `43ccd1b`, the live settings file,
  and one check-in body as the feed sends it:
  - posted as the feed posts it, with the key in the address and in
    `X-Sentry-Auth`: "401 Unauthorized. Sentry says: multiple
    authorization payloads detected";
  - posted with the key in the address only: "202 Accepted";
  - `motodiag telemetry check`, the server's error-report path: accepted,
    status 200.

  So the key in `server.env` is the project's, and the fault is the second
  copy of it.

## S0-2. The code

- `git grep -n "X-Sentry-Auth" -- src` gives 2 lines. The second is right
  and stays.
  - `src/motodiag/telemetry/monitor.py:59`: the check-in.
  - `src/motodiag/telemetry/sender.py:181`: the error reports. They post
    to `envelope_url` (`dsn.py`), an address with no key in it, so the
    header is their only copy.
- `checkin_url` (`monitor.py` line 33) is
  `<scheme>://<netloc>/<prefix>api/<project>/cron/<slug>/<public key>/`.
  The key is already in the path.
- `git grep -n "monitor.checkin(" -- src` gives 1 line:
  `src/motodiag/payments/event_feed.py:426`, `_Job.checkin`, which
  `run_forever` calls after each round. That is the only caller.

## S0-3. Sentry's rule

Read on 2026-11-11 from Relay, Sentry's ingest server (`getsentry/relay`,
`master`):

- **The order Relay reads a key in.** `auth_from_parts`, in
  `relay-server/src/extractors/request_meta.rs`, reads it from:
  1. `X-Sentry-Auth`, when the value begins with "Sentry ";
  2. then `Authorization` with the Sentry scheme;
  3. then Basic auth;
  4. then a query string holding `sentry_`;
  5. then the key in the path.
- **A second key is refused.** Any second source returns
  `BadEventMeta::MultipleAuth`, "multiple authorization payloads
  detected". Relay does not compare the values.
- **That refusal is a 401.** `IntoResponse` maps `MultipleAuth`, like
  `MissingAuth`, to 401.
- **The routes.** `relay-server/src/endpoints/mod.rs` routes both
  `/api/{project_id}/cron/{monitor_slug}/{sentry_key}` and
  `/api/{project_id}/cron/{monitor_slug}`, each with and without a
  trailing slash. `monitor.rs` answers GET and POST, and 202 on success.
- **The documentation.** `docs.sentry.io/product/crons/getting-started/http/`
  puts the key in the path. Its POST example sends `Content-Type` and no
  auth header.

## S0-4. The tests

`git grep -n "X-Sentry-Auth" -- tests` gives 4 lines in 2 files:

- **`tests/test_phase343_sender.py`, 3 lines** (96, 241, 259): the error
  reports' header. They are right and stay.
- **`tests/test_phase371_monitor.py:49`** asserts that the check-in's
  header holds the key. Its `FakeTransport` answers 202 to any post, so
  nothing in the suite could refuse the key sent twice.

## S0-5. What 371 locked

`docs/phases/completed/371_implementation.md`, item 3, fixed:
- the address's shape;
- the body: interval 5 minutes, margin 10, `max_runtime` 5, UTC;
- the transport's signature;
- that no log line carries the key;
- that the check-in is sent "with the `X-Sentry-Auth` header
  `Dsn.auth_header` already builds".

371B keeps every one of these but the last. Its finish line asked the
fake transport to receive "the auth header with the key", which is the
line this phase reverses.

## S0-6. The one choice, and why it is not a fork

There are two ways to send the key once:
- **in the path, with no header.** This is Sentry's documented example,
  and the desktop's second check-in proved it with the live key;
- **in the header, with an address without the key.** Relay routes that
  too.

Chosen: the path. It is the documented example. It is the shape the
desktop proved on 2026-11-11, and it changes one line. Both ways ship the
same behaviour, a check-in accepted with one key, so this is not a fork
under rule 1. It is decided here.

## S0-7. The verbs

The row promises "the alarm's check-in sends its key once". The entry
point that reaches it is the payments feed: `motodiag payments feed run`,
which the unit `motodiag-payments.service` runs.

- `test_run_forever_checks_in_at_300_second_steps`
  (`tests/test_phase371_monitor.py`) already drives the feed's loop
  through the check-in. It stays.
- The new test drives `monitor.checkin` through the real `urllib_transport`
  to a stand-in on loopback that applies Relay's rule.

## Rule-1 stops

None. No threshold or rule's definition changes. No live-database change.
The desktop step after the merge restarts the payments feed, which needs
the operator's Ubuntu password.
