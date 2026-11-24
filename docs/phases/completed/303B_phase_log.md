# Phase 303B — phase log

**Status:** Complete

## 2026-11-20 — Step 0 and v1.0

The operator, 2026-11-20, evening (K99): "yes add the staff sign-in screen
to the list too", then "yes write the sign-in screen instructions" and
"yes write the sign-in screen plan".

Master `45c26d9` holds K99, row 303B and its place in 'Next, in order'
(#22, before 334B, 372B and 210); `2fb8f90` holds the prompt,
`docs/prompts/303B_the_apps_staff_sign_in_screen.txt`, written against
both repositories' code.

Step 0 (`303B_step0.md`) read the app at `2267ea5` and this repository at
`2fb8f90`: nothing in the app calls the login, me or logout routes; the
Keychain slot, the client and the push token's resync and deregister are
there to build on; "session" already means a diagnostic session in the
app, so the new credential is called a sign-in. Classification: extension.

v1.0 (`303B_implementation.md`): the token in the existing slot, the
sign-in box, the auth block's three views, signing out with logout only for
a sign-in, an ended sign-in noticed once by the client, and their tests.
Row 303B is marked 🚧 in the same commit.

**Who builds and who records.** The build is a session in
`moto-diag-mobile` on `phase-303B-the-apps-staff-sign-in-screen`; it writes
nothing in this repository. The advisor keeps this log, the row and the
close-out here, from the app's pull request.

**A guard block, recorded as rule 6 asks.** The first try put these three
files on master through a local merge. The push guard refused the push to
master before anything was sent: "closeout is not complete for phase 303B;
push blocked", naming A1, A2, A3, A5 and A7. A phase's files reach master
only at its close-out. So they live on this repository's branch of the same
name, `phase-303B-the-apps-staff-sign-in-screen`, until then; the unpushed
merge was dropped, and the app's session reads the plan from that branch on
GitHub (the prompt says how). The guard is unchanged.

## 2026-11-22 — the build, the review, the merge and the phone check

**The build.** The operator, 2026-11-22: "303B is being built by a session
of mine on moto-diag-mobile, starting now. Do not build it." It built from
v1.0 on this repository's branch (`833fb20`) and opened moto-diag-mobile's
pull request #11: three commits, `e4f1bb0`, `ff1d53f` and `b7ad88f`. Its
description is the build's record, and v1.1 is written from it: the
decisions the plan left to the build, two small additions, and one wording
line left alone (v1.1, Deviations).

**The advisor's review,** at the operator's "Read it against the 303B plan
and tell me: safe to merge, yes or no":
- read against v1.0, item by item, and against the server's routes: the
  `mds_` and `mdk_` prefixes (`src/motodiag/auth/api_key_repo.py`), the
  login request and its 64-character `client` (`src/motodiag/api/routes/auth.py`),
  the three problem types (`src/motodiag/api/errors.py`), the user block
  and `credential.kind`;
- tsc, eslint and jest run again on the Mac, in a scratchpad clone at
  `b7ad88f` with a copy-on-write copy of the app checkout's installed
  packages (the lockfiles are identical): tsc exit 0; eslint exit 0, 0
  errors and 143 warnings; jest 104 suites, 1248 tests passed. No line of
  an existing test was removed;
- "Safe to merge: yes", with one tap added to the phone check: "Use an API
  key instead" from inside the sign-in box, which closes one pop-up and
  opens another at once.

**The merge.** The operator merged #11 as `2f6739c` (moto-diag-mobile
`main`) at 16:47 UTC.

**The phone check,** run by the operator on a real iPhone. The operator:
"wrong password refused, sign-in as [the operator's own login] works,
sign-out clean, "Use an API key instead" opens the key box and cancel
returns to Home." All four passed.

**A change on live, the operator's own.** Before the phone check, the
operator reset the password of their own login on live, with `motodiag user
set-password` on the home desktop, after a backup in the backup folder,
because the password given to that login during the app's earlier testing
was never recorded. One existing row on live changed: that login's password
hash. The login's name is left out of this record.

## 2026-11-22 — the close-out

The operator: "Write 303B's moto-diag record (plan v1.1, log, row closed,
handoff) and push to master."

Master (`3bfb2ad`) was merged into this branch as `2225ec3`, with no
conflict. The whole-tree command, run on the merge before it was committed,
failed one test:
`tests/test_phase408_site.py::test_each_lastmod_is_the_date_its_page_last_changed`.
`last_changed` in `scripts/site_build.py` dates a page in `site/` as today
while the page is uncommitted, and the merge brought 408's `site/` into the
branch. On the committed merge the test passed. `wholetree.sh --full` then
ran on `2225ec3`: 5461 passed, 1 skipped, exit 0 (12 min 51 s).

Regression of record: 13086 passed, 0 failed, 49 skipped, 0 errors at `2225ec3` (39 min 20 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
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
Line coverage of record: 88.45% at `2225ec3` (the pin is 88.00%)

This repository's code did not change in this phase: the regression of
record is master's code at the close-out, with this phase's documents.

After the run, the operator merged pull request 87 (293's row, in progress) as `5554f95`, and said: "Pull master before your 303B push." Master was merged in again as `ad2dd8e`: it brings only row 293's line in `docs/ROADMAP.md`, with no conflict, and the whole-tree command passed on it before the commit (2966 passed, 1 skipped).

The close-out: v1.1; row 303B ✅; `implementation.md` 0.13.143 and its
history row; the handoff `docs/handoffs/2026-11-22_303B_closed.md`; the
three phase files moved to `completed/`.
