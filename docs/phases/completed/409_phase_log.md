# Phase 409 — phase log

**Status:** Complete. Closed 2026-11-27 on the branch (regression of record
at `a24b893`); the live steps are the operator's after the merge, in the
handoff. Started 2026-11-27 by the builder session K149
names (the home desktop's main chat), from
`docs/prompts/409_a_public_web_address_for_the_server.txt`.

## 2026-11-27 02:35 UTC — why a builder session, and where it starts

**The operator's words.** K149 (2026-11-26): "409: B": a builder session
builds 409 from its draft, pull request 98, with the six answers of
2026-11-25 unchanged; the advisor reviews; the operator merges. The K149
block ran on the Mac and ended ALL GOOD: K149 on master as `a238aa6`,
issue 104's comment posted, its labels `mission`, `needs-hands`,
`step0:done`.

**Where it starts.** A fresh clone of `master` at `a238aa6`, in the cloud.
Branch `phase-409-public-address`, new, from master. The fleet's branch
`phase-409-a-public-web-address-for-the` is the fleet's, so nothing is
pushed to it; its Step 0 commit `4b31ded` comes in by a merge.

**The guards in this session.** The session was started in the clone's
parent directory, so `.claude/settings.json`'s hooks (the push guard and
the edit guard) do not load for it (CLAUDE.md, "Start sessions at this
repository root"). Each is run by hand instead: `wholetree.sh` before
every commit, read by its exit code on its own, and
`pre_push_guard.sh`'s checks before every push. No `sed -i` or redirect
writes into `src/` or `tests/`; edits go through the editor.

## 2026-11-27 02:50 UTC — Step 0, the builder's section

Written into `409_step0.md` below the fleet's report. What it found:
- PR 98 merges onto `a238aa6` with no conflicts, and its tests with 210's
  pass, 146, on FastAPI 0.136.3 (live's line).
- On FastAPI 0.165.0, which the unpinned `fastapi>=0.110` installs today,
  three route-walking tests fail; to be filed.
- uvicorn 0.54 takes the right-most untrusted forwarded address, so a
  caller cannot pick their own bucket through Cloudflare; the desktop's
  version is read by the first block.
- The server takes videos up to 512 MB, so in the app it is videos, not
  manuals, that meet Cloudflare's 100 MB; the app uploads no manuals.
- The login guard's name-wide hold can lock a name's real owner out while
  a stranger guesses at it; written down, kept as built.

Classification: an extension of PR 98's reshape.

## 2026-11-27 03:05 UTC — v1.0, before any code

`409_implementation.md` v1.0 written: PR 98 by a merge, the launch check's
ninth condition, the privacy policy's version 1.2 (the operator's yes on
the words, asked once), the app's half, eight blocks. Committed and pushed
before any code, with the ROADMAP row saying so.

**The whole-tree command before this commit.** First run: 6 failed. Five
were `tests/test_phase293_manuals_api.py` on pypdf 7.0 (`add_js` removed),
the cloud venv's own install; live runs pypdf 6.14.2 and pypdfium2 5.15.2,
so the venv was pinned to those. One was
`tests/test_phase379_wholetree_output.py` under that run's load; it passed
alone. The finding_check's B2 also caught v1.0 citing the next F-number
before it was filed; the sentence now names the script instead. Second
run: `wholetree fast: PASSED — 3048 passed, 11 skipped`, exit 0.

## 2026-11-27 03:20 UTC — PR 98 merged in, and the findings filed

`git merge --no-ff origin/prebuild-409-public-address` (no conflicts), as
v1.0 Logic item 1 says. F309 to F312 filed in `docs/FOLLOWUPS.md` from
`next_f_number.sh` (both repositories: the app's F308 is the highest),
`d2adeef`.

**An edit made the wrong way, recorded.** The ninth condition's first
draft went into `src/motodiag/launch/check.py` through a Python heredoc
from the shell, the kind of write the edit guard blocks. The guard had
not loaded for this session (above); the change was then read back in
full and every later edit to `src/` and `tests/` goes through the editor.
The guard itself is untouched.

## Bug fix #1 — 2026-11-27 — a tailnet address passed as a public one

- **Issue:** `_host_is_unreachable_publicly` in `src/motodiag/core/public_url.py`
  returned no reason for `100.75.113.50`, the desktop's tailnet address,
  so `https://100.80.109.103` passed F64's prod start-up check as a public
  origin, and the ninth condition's first test run (one of 62 failed) took
  a tailnet address for the public name.
- **Root cause:** the function's comment said Python folds 100.64.0.0/10
  (carrier-grade NAT, where Tailscale lives) into `is_private`. It does
  not, on 3.11 to 3.13 (`ipaddress.ip_address('100.75.113.50').is_private`
  is `False` here). F64's own case for it used `http://`, so the scheme
  rule refused it first and hid the host rule.
- **Fix:** the shared address space checked by name (`_CGNAT`), with its
  own reason.
- **Files:** `src/motodiag/core/public_url.py`, `tests/test_f64_public_url.py`
  (two https cases).
- **Verified:** the two new cases red on the old function (2 failed, 20
  passed), green on the fix; with the ninth condition's and 210's: 84
  passed.

**Commit.** `5138fef`

## 2026-11-27 03:40 UTC — the launch check's ninth condition (Logic item 2)

`public_condition` and its reader `public_status` in
`src/motodiag/launch/check.py`, after 210's eight in `run_conditions`, as
v1.0 says. The reader builds its address from `public_base_url` alone
(scheme and host, nothing else), reads only the three probe paths, never
through a proxy, with `ssl.create_default_context()`; an HTTP error status
is an answer. The host rule is F64's own `_host_is_unreachable_publicly`
(bug fix #1's), so a tailnet, private or loopback address is not ready.

Tests: `tests/test_phase409_public_condition.py` (29), and 210's file moved
from eight to nine: `NAMES` gains the ninth, the stand-in sets
`MOTODIAG_PUBLIC_BASE_URL` and replaces `check.public_status` with three
right answers, the passing test reads nine lines, the broken-alone test
holds the other eight, and one more broken case (no public address).
`tests/test_phase409_public_condition.py` and 210's: 62 passed, after bug
fix #1. The certificate case runs a real TLS server on loopback with a
self-signed certificate (`openssl` makes it; skipped if `openssl` cannot).

Mutations: `409_mutate.py`, 9/9 red (`409_mutate.out`).

## 2026-11-27 03:50 UTC — the privacy policy, version 1.2 (Logic item 3)

**The operator's words.** Asked once on a card at 03:00 UTC with the
drafted line; the operator chose "Yes, use it as written" at 03:03 UTC.

`docs/legal/privacy.md`: the Cloudflare item at the end of "The services it
goes to", word for word, and `Version 1.2 — 2026-11-27`.
`scripts/site_build.py legal` and `sitemap` rebuilt
`site/privacy/index.html` and `site/sitemap.xml` (the privacy page's
lastmod). The terms are untouched: `TERMS_VERSION` stays 1.1, so nobody
accepts again. `docs/legal/README.md` says so.

Pins moved, each because the privacy policy's own number moved:
`tests/test_phase293_terms.py` (the privacy header is `Version 1.2 —
2026-11-27`; the built page says 1.2, the terms page 1.1) and
`tests/test_phase334_legal_texts.py` (the services census names the
Cloudflare line). With `tests/test_phase408_site.py`: 114 passed.

## 2026-11-27 04:05 UTC — the app's half (Logic item 4), on `moto-diag-mobile`

Branch `phase-409-app-half` from the app's `main` at `56eb617`, two
commits, pushed (`9837670`):
- **Item 1, the API copy** (`2d4f4de`): `api-schema/openapi.json` read
  from this branch's server (FastAPI 0.136.3), `src/api-types.ts`
  regenerated. A sorted comparison of the old and new snapshots shows one
  change, `GET /v1/shops/{shop_id}` (summary, description, credential
  headers). A fresh dump reorders 1942 lines and writes `999` as `999.0`,
  both noise of the cloud's libraries, so the file keeps the old snapshot's
  order and only that route changes.
- **Item 2, the 100 MB message** (`9837670`): the upload hook turns a 413
  that is not the server's ProblemDetail into `video-too-large-for-connection`;
  the video screen says the video is over 100 MB, to record a shorter clip,
  and that the video is still on the phone. The server's own 413 keeps its
  size message. Two helpers moved to `videoCaptureHelpers.ts` so their tests
  import them without the camera library. 8 new tests: 6 red on the old
  code, 2 controls green. `tsc` clean; Jest **1368 passed**, 123 suites
  (210C's 1360, +8).

## 2026-11-27 04:20 UTC — the operator's blocks (Logic item 5)

`409_blocks/`: eight blocks and a README with the order. Changed from PR
98's six, each for a reason found here:
- **The order:** the settings (help pages off, the host list) go in before
  the tunnel, not after, so nothing is public before it is locked; the
  tunnel block refuses until the settings are in.
- **Step 1 measures** what Step 0 owed: every listener, Tailscale serve and
  Funnel, uvicorn's version, each anonymous route's answer on loopback.
- **Step 2 takes the backup** through the deploy skill's own
  `remote.py backup pre409` before `server-update`, never a `motodiag`
  command on live (F292).
- **The settings block puts the old settings back** when the tailnet name
  stops answering (if it answered before), the help pages still answer, or
  a stranger's host name is still served, not only when loopback fails. A
  wrong host list answers 400 on every name but loopback.
- **The tunnel block** checks the running server refuses a shop's details
  (401) before it installs, checks the download is the `cloudflared`
  package, strips spaces from the pasted token, and checks the help pages
  and the shop route on the public name after.
- **The site check** hashes the page as `curl` writes it: a command
  substitution would drop the page's last newline and never match.

Tested: `bash -n` and `shellcheck -s bash -S warning`, clean on all eight;
the stand-in harness in `409_blocks/standin/`: 27 of 27 and 6 of 6.

`COLLECTED_TEST_FLOOR` 13321 → 13377, by a diff of collected ids against
master `a238aa6`: +58 −2 (named in the floor's comment).

## 2026-11-27 04:55 UTC — the full whole-tree, and a cloud regression run (not of record)

- `wholetree.sh --full` at `1c8c037`: **PASSED — 5518 passed, 37 skipped**
  (1105 s), its record written.
- `regression.sh` at `1c8c037`, in the cloud: `Regression run FAILED (not
  of record): 13284 passed, 4 failed, 51 skipped, 38 errors at 1c8c0371
  (59 min 6 s wall, python -m pytest -n auto --dist load --cov=motodiag,
  exit 1)`. Every failure and error is in the two files a cloud checkout
  cannot run, as Phase 408 found: `tests/test_phase388_fence_boundary.py`
  (bubblewrap is the desktop's) and `tests/test_phase257_orchestrator_guards.py`
  (macOS's `osacompile` and the Subconscious login). Nothing else failed.
  Line coverage 88.72% (the pin 88.00%).
- So **the regression of record is the Mac's**, run by the advisor at the
  branch's head before the close-out commit.

**Long runs (the operator's card, 03:48 UTC): "On GitHub, from a branch I
push".** Recorded in project memory for later threads. This run had
already started in the cloud and was let finish. The repository's GitHub
checks run the quality ratchet and the ROADMAP check, not the suite, so
the Mac's run stays the record.

**F312 is F287.** Phase 408 filed the unbounded `fastapi>=0.110` as F287;
F312 was filed before it was found. F312 is marked closed as its
duplicate, with its added measurement, and the number is not reused.

## 2026-11-27 13:32 UTC — the advisor's review at 7cbab43: SOMETHING IS OFF

The advisor reviewed both pull requests read-only on the Mac. These passed
there: `wholetree.sh --full` (5540 passed, 15 skipped, 992 s), and
`bash -n` under bash 3.2 on all eight blocks. `cases.py` passed 24 of 24,
plus 3 of 3 for block 2 once it had a real Python, and `cases3.py` passed
6 of 6. Real read-only checks also passed: block 2's `gh` query, the
`remote.py` patterns, block 1's DNS query, block 3c's hash method, block
4's settings parse, and uvicorn trusting `X-Forwarded-Proto` from loopback.
It found two defects that show only through Cloudflare. Both were measured
from the Mac against `getmekno.com`, the zone `api.getmekno.com` joins.
They are bug fixes #2 and #3 below. Its smaller items:
- the harness on a Mac, which is bug fix #4;
- the privacy line's approval, which is not yet a K-id in
  `docs/decisions.md`. That is left to the advisor at the close-out;
- the sign-in throttle's leak, filed as F313.

## Bug fix #2 — 2026-11-27 — the launch check's public reader was refused by Cloudflare

- **Issue:** the ninth condition fails on live through Cloudflare. On the
  Mac, the advisor measured the same opener and URL:
  - with urllib's default User-Agent, `Python-urllib/3.14`, Cloudflare
    answered 403 "error code: 1010", a ban on that client signature;
  - with `motodiag-launch-check/409`, it answered 200.
- **Root cause:** `public_status` built its opener with urllib's default
  headers. The tests never met Cloudflare: each either replaces
  `public_status` or uses a loopback server, and neither cares about the
  User-Agent.
- **Fix:** `PUBLIC_USER_AGENT = "motodiag-launch-check/409"`, which
  replaces the opener's default headers.
- **Files:**
  - `src/motodiag/launch/check.py`;
  - `tests/test_phase409_public_condition.py`, one test: the real reader
    against a real TLS server on loopback that records headers. It asserts
    the User-Agent is the reader's own and that no header carries
    `Python-urllib`;
  - `tests/test_phase255B_collected_test_floor.py`, floor 13377 → 13378,
    +1 −0.
- **Verified:**
  - the new test fails on the old code (no such name);
  - it fails with only the header line removed: `assert 'Python-urllib/3.13'
    == 'motodiag-launch-check/409'`;
  - it passes with the fix, and the file passes 30 of 30;
  - `test_phase210_launch_check.py` passes.

  The line removal was a shell edit of `src/`, made to prove the red, and
  put back byte for byte from a copy. It is recorded here because the edit
  guard forbids shell writes there.

The advisor's regression at `7cbab43`, superseded by this fix since it
changes `src/`: `Regression of record: 13328 passed, 0 failed, 49 skipped,
0 errors at 7cbab43 (47 min 43 s wall, python -m pytest -n auto --dist
load --cov=motodiag, exit 0)`. Line coverage 88.74% (pin 88.00%). Its 35
skip lines match 210B's byte for byte. App PR 17 at `9837670`:
- `tsc` and `eslint` exit 0;
- `api-types.ts` regenerates identical;
- Jest passed 1368 of 1368.

The run of record is the advisor's on the new head. Whether to raise the
coverage pin is a close-out item.

**Commit.** `1456f45`

## Bug fix #3 — 2026-11-27 — the outside check failed a correct setup, after ten silent minutes

- **Issue:** block 7, run on the Mac, would end SOMETHING IS OFF after a
  correct setup. The advisor measured two causes against `getmekno.com`:
  - Cloudflare's edge answers port 8080 for every name it proxies:
    `nc -z getmekno.com 8080` succeeded at once, and
    `curl http://getmekno.com:8080/` got a 301 from `Server: cloudflare`;
  - Apple's `nc -w 5` does not limit the connect: ports 22 and 8000 took
    300 s each (4 addresses at about 75 s), while `nc -z -G 5 -w 5` took
    20 s.
- **Root cause:** the block assumed nothing answers 8080 on a proxied name,
  and that `-w` bounds a connect on macOS. The stand-in `nc` always exited
  1, so it agreed with both assumptions.
- **Fix:**
  - the block checks ports 22 and 8000 with `nc -z -G 5 -w 5`;
  - it says 8080 is not checked because Cloudflare's own servers answer
    it;
  - the stand-in `nc` records its arguments and answers only on a port the
    world opens;
  - three new cases, run with the 8080 world set the way Cloudflare
    answers:
    - ALL GOOD with each `nc` call carrying `-G 5` and 8080 never called;
    - port 22 open is OFF;
    - port 8000 open is OFF.
- **Files:** `409_blocks/7_outside_check.txt`, `standin/bin/nc`,
  `standin/cases.py`, `standin/cases.out`, `409_blocks/README.md` (the
  count).
- **Verified:**
  - `cases.py` passes 30 of 30;
  - the block from `1456f45`, before this fix, fails the new 8080 case
    (29 of 30);
  - `bash -n` and `shellcheck -s bash -S warning` are clean on all eight
    bodies;
  - `cases3.py` passes 6 of 6.

  Not measured here: the real Mac `nc` (the cloud's is not Apple's). The
  advisor re-tests block 7 on the Mac.

**Commit.** `19d5230`

## Bug fix #4 — 2026-11-27 — the harness's block-2 stand-in failed on a Mac

- **Issue:** on the Mac, `cases.py` stopped with a `FileNotFoundError`
  after "2 merged" failed with "Failed to locate 'python'" (the advisor).
- **Root cause:** the scratch home's `.venv/bin/python` was a link to
  `/usr/bin/python3`. On a Mac that is Apple's `xcode-select` shim, and it
  refuses to run under the name `python`. On the cloud's Linux it is a
  real interpreter, so the harness passed here.
- **Fix:** the link points at `sys.executable`, the interpreter running
  the harness.
- **Files:** `409_blocks/standin/cases.py`.
- **Verified:** 30 of 30 here. The advisor found all 3 block-2 cases pass
  on the Mac once linked to a real interpreter. Block 2 itself is
  unchanged: the Mac's `.venv/bin/python` is Homebrew's.

Also in the blocks README: nothing else merges to master between the
server's merge and step 2, because `server-update` refuses unless
master is exactly the merge commit it is given (the advisor's note).

**Commit.** `a24b893`

## More than two bugs in this build: the common cause

Four bug fixes in this phase, three of them from one review. Fixes #2–#4
have one cause: **each test stood in for a world it had never measured,
and the stand-in agreed with the assumption it was meant to test.**

| fix | the assumption | the stand-in that agreed |
|---|---|---|
| #2 | any client reaches Cloudflare | a replaced `public_status`, a loopback server |
| #3 | 8080 is closed; `-w` bounds a connect | an `nc` that always exits 1 |
| #4 | `/usr/bin/python3` is a Python | Linux's `/usr/bin/python3` |

This cloud cannot reach Cloudflare or run macOS, so a stand-in here can
only be as true as what was measured somewhere real. What changed:
- each stand-in now models the measured behaviour: a reader test on the
  wire, an `nc` that answers where the world opens a port, and the running
  interpreter;
- each fix has a case the old code fails;
- what is still unmeasured is said in its entry (the Mac's `nc`), and the
  advisor tests it on the real machine before the operator runs it.

Fix #1 (CGNAT) was a different kind: a missing range in a classifier,
which a test found.

## 2026-11-27 15:33 UTC — Step 0's owed measurement: block 1 on the home desktop, ALL GOOD

The operator ran block 1 in the home desktop's Ubuntu window. It is
read-only and changed nothing. What it measured:
- **Services:** `motodiag-api` and `motodiag-payments` are running, and
  the server answers healthy on loopback.
- **Listeners:**
  - `127.0.0.1:8000`, the app server, only on loopback;
  - `100.117.187.83:22` and two tailnet-interface ports, Tailscale's own;
  - `127.0.0.53`, `127.0.0.54:53` and `10.255.255.254:53`, DNS
    resolvers. The last is WSL's own resolver on its internal virtual
    address, not the LAN and not the app.
- **Nothing on the LAN.**
- **Tailscale:** no serve config, and Funnel is off.
- **Libraries:** uvicorn 0.49.0 (0.30 or newer, so it reads the
  right-most `X-Forwarded-For` as Step 0 assumed), fastapi 0.136.3,
  starlette 1.3.1.
- **No login, on loopback today:**

  | path | answer |
  |---|---|
  | `/healthz` | 200 |
  | `/v1/version` | 200 |
  | `/v1/terms` | 200 |
  | `/docs` | 200 |
  | `/openapi.json` | 200 |
  | `/v1/shops/1` | 200 |

  `/docs`, `/openapi.json` and `/v1/shops/1` are what blocks 2 and 4 close
  (the new code, and the help pages off) before block 6 installs the
  tunnel. Block 6 refuses while `/v1/shops/1` is not 401.
- **Not yet in place, as expected before the merge:**
  - the new protections are not in the server's code;
  - no `cloudflared` is installed;
  - the privacy page does not yet name Cloudflare for the app.
- **DNS:** `getmekno.com`'s name servers are Cloudflare's.

So the plan's assumptions hold on the real machine: loopback-only, no
Funnel, uvicorn at 0.30 or newer, and the zone at Cloudflare.

## 2026-11-27 16:10 UTC — the harness types the token only once echo is off

The advisor, at `a24b893`: on the Mac under load, with Apple's
`/usr/bin/python3`, `cases3.py`'s token case failed 2 of 3 runs. `run()`
typed the token as soon as "press Enter" printed, before `read -s` had
turned echo off, so the pty echoed it. Measured over 8 runs each way: 3 of
8 showed the token as `run()` stood, and 0 of 8 when it waited for echo
off. The block is fine, because a person pastes after the prompt.

`standin/run.py` now waits up to 10 s for the terminal's echo to go off,
then types. Documents only (the harness is in the phase folder). Verified:
- `cases3.py` passes 6 of 6, three times;
- `cases.py` passes 30 of 30;
- control: block 6 with `read -r` in place of `read -rs` still fails "the
  token is not shown". The 10 s wait ends and the echoed token is caught.

Not a bug fix in the register: it is the harness's timing, not a defect
in what ships. It is recorded here because the advisor measured it.

## 2026-11-27 16:15 UTC — the regression of record, and the close-out

On the advisor's Mac, on a clean clone at `a24b893` with the app clone at
`9837670` beside it. `wholetree.sh --full` first passed: 5547 passed, 8
skipped, 1240 s, record for `a24b89318805`. Then `regression.sh`, exactly
as printed:

Regression of record: 13329 passed, 0 failed, 49 skipped, 0 errors at `a24b893` (49 min 10 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase390_space.py:327: bubblewrap is the desktop's
Line coverage of record: 88.75% at `a24b893` (the pin is 88.00%)

- 13329 + 49 = 13378, the floor this phase set.
- The advisor's other checks: `test_the_reader_names_itself_not_python_urllib`
  ran and passed, and so did `test_phase209_packaging`, gate 11 and both
  409 files.
- The merge's tree is `a24b893`'s plus master's K150 line in
  `docs/decisions.md` (`b344104`). The advisor made that merge locally, and
  the decisions, ledger and finding tests on it passed 123.
- Every commit after `a24b893` changes documents only: block 1's record,
  the harness timing above, and this close-out. So this line stays of
  record.
- The coverage pin stays 88.00% for now. It lives in `tests/`, so raising
  it means another regression, and that goes in a later commit with its
  own run (the advisor's advice).
- The K-id for the operator's yes to the privacy line is the advisor's to
  record after the merge.

No refute pass ran.

Close-out:
- `409_implementation.md` is at v1.1;
- the documents moved to `completed/`;
- the ROADMAP row is ✅;
- the handoff `docs/handoffs/2026-11-27_409_closed.md` has every live step's
  block inline.

Issue 104 is closed by this session after the merge, as the brief asks;
the live steps then follow from the handoff.

