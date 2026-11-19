# Phase 334 — phase log: Terms of Service + liability framework, the terms from templates (K84)

**Status:** In progress — migration 091 committed and the regression of record run; waiting for the operator's live apply before the close-out

**Started 2026-11-19** by the Chief Engineer, in a fresh clone of
`phase-334-terms-of-service-liability-framework` at `bc78448`, inside the
fleet's sandbox. The plan is `334_implementation.md` v1.0, approved by the
Executive Officer on issue #72. The plan has "## The database step", so the
build ends after the regression of record with the `deploy` outcome; the
close-out follows the operator's live apply.

## 2026-11-19 — Step 0, re-measured

**The prompt's search.**
`git grep -n -i -E "disclaim|terms of service|privacy policy|own risk" -- src`:
**5** lines, as the plan says, none shown to a user: `cli/main.py:155` (a
developer's note), `core/migrations.py:6243` (migration text) and three
knowledge rows (`known_issues_kawasaki_electrical.json:110`,
`known_issues_suzuki_electrical.json:78`, `known_issues_zero.json:222`).
The same search in `../moto-diag-mobile` at `9045c32`, `-- src`: **0**. Over
the whole mobile repository it finds 6, all in its `docs/` (F80 and F14 in
its FOLLOWUPS, and `app-store-listing.md`'s "privacy policy URL ... does not
exist yet"); none in the app.

**The acceptance vocabulary** (Step 0 report's terms: `terms_version`,
`tos_version`, `accepted_version`, `accepted_at`, `accept_terms`,
`terms_accepted`, `require_terms`): no hit before this phase. The
classification stands: extension.

**The three dependency counts**, in `src/motodiag/api/routes/`:
- `Depends(get_current_user)`: **86** across **14** files (auth 5, billing 3,
  diagnostics 1, parts 12, photos 3, push 2, reports 3, sessions 10, share 3,
  shop_mgmt 26, time_tracking 5, transcripts 3, vehicles 6, videos 4).
- `Depends(require_api_key)`: **8**, all in `kb.py`.
- `Depends(get_api_key)`: **0**.
- `require_tier(` reaches `get_current_user`: payments.py 182, 215, 259,
  280, 304; audit.py 49; and the shop routes (auth, parts, photos, reports,
  shop_mgmt, time_tracking, transcripts, videos).
All three agree with the plan. The live WebSocket route
(`api/routes/live.py`) resolves its credential itself and is the one
credentialed route the first switch does not hold: named here for 334B.

**The services census.** Command, as the plan names it:
`git grep -n -i -E 'openai|whisper|anthropic|sentry|backblaze|s3' -- src`:
**267** lines in 47 files; most hits of `s3` are substrings (`ss3`, ids,
knowledge text). Each traced to where data leaves:

| service | where in the code | what leaves |
|---|---|---|
| Stripe | `billing/providers.py`, `payments/` | subscriber's email and plan; shop card payments |
| Anthropic | `engine/client.py`, `shop/ai_client.py`, `intake/vehicle_identifier.py`, `media/vision_analysis_pipeline.py`, `media/transcript_pipeline.py` | diagnosis text, photos, video frames, transcript text |
| OpenAI (Whisper) | `media/whisper_client.py`, `media/transcript_pipeline.py`; `core/config.py` `openai_api_key`, `whisper_model` | voice-note audio |
| Sentry | `telemetry/` | crash reports, one request in ten timed |
| Backblaze (S3 API) | `backup/` (`MOTODIAG_BACKUP_S3_*`); `docs/guide/backups.md` names Backblaze | the encrypted nightly copy |

The census grep does not reach two more destinations, found by a search of
the code's outbound addresses
(`git grep -n -i -E "https?://" -- 'src/motodiag/*.py'`, then
`git grep -n -i -E "nhtsa.gov|push.apple|fcm|firebase|googleapis|twilio|sendgrid|mailgun|smtp" -- 'src/*.py'`):
- **Apple** push notifications (`push/sender.py`, `api.push.apple.com`): the
  device token and the notification's text;
- **NHTSA** (`advanced/nhtsa.py`): a VIN, or make, model and year, for
  recall and VIN lookups.
The ECB rate fetch sends no user data. No Firebase, SMS or email service.
The privacy policy names all seven.

**The template.** The fence could not reach github.com
(`curl -I https://raw.githubusercontent.com/basecamp/policies/master/README.md`:
`CONNECT tunnel failed, response 403`). As the plan says for that case, the
texts are written from Basecamp's policies as the Engineer knows them, the
attribution names the source and CC BY 4.0, and the handoff asks the
operator to open the address once and confirm the licence line.
`docs/legal/README.md` records the name, the address, the licence and the
date read.

**The liability cap's period.** Basecamp's terms, as the Engineer knows
them, disclaim indirect and consequential damages in their "Liability"
section and name no cap with a period. The plan makes that a threshold for
the operator (its "Rule-1 stops anticipated"). The cap clause in
`docs/legal/terms.md` therefore reads "capped at what the shop paid Mekno",
with no period, until the operator names one.

## 2026-11-19 — the build

- `src/motodiag/auth/terms_acceptance.py`: `TERMS_VERSION = "1.0"`,
  `TERMS_DATE = "2026-11-19"`, `TERMS_EXEMPT_PATHS` (the four routes),
  `record_acceptance`, `has_accepted`, `get_acceptance`, the two errors and
  the refusal's message. `record_acceptance` inserts with
  `ON CONFLICT (user_id, version) DO NOTHING` and reads the row back, so a
  second acceptance returns the first row and no `except` is needed.
- Migration 091 (`terms_acceptances` and the unique
  `idx_terms_acceptances_user_version`), `SCHEMA_VERSION` 91, and
  `334_deploy_scope.json`.
- `src/motodiag/api/routes/terms.py`: `GET /v1/terms` (through
  `get_api_key`) and `POST /v1/terms/accept` (through `get_current_user`),
  mounted beside `auth_router`. Anonymous, `accepted` and `accepted_at` are
  null; signed in, `accepted` is true or false.
- The check in `require_api_key`, which gains `request` and `db_path`;
  `get_current_user` unchanged. No query while the switch is off.
- `checkout_session_params(...)` in `billing/providers.py`, called by
  `StripeBillingProvider.create_checkout_session`;
  `consent_collection.terms_of_service = "required"` only with the switch on.
- Four settings (`terms_url`, `privacy_url`, `terms_required`,
  `checkout_terms_consent`), after the payments feed's block.
- Two rows in the error table; a `terms` entry in `TAG_CATALOG`.
- `docs/legal/` (README, terms, privacy); the guide notes in `api.md` and
  `payments.md`; the launch checklist's dated note; row 334B and
  `docs/prompts/334B_the_apps_terms_screen.txt` (listed in
  `docs/prompts/README.md`); README's route count 117 → 119.

**Tests.** Four new files, 70 tests, green on this branch:
`test_phase334_legal_texts.py` (33), `test_phase334_terms_routes.py` (24),
`test_phase334_migration_091.py` (7), `test_phase334_checkout_consent.py`
(6). `COLLECTED_TEST_FLOOR` 12779 → 12850 by a diff of collected ids
against `bc78448` (12780): +70 −0.

**Pins grepped before changing.** No test pins the error table's size, the
guide's route count, the settings' fields or `require_api_key`'s
signature; `test_phase176_auth_billing.py` line 386 runs unchanged. The
route tags are pinned against `TAG_CATALOG` (`test_phase183_openapi.py`
line 118), so the `terms` tag is catalogued.

## 2026-11-19 — the whole-tree runs, and the migration held back

- `wholetree.sh` (fast), on its own, before staging: exit 0, "wholetree
  fast: PASSED — 2750 passed, 10 skipped, 33 warnings in 151.70s (0:02:31)
  (152.8 s wall)".
- The OpenAPI, auth, floor and docs suites with Gate 11: 240 passed, 2
  failed, the two Gate 11's `TestContractSnapshot` (the two new paths and
  the schemas `AcceptRequest`, `Acceptance`, `TermsInfo`), as the plan
  says.
- `wholetree.sh --full` on the staged build, on its own: exit 1, "wholetree
  full: FAILED — 4 failed, 5215 passed, 36 skipped, 33 warnings in 1020.06s
  (0:17:00) (1022.4 s wall)". The four failures are one cause: gates 12, 13
  and 14 re-run Gate 11, which is red until the app's copy is refreshed.
- **So the commit of `migrations.py` waits.** The commit guard refuses a
  commit that changes `migrations.py` without a passing `--full` record for
  its tree, and `--full` cannot pass while Gate 11 is red; Gate 11 turns
  green only after the fleet refreshes the app's copy from a commit of this
  branch. Phase 372, the last phase with new routes, had no migration, so
  this order is new. The guard is left as it is.
- **A commit without the migration is not green either.** With migration
  091 and `SCHEMA_VERSION` held out, `wholetree.sh` (fast), on its own:
  exit 1, "wholetree fast: FAILED — 4 failed, 2742 passed, 10 skipped, 33
  warnings, 4 errors in 162.24s (0:02:42) (164.3 s wall)": the seven tests
  of `test_phase334_migration_091.py` and the floor (the tree collects
  12849 then, one test parametrised by migration fewer). So no code is
  committed red.
- **What is committed now:** the documents only (`docs/legal/`, the guides,
  the launch checklist, row 334B and its prompt, README's count, the scope
  file and this log). The code and tests, `src/` and `tests/` exactly as
  built and tested above, are kept whole in the clone's working copy and as
  a patch, `/fleet/run/334_code.patch`.
- **The order for the session that resumes:** apply the code (from the
  working copy or the patch); commit everything except migration 091,
  `SCHEMA_VERSION`, `test_phase334_migration_091.py` and the floor's last
  eight (raised by the diff then measured), so fast mode passes; the
  `app-copy` outcome; once Gate 11 is green, `--full` with the rest, its
  commit, the mutations (`334_mutate.py`, drafted at `/fleet/run/334_mutate.py`),
  the old-code run, the regression of record and the `deploy` outcome.

## 2026-11-19 — stopped for the operator

The plan's anticipated threshold stop: the template, as the Engineer knows
it, names no period for the liability cap, so the period is the operator's.
The answer changes one sentence of `docs/legal/terms.md` ("capped at what
the shop paid Mekno", then the period) and nothing in the code.

## 2026-11-19 14:59 EST — the operator's answer to the stop of 2026-11-19 13:33 EST

Quoted by the fleet's dispatcher, verbatim, from issue #72: the comments the operator's own account (`Kubanjaze`) posted after the Chief Engineer's stop (threshold-or-rule). No other account's words are quoted.

**2026-11-19T19:58:22Z:**

> Cap Mekno's liability to a shop at the fees that shop paid Mekno in the 12 months before the claim.
>
> Recorded as K92 in docs/decisions.md.

## 2026-11-19 15:07 EST — resumed: the answer applied, the code restored

**The answer, applied to the one sentence it covers.** `docs/legal/terms.md`,
"What Mekno owes is capped": "is capped at what the shop paid Mekno" now
reads "is capped at what the shop paid Mekno in fees in the 12 months
before the claim." `test_phase334_legal_texts.py`'s phrase for the cap now
holds the whole sentence, period included, so deleting the period turns it
red. Nothing else changed for the answer; `docs/decisions.md` is not
touched by this session (the operator's comment says K92 is recorded
there).

**The code was not in this clone.** The working copy started clean at
`e4eefa1`, and `/fleet/run/334_code.patch` was gone with the old run's
folder. `git fsck --unreachable` found the last session's stash, "334 code"
(`dc4e31d`, its untracked files in `a27ad05`, 13:30:16). The 15 files under
`src/` and `tests/` were restored from it with the Edit and Write tools,
hunk by hunk; afterwards `git diff dc4e31d -- src tests` was empty and each
new file's `git hash-object` equalled its blob in `a27ad05`. The stray
`<<<<<<< Updated upstream` line that `f53b92c` carried into this log, left
by a stash pop, is removed. With the restored build and the new sentence,
the four new files ran 70 passed.

**What this commit holds,** in the order the entry above set: everything
but migration 091, `SCHEMA_VERSION` 91 and the two test files that need the
table (`test_phase334_migration_091.py`, `test_phase334_terms_routes.py`),
kept at `/fleet/run/held/` and, because `/fleet/run` did not outlive the
last run, also in the clone at `.git/334_held/` with the migration's diff
(`migration_091.diff`); the stash's objects hold them a third time. Collected: 12818, against `bc78448`'s 12779
(collected in a worktree at `/fleet/run/base`) +39 −0, all in
`test_phase334_legal_texts.py` (33) and `_checkout_consent.py` (6);
`COLLECTED_TEST_FLOOR` 12779 → 12818. The rest returns once the app's copy
of the API description carries the two terms routes and Gate 11 is green.

- `wholetree.sh` (fast), on its own, on this tree: exit 0, "wholetree fast:
  PASSED — 2743 passed, 10 skipped, 33 warnings in 149.92s (0:02:29)
  (151.9 s wall)".
- The auth, billing, OpenAPI, payment-route and Gate 11 files with the two
  phase-334 files: "2 failed, 347 passed, 1 warning in 672.91s", the two
  being Gate 11's `TestContractSnapshot` (every live path, every live
  schema in the app's copy). Gate 11 is the only red, so the outcome is
  `app-copy`.

## 2026-11-19 16:04 EST — resumed after the app's copy: migration 091, the mutations, the old code

The dispatcher regenerated the app's copy of the API description from
`eaed639` on the app's branch of this phase's name, and Gate 11 passes
against it. This session resumed in the same clone, at `eaed639`, clean.

**The held part restored.** `.git/334_held/` and `/fleet/run/held/` were
gone; the stash's objects were not. Migration 091 and `SCHEMA_VERSION` 91
were put back with the Edit tool from `dc4e31d`'s diff (afterwards
`git diff dc4e31d -- src/motodiag/core` is empty), and the two test files
with the Write tool from `a27ad05`; each one's `git hash-object` equals its
blob there. The four phase files: 70 passed.

**The floor.** Collected ids against `eaed639` (12818, `--collect-only -q
-o addopts=`): +32 −0. `test_phase334_migration_091.py` 7,
`test_phase334_terms_routes.py` 24, and `test_phase272_gate15.py`'s
`test_rolling_back_peels_every_successor[90]`, parametrized up to
`SCHEMA_VERSION`. `COLLECTED_TEST_FLOOR` 12818 → 12850.

**The mutations.** The script drafted at `/fleet/run/334_mutate.py` did not
outlive the old run, so `334_mutate.py` was written again from the plan's
list, on 404's harness. Each mutation is an exact string that occurs once:
- the exempt tuple emptied;
- the switch read inverted;
- the check moved from `require_api_key` into `get_current_user`;
- `has_accepted` matching the user alone;
- a stale version accepted;
- `consent_collection` sent with the switch off;
- `TERMS_VERSION` out of step with the file's header;
- the cap clause deleted from the terms;
- the rollback leaving the table.

Run on its own: "9/9 red", exit 0 (`334_mutate.out`).

**The old code.** The four new test files were run against master's `src/`
(`e9132ea`, a detached worktree at `/fleet/run/oldcode`, through
`PYTHONPATH`, removed afterwards). Master has no `src/` change since the
branch point `0fa4d89`, so 091 is still the next number.
- `test_phase334_legal_texts.py`, `_checkout_consent.py` and
  `_terms_routes.py` are each "1 error": `cannot import name
  'terms_acceptance' from 'motodiag.auth'`. The module is new, so these
  files cannot run their controls against master's code one by one. The
  knowledge-base control (the switch off, an unaccepted user reaches
  both) passes on this branch.
- `test_phase334_migration_091.py`: "2 failed, 1 passed, 4 errors". Its
  control, `test_before_it_none_of_the_objects`, is the one that passed.

**`wholetree.sh --full`**, on its own, before staging: exit 0, "wholetree
full: PASSED — 5219 passed, 36 skipped, 33 warnings in 1036.70s (0:17:16)
(1039.0 s wall)". It wrote no record because the tree was not staged. It
runs again on the staged tree before the commit.

## 2026-11-19 17:20 EST — the commit, and the regression of record

- `wholetree.sh --full` on the staged tree, on its own: exit 0, "5219
  passed, 36 skipped, 33 warnings in 1036.19s (0:17:16) (1038.7 s wall)".
  Committed as `6d12ab7`.
- `regression.sh`'s first start refused: the `--full` record named the
  parent commit `eaed639`, because the staged tree's record is keyed to
  HEAD, not to the commit that follows. `wholetree.sh --full` again on the
  clean `6d12ab7`, on its own: exit 0, "5219 passed, 36 skipped, 33
  warnings in 1026.12s (0:17:06) (1028.6 s wall)". The guard is left as
  it is.
- `regression.sh` on the clean tree at `6d12ab7`: exit 0. 12745 passed and
  105 skipped make 12850, the collected count and the new floor. The whole
  record, exactly as it printed:

Regression of record: 12745 passed, 0 failed, 105 skipped, 0 errors at `6d12ab7` (37 min 0 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
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
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
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
Line coverage of record: 88.35% at `6d12ab7` (the pin is 87.50%): 0.85 points above it; raise COVERAGE_PERCENT to lock it in

- **Coverage's pin is left at 87.50%.** The plan names no change to it, and
  a total above the pin passes; raising it is a separate decision.
- **Next: the database step.** The operator applies migration 091 to the
  live database on the home desktop. The close-out follows: v1.1, the
  documents to `completed/`, the ROADMAP row ✅ and the handoff.
