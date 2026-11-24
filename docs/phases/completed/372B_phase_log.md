# Phase 372B — phase log

**Status:** Complete

## 2026-11-22 — Step 0 and v1.0

The operator, 2026-11-22 (K128): "im taking all your recommendations", one
of which was that 372B gets a fresh prompt from the advisor after 334B.
Then, after 334B closed: "give me the prompt from main to continue through
it", and "i mean continue through whats to be accomplished right now. we
are running a strict schedule here".

Step 0 (`372B_step0.md`) read the app at `58142e4` and this repository at
`618bc73`:
- the app's types name all seven routes, and nothing in the app calls
  them yet;
- the stacks, the settings screen, the shop-access errors, the share sheet
  and the tier hook are there to build on.
Classification: extension.

v1.0 (`372B_implementation.md`) is 372's item 7, re-read against today's
code:
- one hook for the payment routes;
- card payments setup;
- an invoice's payment at the reader or by pay-link, with its outcome;
- the plan screen;
- and their tests.
Row 372B is marked 🚧 in the same commit.

**Who builds and who records.** As for 303B and 334B: the operator's own
session in `moto-diag-mobile` on `phase-372B-the-apps-payment-screens`
opens its pull request there only and writes nothing here. The advisor
keeps this log, the row and the close-out. These files stay on this
repository's branch of the same name until the close-out; row 372B is
marked 🚧 on master in its own commit.

## 2026-11-22 — a guard block

At 18:43 local, this branch's first push was sent in the same command as
the whole-tree run before it:
`wholetree.sh > …; grep -q "exit 0$" … && git push -u origin phase-372B-the-apps-payment-screens > …/push_372B.out 2>&1`.
The push guard judges a push before any of the command runs, and refused
it: "whole-tree check: push blocked. the guard cannot tell which commits
this push sends (--all, --mirror, --tags, or a ref that does not resolve).
Push a named branch." The push was sent again as its own command at 18:48
and was accepted on the whole-tree record. The guard was not changed.

## 2026-11-22 — the review

The operator: "372B is built. Mobile PR 13, branch
phase-372B-the-apps-payment-screens, last commit cb0786d. … Review it as
you did PR 12 and tell me safe to merge or not. Do not merge, do not build
anything."

The advisor read the pull request in a scratchpad clone of the app at
`cb0786d`. The lockfile is unchanged, so the app checkout's `node_modules`
was copied in.
- `npx tsc --noEmit` exit 0; `npx eslint .` exit 0, 0 errors and 150
  warnings; `npx jest --ci` 113 suites, 1308 passed. The four new test
  files alone: 37 passed.
- `git diff --numstat origin/main...HEAD -- __tests__`: four files added,
  no line of a test removed. No package file and no `api-types.ts` in the
  diff, and no card number or key in the new tests.
- Against this repository's code:
  - `SUBSCRIPTION_TIERS` is `("individual", "shop", "company")`
    (`src/motodiag/auth/deps.py`), the app's three plans;
  - the portal answers `SubscriptionRequiredError` when there is no plan
    (`src/motodiag/api/routes/billing.py`), the app's "Choose a plan
    first.";
  - the account route answers 404 "this shop has no Stripe account yet",
    and connect needs `manage_billing` and, the first time,
    `contact_email` (`src/motodiag/api/routes/payments.py`,
    `src/motodiag/payments/connect.py`);
  - `invoice_payments.status` is one of `started`, `failed` and
    `succeeded` (`src/motodiag/core/migrations.py`), so the polling's stop
    on anything but `started` is a stop on a final state;
  - the invoice list returns each invoice's columns, with `total_cents`
    added (`src/motodiag/shop/invoicing.py`);
  - the terms refusal is caught in the app's shared client, before any of
    the new screens.

The verdict to the operator: safe to merge, with two notes. GitHub shows
the merge as blocked only because of `main`'s rule that the operator
merges. The two new buttons show for every member of the shop, and the
server refuses connect to one without billing rights, with its sentence.

## 2026-11-22 — the close-out

The operator: "PR 13 merged as f87d04b. Write the 372B record and give me
the sha when it is on master. Do not build anything."

Master (`6ec0298`) was merged into this branch as `0bd368b`, with no
conflict. Row 372B had been changed the same way on both sides, so the
merge brought only K131's row in `docs/decisions.md`, the prompt and its
README row. The whole-tree command passed on it before the commit (2966
passed, 1 skipped).
`wholetree.sh --full` then ran on `0bd368b`: 5461 passed, 1 skipped, exit 0 (12 min 10 s).

Regression of record: 13087 passed, 0 failed, 49 skipped, 0 errors at `0bd368b` (44 min 7 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
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
Line coverage of record: 88.48% at `0bd368b` (the pin is 88.00%)

This repository's code did not change in this phase: the regression of
record is master's code at the close-out, with this phase's documents. It
ran on battery.

The close-out: v1.1; row 372B ✅; `implementation.md` 0.13.145 and its
history row; the handoff `docs/handoffs/2026-11-22_372B_closed.md`; the
three phase files moved to `completed/`.

The whole-tree command's first run on the staged close-out failed one
test, outside this phase:
`tests/test_phase403_granted_round.py::test_a_grant_in_any_other_form_grants_nothing[another form]`.
That fleet test's stand-in mirror failed to clone ("the mirror could not
be updated: fatal: failed to copy file to …", git's message cut at 200
characters by the dispatcher). Its origin is a fixture tree in pytest's
temporary folder, which no document here reaches. The test file then
passed alone 5 times of 5, and with `tests/test_phase390_resume.py` under
`-n 4` 3 times of 3. Filed as F295. The whole-tree command was then run
again before the commit.
