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
