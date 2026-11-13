# Phase 372 — phase log: Payment API routes and the app's payment screens

**Status:** Complete

Built by the Chief Engineer in the fleet's fence, on `phase-372-payment-api-routes-and-the-app`; the plan is `372_implementation.md` v1.0, approved by the Executive Officer on issue #59.

## 2026-11-12: How the record answers Step 0's stops

The Science Officer's Step 0 (`372_step0.md`) listed five stops, (a) to (e). Four are answered by the record; (d) stays a fork.

- **(a) Stripe's live account.** It exists and is in use: live payments went on at 21:10 EST on 2026-11-11 (`docs/handoffs/2026-11-10_402_closed.md`, "Live payments went on"). K66 did not cover this phase, so it did not start early; it starts with the account in use.
- **(b) Which issue holds the phase.** Issue #59, the mission issue this phase was opened from. K76 names it ("issue #59 (372) keeps its hold"). K66's issue #54 is Phase 371's (K65, K70 and K73 all name #54 for 371), so the two do not conflict. The hold on #59 is lifted when the operator marks the plan approved; the Executive Officer's approval of v1.0 is on #59.
- **(c) The sequencing.** Every row before #14 in "Next, in order" is ✅, which is why `plan_order.py` picked 372; the 2026-10-22 to 2026-10-25 entry's first-shop rows 303 and 348 have closed.
- **(d) The app half.** A real fork, left to the operator: (A) one phase, both repositories; (B) the routes now and the screens as a letter follow-on. The plan's recommendation is (A). The operator picks at the Gate 11 stop at the latest.
- **(e) The live key.** No step of the build or the tests reads it: the tests use the test-only key in `tests/support/stripe_fixtures.py` and Stripe's recorded answers.

The decisions, character for character from `docs/decisions.md`:

- K48 (2026-10-27): "1: The plan of record stays the single source; add a short "Next, in order" list at its top that the fleet reads exactly; it changes only by a dated entry with a K-id, written on my word."
- K66 (2026-11-05): "yes, the fleet can start before the live account"
- K76 (2026-11-09): "402: start it now, the fleet builds it."

## 2026-11-12: Items 1 and 2 built (the routes, the error map, the document)

- **`src/motodiag/api/routes/payments.py`**, new: the five routes, each on `Depends(require_tier("shop"))` (which wraps `get_current_user`) and `require_shop_access` imported from `shop_mgmt.py`: the account read for any active member, connect on `manage_billing`, the two starts and the payments list on `manage_shop`. Registered in `app.py` beside `shop_mgmt_router`.
- **Decided here:** the responses are pydantic models, so the document carries the fields by name for the app's generated types; an invoice not at the shop raises `InvoiceNotFoundError`, whose row in the chain already answers 404 `invoice-not-found`, so the 404 is a problem document like its neighbours; the account read's "no account" is an `HTTPException(404)` with the plan's sentence, before any Stripe call; connect sends `contact_email or ""`, so a missing email is `connect_shop`'s own refusal (409). Besides `_invoice_shop_id`, three small private helpers: `_require_invoice_at_shop` (the check the three invoice routes share), `_account` and `_started_fields` (the answer's fields). None writes.
- **`src/motodiag/api/errors.py`**: four rows in `_exc_class_chain`, `ConnectError` 409 `payment-refused`, `StripeNotConfigured` and `LiveKeyRefused` 503 `payments-not-configured`, `StripeUnavailable` 503 `stripe-unavailable`. `StripeLibraryMissing` is a `StripeNotConfigured` and answers through its row.
- **`src/motodiag/api/openapi.py`**: `payments` in `TAG_CATALOG` and in `_ALWAYS_TIER_GATED_TAGS`. Each route declares 403 as `{"$ref": "#/components/responses/Forbidden"}` and 409 and 503 with the `ProblemDetail` schema. FastAPI adds a `description` beside the `$ref`, which OpenAPI 3.1 allows on a reference.
- `create_app().openapi()`: each of the five operations carries `security` and 401, 402, 403, 404, 409 and 503.

## 2026-11-12: Item 4, the tests

- `tests/test_phase372_payment_routes.py`, 26 tests, all green on the first run. Only the writer, who logs in for the audit test, gets a password hash; the other callers use API keys (a hash per user made the file 76 s).
- `tests/test_phase372_wiring.py`, 18 tests, read with `code_of`.
- **Against master's code.** A scratch worktree at `62c9f3c` (master's code) with the new route module and the two test files copied in, so only `app.py`, `errors.py` and `openapi.py` were master's, run with that worktree's `src/` on `PYTHONPATH`: route tests 1 passed / 25 failed, wiring 10 passed / 8 failed, `tests/test_phase273_connect.py` 12 passed / 0 failed, `tests/test_phase273_invoice_payments.py` 35 passed / 0 failed. The ten wiring tests that passed read the route module's own text, which the control kept. The one route test that passed was "an invoice that does not exist is 404": a path nobody serves is a 404 too, so it could not fail. It now also requires the problem type `invoice-not-found`, and re-run on master's code it is red (1 failed); on the branch its class is 4 passed. So all 26 route tests are red on master's code.
- **Mutations.** `372_mutate.py`, the plan's thirteen, on 348's harness; its output is `372_mutate.out`: **13/13 red**, every file restored. The route mutations run the route tests alone, so each is caught by an answer, not by the wiring file's reading of the text.
- **The OpenAPI suites unchanged:** `tests/test_phase372_wiring.py`, `test_phase183_openapi.py`, `test_phase184_gate9.py`, `test_phase204_gate10.py` and `test_phase205_gate11.py` together: 91 passed, 1 skipped, 2 failed, the two failures Gate 11's `TestContractSnapshot` (below).
- **`COLLECTED_TEST_FLOOR`** 12576 → 12620, by a diff of collected ids against `62c9f3c`, each side with its own `src/`: +44 −0 (26 and 18).
- The quality counts (`scripts/code_quality.py counts`) equal their pins: ruff 1108, mypy 202, complex 25, big 5, helpers 19, swallowed 22. The test file's import order was put right for ruff before the commit.
- `wholetree.sh`: exit 0, 2634 passed, 10 skipped. Commit `2106fc7`.

## 2026-11-12: Item 5, the guide; item 6, the app's prompt

- `docs/guide/api.md`: the `payments` row (five operations) and the sentence on `manage_billing` and `manage_shop` under "Tiers and limits". `docs/guide/payments.md`: "From the app".
- **`README.md`'s route count** said "Serves 80 routes", from Phase 208 (`e79ad0f`) and already wrong: master's code serves 112 operations, by `create_app().openapi()`. The plan says the count "moves with it"; moving 80 by five would print another wrong number, so it now says 117, the measured count on this branch.
- `docs/prompts/372_the_apps_payment_screens.txt`, for the session in `moto-diag-mobile` under option A; `docs/prompts/README.md` lists it in a new section, "Written for a session in the mobile repository", since its table lists only the prompts moved in on 2026-09-27.

## 2026-11-12: Gate 11 is red, as the plan says

`tests/test_phase205_gate11.py`, `TestContractSnapshot`:

- `test_every_live_path_is_in_the_committed_snapshot`: missing the five operations of this phase, and nothing else.
- `test_every_live_schema_is_in_the_committed_snapshot`: missing `CheckoutStarted`, `ConnectAnswer`, `ConnectRequest`, `InvoicePayment`, `InvoicePayments`, `PaymentAccount` and `TerminalStarted`, this phase's seven models, and nothing else.

The phone app's copy at `../moto-diag-mobile` is read-only inside the fence and stands at `04be61c` on `main` (348's refresh). No gate is loosened. As for 303 and 348, the Engineer commits what is built and stops with kind `test-cannot-be-green`; the operator refreshes the app's snapshot on the mobile branch `phase-372-payment-api-routes-and-the-app` and picks between the plan's options (A) and (B). The regression of record and the close-out wait for that.

## 2026-11-12: The operator's answers to the Chief Engineer's stop

Written by the advisor session on the Mac, from the operator's answer and their desktop block's output. The ranks read no comment of the operator's on issue #59 (F223), so the answer is here and in `docs/decisions.md` (K81, merged into this branch at `024b4e8`).

- **The fork, (d): (B).** K81, 2026-11-12, the operator's words, character for character:

  > B, give me the desktop block

  So the routes ship in this phase, and the phone app's three screens become a letter follow-on, 372B, built later by a session in the mobile repository. As the plan's "A real fork" says for (B), items 6 and 7 move there, and the handoff's step 2 shrinks to the snapshot push and the types.
- **Gate 11, the phone app's snapshot: refreshed.** The operator's desktop block printed ALL GOOD at 22:22 EST. It did three things.
  - **It pushed this branch's commits through `cbfa766` to GitHub by hand,** as for 348. The fleet's own push check (G1 to G5) passed first; G6 could not pass while Gate 11 was red.
  - **It wrote the app's snapshot, `api-schema/openapi.json`, from `cbfa766`,** by `create_app().openapi()`, as for 303 and 348.
    - The commit is moto-diag-mobile `993fadcdde68`, "API schema: refresh for backend Phase 372 (payment routes)", on that repository's branch `phase-372-payment-api-routes-and-the-app`.
    - The branch starts from `main` at `0773f91` and is pushed. `main` is not touched.
  - **It left the desktop's `~/Projects/moto-diag-mobile` on that branch,** so the fence's read-only copy carries the five operations and the seven models.
- **The advisor checked it on the Mac,** with this branch at `cbfa766` and the mobile branch at `993fadc` side by side.
  - The snapshot is byte for byte what `create_app().openapi()` gives on `cbfa766`.
  - 120 passed: `tests/test_phase205_gate11.py`, the two `test_phase372_*` files, and the OpenAPI suites 183, 184 and 204.
  - 287 passed: gates 12, 13 and 14.
- **What follows is unchanged.**
  - The standing test is not changed.
  - Next come `wholetree.sh --full`, the regression of record, and the close-out. There is no migration, so there is no database step.
  - Regenerating `src/api-types.ts` and merging the mobile branch are the handoff's steps for after this phase merges.

## 2026-11-12: Carrying on after the operator's answers

- **Gate 11 in the fence.** The fence's read-only `../moto-diag-mobile` stands on `phase-372-payment-api-routes-and-the-app` at `993fadc`. `tests/test_phase205_gate11.py`: 21 passed.
- **Option (B) applied.** Row 372B is added to the ROADMAP, 🔲, for the three screens; it is the next free letter after 372 and names the prompt it starts from. The prompt `docs/prompts/372_the_apps_payment_screens.txt` is kept as written: it already says it applies only under option (A) and tells a session not told that to stop and ask, so 372B's session is not misled by it; 372B's own prompt is written when that phase starts. Item 7 is not built here.

## 2026-11-13: The operator's answers to the Chief Engineer's stop (second stop, guard-blocked-twice)

Written by the advisor session on the Mac. The ranks read no comment of the operator's on issue #59 (F223), so the answer is here.

- **The stop.**
  - The second session was run `20261112_225609_engineer_372`, from `ef8bacc`. It ended at 23:56 EST on 2026-11-12 with kind `guard-blocked-twice`.
  - The edit guard twice refused the redirect `> $b.inner`: "the edit guard cannot tell where the redirect `>` `$b.inner` writes (a variable, substitution, glob or unknown directory), and blocks what it cannot resolve. Use a literal path."
  - Nothing that session made was pushed: this branch stayed at `ef8bacc`. The next session starts again from the answers above.
- **The guard is right, and it stays as it is** (CLAUDE.md rule 6).
  - It refuses any write whose target it cannot read, wherever the write would land, not only under `src/` and `tests/`. A redirect, `tee`, `cp` or `mv` to `$var…`, `$(…)` or a glob is refused.
  - The brief's rule 3 says less than that. F275 records the gap, for a fleet phase.
- **So, in every session from here:**
  - Write each scratch file to a literal path in a literal directory, for example `> /fleet/run/base.inner` and `> /fleet/run/head.inner`, never `> $b.inner` in a loop; or use the Write tool.
  - Do not retry a refused command in the same form.
- **The operator's words,** 2026-11-13, asking for the restart: "Then give me the block that gets the build going again."
- **A guard block while this entry was written.** The advisor ran `git commit` and `git push` in one command. The push guard refused it, because it judges a push before the commit exists. Both were run again as separate commands, and nothing was loosened.
- **Unchanged:** K81's (B) above, and the phone app's snapshot at moto-diag-mobile `993fadc`. Next come `wholetree.sh --full`, the regression of record, and the close-out.

## 2026-11-13: The stopped session's commit is carried; its close-out is done again

Written by the advisor session on the Mac, after the operator copied the stopped session's work from the home desktop to GitHub.

- **What the stopped session made.** Run `20261112_225609_engineer_372` pushed nothing, as the entry above says. In its own folder it had made one commit, `4e46bcf`, at 23:01 EST, and after it most of a close-out, never committed.
- **Carried: `4e46bcf`,** merged into this branch as `df88d09`. Its entry is the 2026-11-12 one above, and row 372B came with it.
- **Not carried: the close-out.** It is kept as it was left, as `1b59a8d` on the branch `carry-372-stopped-build`: a record of what that session wrote, not a draft for the next one. It is not carried because:
  - its whole-tree record and regression of record are of `4e46bcf`, not of the tree this branch closes on;
  - it is dated 2026-11-12, in row 372's CLOSED date and in the handoff's name, and the phase closes later;
  - it never reached its end: its last command was the refused `$b.inner` write.
- **For the next session: the close-out, from this branch as it stands.** `wholetree.sh --full`, the regression of record, v1.1, row 372 and the handoff, dated the day the phase closes.
  - For comparison only, and not of record here, the stopped session measured at `4e46bcf`: `wholetree.sh --full` 5103 passed, 36 skipped (981 s wall); the regression 12515 passed, 0 failed, 105 skipped (35 min 25 s wall, inside the fence); line coverage 88.20%.
  - Change a file's text with the Edit and Write tools, never with a script or `sed -i`. That session's Python edit of v1.1 through a variable path was refused, and so was its `sed -i` on this log; the same edits then went through with the Edit tool.
  - Send shell output only to a literal path, as the entry above says.
- **The operator's words,** 2026-11-13: "Please do your Mac step now (join 4e46bcf to the 372 branch, whole-tree check, the note for the builder) and then give me the restart block."
- **A guard block** (CLAUDE.md rule 6). At 07:12 EST on 2026-11-13, after the entry above was pushed, the edit guard refused one of the advisor's commands: a Python script body writing to a path the guard could not resolve, while the advisor made a stand-in to test the operator's read-only step on the home desktop. It did not run, and nothing was loosened.

## 2026-11-13: The whole-tree run and the regression of record

Run by the third Engineer session, in the fence, from this branch at `d10da9a`. No file under `src/` or `tests/` changed after `4e46bcf` (`git diff 4e46bcf d10da9a -- src tests` is empty).

- `wholetree.sh --full` on its own, on a clean tree: exit 0. It printed "wholetree full: PASSED — 5103 passed, 36 skipped, 33 warnings in 985.25s (0:16:25) (987.8 s wall)" and wrote its record for commit `d10da9a1f6d9`.
- `regression.sh`, then, on the same clean tree: exit 0. Its lines, as printed:


Regression of record: 12515 passed, 0 failed, 105 skipped, 0 errors at `d10da9a` (36 min 53 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
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
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
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
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
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
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: inside the fleet's fence: its boundary is proven from the host, not from inside
Line coverage of record: 88.20% at `d10da9a` (the pin is 87.50%): 0.70 points above it; raise COVERAGE_PERCENT to lock it in

The 105 skips are the fence's: each is named above, by file and reason. `COVERAGE_PERCENT` is not raised: the plan keeps the ratchet's pins as they are. Only documents change after `d10da9a`.

## 2026-11-13: The close-out

- v1.1 written: every section brought to what was built, Deviations (the fork answered B, the prompt kept, the handoff's app steps, the server block's commit, `README.md`'s count, the build's own decisions, the Gate 11 stop, the build over three sessions) and Results. No bug fixes.
- Row 372 closed ✅, dated today, with the regression line above; row 372B stays 🔲. The handoff is `docs/handoffs/2026-11-13_372_closed.md`. The root `phase_log.md` points at the completed documents.
- Text was changed with the Edit and Write tools; the regression's lines were copied by appending the printed output to this file's literal path. No guard blocked a command in this session.
