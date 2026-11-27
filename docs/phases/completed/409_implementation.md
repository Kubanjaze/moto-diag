# Phase 409 — A public web address for the server

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-11-27

v1.1 is the close-out: each section below now says what was built, where
it differs from the v1.0 plan, and the Results and Deviations are filled.
The plan was written before any code. Built by a builder session, the home desktop's
main chat (K149, the operator's "409: B"), from its draft pull request 98
(`prebuild-409-public-address`, head `acd36ac`) and the fleet's Step 0
(`phase-409-a-public-web-address-for-the`, `4b31ded`). Written from
`409_step0.md` (the fleet's report and the builder's section below it),
ROADMAP row 409, `docs/prompts/409_a_public_web_address_for_the_server.txt`
and PR 98's plan page (`docs/reports/2026-11-25_409_prebuild_plan.md`),
checked against the tree at `a238aa6`. The advisor on the Mac reviews the
branch read-only before the operator merges.

## Goal

The live server answers at one https name on the internet,
`https://api.getmekno.com`, so a phone on any network reaches it without
Tailscale, and nothing else on the home desktop becomes reachable. The
server is made ready for anonymous callers from anywhere before the name
goes on, and the tailnet name keeps working beside it.

Why now: the operator releases to individuals first and has no shops yet
(the advisor's note of 2026-11-26), so without this phase nobody outside
the tailnet can use the app, and Apple's review for a public TestFlight
link cannot reach the server.

## The operator's answers this plan builds to

- **K149 (2026-11-26):** "409: B": this session builds it; the advisor
  reviews; the operator merges.
- **The six answers of 2026-11-25** (issue 104), unchanged:
  1. the way in is a Cloudflare Tunnel;
  2. the name is `api.getmekno.com`;
  3. the API pages are off in prod;
  4. share links stay off;
  5. K119's 300 MB manual limit stays, with chunked uploads before 410 and
     329, and the app explains the limit in its own words;
  6. the open shop route closes before the tunnel goes on.
  The outside account is the Cloudflare account that holds getmekno.com.
- **Agreed with them:** the privacy page names Cloudflare for the app's
  traffic before the tunnel goes on; the app's copy of the API is
  refreshed before the merge.

## Logic

### 1. PR 98's hardening, brought in by a merge

PR 98's three commits come onto this branch by `git merge` of
`origin/prebuild-409-public-address` (no cherry-pick, no rebase, no
force-push; the draft branch is left as it is). Measured in Step 0: the
merge onto `a238aa6` is clean, and its tests with 210's pass (146).
**As built:** merged in `10fe0f3`. PR 98 was left open rather than
closed: its head `acd36ac` is inside this branch, so GitHub marks it
merged when pull request 111 merges.

What it carries, as its plan page lists it:
- `core/config.py`: `api_docs_enabled` (default on), `api_allowed_hosts`
  (default empty: any host), `security_headers_enabled` (default on),
  `login_failure_limit` 10 and `login_failure_window_s` 900,
  `api_max_body_bytes` 1 MiB.
- `auth/login_throttle.py` (new): failed logins per name and address, and
  per name from every address (×5), in a sliding window; 429 with
  Retry-After through the existing handler.
- `api/routes/auth.py`: the login checks the guard before the password.
- `api/middleware.py`: `SecurityHeadersMiddleware` (nosniff, no framing, no
  referrer; HSTS on https only) and `BodySizeLimitMiddleware` (a declared
  non-multipart body over the cap is 413).
- `api/app.py`: the docs switch, the two middlewares, Starlette's
  `TrustedHostMiddleware` when hosts are set, the guard reset per app.
- `api/routes/meta.py`: `/healthz` logs a database error, answers only
  "db unreachable".
- `api/routes/shops.py`: `GET /v1/shops/{id}` needs a signed-in active
  member; a missing shop is 403, so ids cannot be walked (answer 6).
- Tests: `tests/test_phase409_public_hardening.py` (22), and the two old
  tests the closed route moved (`test_phase175_api_foundation.py`,
  `test_phase176_auth_billing.py`).

### 2. The launch check's ninth condition: the public name

The scope: "210's launch check gains a condition: the public name answers
over https with a valid certificate, and nothing it should not reach
answers." In `src/motodiag/launch/check.py`:

- `public_condition(settings)`, named "the public address answers over
  https", after the eight, in `run_conditions` (`5fd8fa6`). As built it
  takes no `fetch` argument; tests replace `check.public_status`.
- **Not ready** when `public_base_url` is empty, when it is not `https`, or
  when its host is a loopback, private or link-local address
  (`core/public_url.py`'s own rules). As built those rules also refuse
  carrier-grade NAT, `100.64.0.0/10`, where Tailscale's addresses live
  (bug fix #1, `5138fef`): Python's `is_private` does not cover it.
- Otherwise three GETs to that one host, never through a proxy, with
  Python's default certificate checks:
  - `/healthz` answers 200 with `"status": "ok"`;
  - `/docs` answers 404 (answer 3);
  - `/v1/shops/1` answers 401 with no credential (answer 6).
  A certificate failure is its own detail ("the certificate is not
  valid"); a timeout or refused connection is "did not answer".
- **What 210 locked stays:** the check writes nothing; no detail carries
  a settings value (the host is not printed, only words); the one outside
  connection is to the host `public_base_url` names, and
  `loopback_json` keeps refusing any other host. A new reader,
  `public_status(settings, path)`, returns a status code and at most
  64 KB of body, and refuses any path but the three and any host but the
  configured one (`NotPublicName`). As built it names itself,
  `User-Agent: motodiag-launch-check/409`: Cloudflare refuses urllib's
  default name with 403 (bug fix #2, `1456f45`).
- The CLI prints nine lines; `ALL GOOD` needs all nine ready. Until the
  tunnel is on, the ninth says NOT READY, which is the truth: launch to
  anyone off the tailnet needs it.

"Nothing else on the desktop answers" is measured from outside, by the
handoff's outside check (ports 22 and 8000 on the public name; the phone
on mobile data), not by the check, which runs on the desktop itself. As
built, 8080 is not checked: Cloudflare's own edge answers it on every
name it carries (bug fix #3, `19d5230`).

### 3. The privacy policy, version 1.2: Cloudflare for the app

`docs/legal/privacy.md` gains one item in "The services it goes to", the
line drafted on 2026-11-25 for the operator's wording:

> **Cloudflare**, for the connection between the app and Mekno's server:
> every request the app sends passes through Cloudflare, which opens it to
> deliver it and keeps standard request logs.

Its version line becomes `Version 1.2 — 2026-11-27`, and
`python scripts/site_build.py legal` rebuilds `site/privacy/index.html`
from it (`tests/test_phase408_site.py` holds the page to the build). The
terms are not changed, so `TERMS_VERSION` stays 1.1 and nobody is asked to
accept again (`docs/legal/README.md`: the privacy policy keeps its own
number; an acceptance counts against the terms' version). The policy's
own "Changes" rule ("we tell users in the app before it applies") is met
because the line is live before the tunnel is, and today's only accounts
are the operator's own. The site goes live by the operator's upload, a
handoff step before the tunnel's.

**The words are the operator's.** The line goes on the branch as drafted;
the operator's yes to it, or their own wording, is asked once with the
v1.0 reply. Until then the tunnel block refuses to run (it checks the live
page for the line). **As built** (`cf875f9`): the operator chose "Yes, use
it as written" at 03:03 UTC. The advisor records its K-id after the merge.

### 4. The app's half (moto-diag-mobile)

Two agreed items, one pull request on `moto-diag-mobile`, from this
session, before the server's merge:
- **The app's copy of the API refreshed** from this branch's
  `/openapi.json` (`npm run refresh-api-schema` then
  `npm run generate-api-types`), so `GET /v1/shops/{id}` carries its
  credential and its 401/403.
- **The app explains the 100 MB limit.** Through the public name,
  Cloudflare refuses any body over 100 MB with its own 413 page, before
  the server sees it. In the app that is a video: the app uploads no
  manuals, photos are capped at 25 MB, and the server allows a video up
  to 512 MB (`api/routes/videos.py`, `PER_FILE_BYTES_CAP`), so a phone
  video of about a minute at 1080p is over. The video screen's upload
  error says, in its own words, that videos over 100 MB cannot be sent
  yet, and to record a shorter clip. Found in Step 0; it is answer 5's
  limit, met in the app's own place.

**As built:** `moto-diag-mobile` pull request 17, branch
`phase-409-app-half`, at `9837670`:
- `2d4f4de` is the API copy. Only the shop route's entry changed, and the
  file's old key order was kept so the diff shows only that route.
- `9837670` is the 100 MB message: a 413 that is not the server's own
  problem answer becomes "This video is over 100 MB…", and the helpers
  moved to `videoCaptureHelpers.ts`.

On the Mac the advisor got `tsc` and `eslint` clean and Jest 1368 of 1368.
The app's pull request merges first.

### 5. The handoff's blocks

Written to `docs/phases/in_progress/409_blocks/`, each a `bash <<'EOFn'`
heredoc ending ALL GOOD or SOMETHING IS OFF, naming the computer and the
window, `gh` with `-R Kubanjaze/moto-diag`, tested in the cloud against
stand-ins (`bash -n`, `shellcheck`, and each check made to fail on
purpose) before the advisor re-tests them. PR 98's six are the start,
re-read and changed where Step 0 found a gap:

**As built, the order changed** (Deviations): the settings come before the
tunnel, so nothing is public until the help pages are off and the host
list is in. The eight blocks are in `409_blocks/`, and its README gives
the order:
1. desktop measured (PC);
2. backup and server update (Mac);
3. site: 3a the zip (Mac), 3b the upload (Browser), 3c the check (Mac);
4. settings (PC);
5. tunnel created (Browser);
6. tunnel installed (PC);
7. outside check (Mac, then the phone);
8. undo (PC).

The v1.0 plan below is kept for the record.

1. **The desktop measured, read-only** (PC Ubuntu): every listening port
   and its address, `tailscale serve status` and Funnel off, the server's
   uvicorn and FastAPI versions (uvicorn 0.30 or later for the right-most
   forwarded address), each anonymous route's answer on loopback, whether
   `cloudflared` is installed, getmekno.com's name servers, and whether
   the privacy page carries the line. This is Step 0's owed measurement.
2. **A backup, then the server on the merged code** (Mac Terminal, through
   `remote.py`): the server update moves code only (no migration, schema
   unchanged), but a copy of the live database is taken first, with
   Python's `sqlite3` backup API into `~/backups/motodiag/`, never through
   a `motodiag` command (F292). As built, the copy is `remote.py backup
   pre409` and the update is `remote.py server-update <merge>`, the Mac's
   existing desktop list.
3. **The privacy page live** (Mac Terminal, then the browser): the site's
   zip from merged master, uploaded to Cloudflare Pages by hand as every
   site change is.
4. **The tunnel made in Cloudflare** (Browser, no block): Networks,
   Tunnels, `mekno-api`, public hostname `api.getmekno.com` to
   `http://127.0.0.1:8000`.
5. **The tunnel installed on the desktop** (PC Ubuntu): refuses unless the
   privacy line is live and the server has the new code; the token is
   read without echo and never kept.
6. **The server's public settings** (PC Ubuntu): `server.env` copied
   first; `MOTODIAG_PUBLIC_BASE_URL`, `MOTODIAG_API_ALLOWED_HOSTS`,
   `MOTODIAG_API_CORS_ORIGINS`, `MOTODIAG_API_DOCS_ENABLED=false`,
   `MOTODIAG_API_SERVERS`. **Changed from PR 98:** the old settings are
   put back if the public name or the tailnet name stops answering, not
   only loopback (a wrong host list answers 400 on the public name while
   loopback stays healthy). Then `motodiag launch check`'s ninth line.
7. **The outside check** (Mac Terminal, off the tailnet's path, then the
   phone on mobile data).
8. **The undo** (PC Ubuntu): the tunnel removed, the settings put back.

## The plan of record

Row 25 of "Next, in order" in `docs/reports/2026-10-12_plan_of_record.md`:
409, built by "builder" (K149, 2026-11-26); before 329 (#26) and 410
(#27); 344 after all three (K140).

## Rule-1 stops anticipated

| stop | where | who |
|---|---|---|
| a login or a credential | the Cloudflare login and the tunnel's token (blocks 4 and 5) | the operator's hands |
| any server setting | block 6 | the operator's hands, from a tested block |
| the privacy policy's words | Logic item 3 | the operator's yes, asked once |
| a live-database change | none: no migration, no row changed; block 2's copy is a backup, not a change | no stop |
| a new threshold | the login guard's 10 and 50 per 15 minutes, the 1 MiB JSON cap: new limits, not changes to an existing one, read by the operator's advisor in PR 98 | no stop, recorded |
| a test it cannot make green | none known | — |

Never Funnel and never the LAN: no block touches `tailscale funnel` or a
listener address; block 1 checks Funnel is off and the server listens on
`127.0.0.1` only, and block 7 checks nothing else answers.

## Tests

- PR 98's 22 in `tests/test_phase409_public_hardening.py`, and its changes
  to the 175 and 176 tests.
**As built:**
- `test_phase409_public_condition.py` has 30 tests, including the
  User-Agent on the wire;
- `test_f64_public_url.py` gained 2 CGNAT cases;
- the 210 launch-check pins moved to nine;
- the legal-text and site pins moved to 1.2;
- mutations: `409_mutate.py`, 9 of 9 red;
- the floor went 13321 → 13378;
- the regression of record is under Results.

The v1.0 list:
- `tests/test_phase409_public_condition.py` (new): the ninth condition
  not ready with no address, with `http`, with a loopback or private host;
  ready on a stand-in that answers 200/404/401; each of the three answers
  wrong in turn (docs open, a shop's details without a credential,
  unhealthy); a certificate failure; no answer; the reader refusing any
  other host; no detail carrying the host; the CLI's nine lines.
- `tests/test_phase210_launch_check.py` and `test_phase210_wiring.py`: the
  pins of eight conditions move to nine, each change said in the log.
- The privacy page: `tests/test_phase334_legal_texts.py` (Cloudflare is
  named; the attribution and the contact line stay) and
  `tests/test_phase408_site.py` (the page is the build's output), with a
  pin that the line is present.
- Red first: the new tests run on the code before the change and fail
  where they should; mutations of the ninth condition (each check
  dropped, the scheme check dropped, the host refusal dropped) each turn a
  test red.
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids.
- The regression of record by `regression.sh` on a clean tree after
  `wholetree.sh --full`, with the seven quality counts at their pins. The
  advisor re-runs it on the Mac.
- The app: Jest for the changed screen's copy, and the type check, in the
  app's pull request.

## Non-goals

Self-serve sign-up (329) and the App Store (410); chunked uploads (dated
before 410 and 329, a finding); moving the server off the desktop;
Stripe's webhooks to the new address (the feed keeps asking Stripe, K65);
share links back on (answer 4); Funnel or the LAN.

## Planned items

- Findings to file before any document cites them (numbers from
  `next_f_number.sh`, which reads both repositories' files):
  - the open shop route, `GET /v1/shops/{id}`, gave anyone any shop's row,
    tax id included; closed by this phase; never reachable off the tailnet;
  - chunked uploads: K119's 300 MB manuals and the server's 512 MB videos
    against Cloudflare Free's 100 MB; due before 410 and 329;
  - the privacy page names Cloudflare for the app once the tunnel is on;
    closed by version 1.2 once it is live;
  - `fastapi>=0.110` is unpinned, and FastAPI 0.165 breaks three
    route-walking tests (`_IncludedRouter`); live runs 0.136.
- At close-out: issue 104 closed (not only its label taken off), the
  handoff with the live outcome, the row ✅.

## Deviations

1. **The settings before the tunnel.** v1.0 put the server's settings
   (its block 6) after the tunnel install (its block 5). As built, they
   are step 4 and the tunnel is steps 5 and 6. Then the help pages are off
   and the host list is in before anything is public, and the tunnel
   block refuses unless the settings are in.
2. **The backup through `remote.py`.** v1.0 said a `sqlite3` backup by
   hand. As built, `remote.py backup pre409` and `remote.py server-update`
   are used, the routes the Mac already has to the desktop.
3. **Four bug fixes.**
   - #1, CGNAT (`5138fef`).
   - #2, the reader's User-Agent (`1456f45`).
   - #3, block 7's ports (`19d5230`).
   - #4, the harness's Python (`a24b893`).

   Fixes #2–#4 share a cause, recorded in the log: a stand-in agreed with
   an unmeasured assumption. Each now has a case the old code fails.
4. **The 100 MB limit hits videos, not manuals.** Answer 5 spoke of K119's
   300 MB manuals, but the app uploads none; its videos are allowed
   512 MB. The app's message is on the video screen (F310 keeps chunked
   uploads dated before 410 and 329).
5. **F312 is a duplicate of F287.** It was filed before F287 was found,
   and is marked closed as its duplicate. The number is not reused.
6. **The app's API copy kept its old key order.** A full refresh reorders
   the whole file, so only the one changed route was patched in and
   regenerated. The advisor confirmed `api-types.ts` regenerates
   identical.
7. **One edit against the guard's rule.** The first draft of the ninth
   condition, and the one-line removal that proved #2's test red, were
   shell writes into `src/`. The guard's hooks had not loaded, since the
   session started outside the repository. Both are recorded in the log;
   everything else in `src/` and `tests/` went through the editor.
8. **PR 98 left open, not closed** (Logic item 1).
9. **Outside check ports.** 8080 is dropped (bug fix #3).
10. **The ninth condition's reader takes `(settings, path)`**, and
    `public_condition` takes no `fetch` (Logic item 2).
11. **The merge order.** The operator merges the app's pull request first,
    then the server's. Nothing else merges to master before step 2, which
    refuses unless master is exactly the server's merge.

## Results

- **The regression of record**, on the advisor's Mac, on a clean clone at
  `a24b893` with the app clone at `9837670` beside it: 13329 passed,
  0 failed, 49 skipped, 0 errors, 49 min 10 s, line coverage 88.75% (the
  pin is 88.00%). The 35 skip lines match 210B's. `wholetree.sh --full`
  before it passed: 5547 passed, 8 skipped. The commits after `a24b893`
  are documents only.
- **What shipped on the branch:**
  - PR 98's hardening;
  - the ninth condition;
  - privacy 1.2;
  - the eight tested blocks, with the harness at 30 of 30 and 6 of 6 and
    the advisor's real Mac checks of block 7;
  - findings F309–F313.
- **The app** (pull request 17): the API copy and the 100 MB message;
  Jest 1368 of 1368.
- **The desktop measured** (block 1, 15:33 UTC): loopback only, Funnel off,
  uvicorn 0.49.0, zone at Cloudflare. As expected before the merge, the
  help pages and a shop's details answer anonymously on loopback.
- **Live:** none yet. Steps 2–7 are the operator's after the merge, in
  the handoff's order. The handoff gets the live outcome once they run.
  Issue 104 is closed after the merge.

## Version history

| Version | Date | What |
|---|---|---|
| 1.0 | 2026-11-27 | The plan, before any code: PR 98 merged in, the launch check's ninth condition, privacy 1.2, the app's half, eight blocks. |
| 1.1 | 2026-11-27 | Close-out: as built in every section, eleven deviations, four bug fixes, the regression of record at `a24b893` (13329 passed), live steps left to the operator. |
