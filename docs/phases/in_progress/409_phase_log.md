# Phase 409 — phase log

**Status:** In progress. Started 2026-11-27 by the builder session K149
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
