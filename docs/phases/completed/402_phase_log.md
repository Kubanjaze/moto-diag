# Phase 402 — phase log: customer share links off, and the Stripe return pages (K74)

**Status:** Complete

**Built 2026-11-09** by the Chief Engineer, in the fleet's fence, on
`phase-402-share-links-off-and-return-pages`, from the plan
`402_implementation.md` v1.0 (approved by the Executive Officer on issue
#61). No migration; this phase closes out on the branch.

## 2026-11-09 — start

- **The row's status.** The prompt
  (`docs/prompts/402_share_links_off_and_return_pages.txt`) says row 402 is
  🔲; on master it already reads 🚧, put there by K76's commit ("row 402, 🚧
  on master from this commit"). The row is left 🚧 until the close-out; the
  difference is recorded here and changes nothing.
- **K77**, the operator's words, character for character: "Mekno,
  getmekno.com". The sentence of its record this phase rests on: "It is the
  site that introduces the app, links to its download, and serves K74's
  thank-you page, so it replaces K75's "free host for now"."
- **K78**, character for character: "402 is an extension, not a reshape:
  its two settings are new and their defaults keep today's behaviour; the
  only rule it changes is the live start-up check that K74 already
  approved. Correct the fleet's report and let the fleet build it."
- **K79**, character for character: "402: while share links are off, every
  link stops opening, old ones too."
- **The open route**, named from the code: `GET /v1/share/{token}`,
  `view_shared_report` in `src/motodiag/api/routes/share.py`. Minting is
  `create_session_share` in the same file.

## 2026-11-09 — the build: items 1 to 6

- **Item 1.** `config.py`: `share_links_enabled` (default true),
  `stripe_return_page_url` (default empty), the module tuple
  `STRIPE_RETURN_URL_FIELDS` naming the six, and the after-validator
  `apply_stripe_return_page`. Measured before relying on it: pydantic-settings
  does put environment-given fields in `model_fields_set` (a `Settings()`
  with `MOTODIAG_STRIPE_RETURN_PAGE_URL` and `MOTODIAG_CHECKOUT_CANCEL_URL`
  set gave five of the six as the page and `checkout_cancel_url` its own),
  so the plan's fallback (reading the environment by name) was not needed.
- **Item 2.** `public_url.py`: `startup_public_url_problems(settings)`;
  `check_public_base_url` unchanged. `serve.py` calls it, prints the plan's
  one line to stderr when the switch is off, and keeps its loop and its
  refusal as they were.
- **Items 3 and 4.** `share.py`: `SHARE_LINKS_OFF_MESSAGE`; the mint answers
  403 before the ownership check; the open route answers the "Report links
  are off" 404 page before `resolve_share`. The page's body writes the
  apostrophe as `&#39;`, as the route's other pages do; it renders as the
  plan's sentence.
- **Item 5.** The mint declares its 403; the 404's description gains one
  sentence. `tests/test_phase205_gate11.py` passes against the committed
  snapshot (`../moto-diag-mobile/api-schema/openapi.json`), with
  `tests/test_f64_public_url.py`, `tests/test_phase200_share.py` and
  `tests/test_phase191b_serve_migrations.py`: 78 passed, none changed.
- **Item 6.** `tests/test_phase402_share_links_off.py`, 59 tests, all pass.
  - **Against master's code** (`402_mutate.py --old`: master's four
    modules, with stand-ins only for the names the tests import, keeping
    master's behaviour): **18 failed, 41 passed.** The 18 are every test of
    a changed behaviour; the 41 are the controls and pins: the 32 identity
    cases, and nine more (the six's defaults, the six named, the page empty
    with one given, mint on, the message's text, list and revoke, an
    unknown token on, prod with the switch on still blocking, and serve
    refusing with the switch on).
    One test first mixed a new setting's default into the six's defaults
    control and went red on master for that reason; it was split in two
    before this count.
  - **Mutations** (`402_mutate.py`, on a copy, output in `402_mutate.out`):
    **13/13 red**, the plan's nine plus four: a refused open that still
    records a view, serve calling the old check directly, the mint refusing
    after the ownership check, and the 403 not declared.
- **The floor.** A diff of collected ids against master at `67ef2da`
  (12513), each side read with its own `src/`: +59 −0, all in the new file.
  `COLLECTED_TEST_FLOOR` 12513 → 12572.
- **A guard block, recorded:** the edit guard refused a debugging `cp` into
  a folder named by a shell variable ("cannot tell where `cp` `$W/`
  writes"). Re-run with a literal path under `/fleet/run`; the guard is
  unchanged.

## 2026-11-09 — item 7: the documents

`README.md` (two rows in the settings table), `docs/guide/install.md`
("Before it faces anything real"), `docs/guide/api.md` ("Share links" gains
a paragraph on the switch; "Deployment" gains both settings),
`docs/launch-checklist.md` (the prod settings block), `docker-compose.yml`
(the commented example) and `docs/guide/payments.md` (a new section, "The
thank-you page"). The finish line's `git grep -n
MOTODIAG_SHARE_LINKS_ENABLED -- README.md docs/guide
docs/launch-checklist.md docker-compose.yml` finds README.md 1,
docker-compose.yml 1, docs/guide/api.md 2, docs/guide/install.md 1 and
docs/launch-checklist.md 1.

## 2026-11-10 — the regression of record

`wholetree.sh --full` on `4b7a7af`, a clean tree, first: exit 0,
"wholetree full: PASSED — 5103 passed, 36 skipped, 33 warnings in 1004.68s (0:16:44) (1007.2 s wall)". Then `regression.sh`, exit 0; its lines as printed:

Regression of record: 12467 passed, 0 failed, 105 skipped, 0 errors at `4b7a7af` (35 min 51 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
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
Line coverage of record: 88.16% at `4b7a7af` (the pin is 87.50%): 0.66 points above it; raise COVERAGE_PERCENT to lock it in
Coverage data: /fleet/run/home/.cache/motodiag/regressions/4b7a7af_parallel_20261109_233619.coverage.json

Only documents change after this commit.

## 2026-11-10 — close-out

- **Two more guard blocks, recorded**, each for its own reason, neither a
  repeat:
  - the edit guard refused a Python heredoc that edited
    `402_implementation.md`, because its text named `tests/` and the guard
    could not resolve the path written ("a Python script body writes to a
    path the edit guard cannot resolve, and the body names src/ or
    tests/"). The edits were made with the Edit tool instead;
  - it refused a `sed -i` on this log's status line ("`sed -i` edits a file
    in place, and is blocked wherever it points"); nothing in that command
    ran, and the line was changed with the Edit tool.
  The guard is unchanged.
- `402_implementation.md` v1.1: every section noted, Deviations (eight),
  Results, the history row.
- F257 marked closed by Phase 402 in `docs/FOLLOWUPS.md`.
- The handoff, `docs/handoffs/2026-11-10_402_closed.md`: 371's steps 2 to 4
  rewritten. Its step 2 and step 3 checks were run against two throwaway
  settings files in `/fleet/run` before it was written: one with the nine
  lines (the rule found nothing blocking; all six return addresses were the
  page; the block's loop counted 9) and one with share links on (refused).
  Steps 1 and 4 were not run: they restart services on the home desktop.
- The phase's files moved to `docs/phases/completed/`; row 402 ✅; the root
  `phase_log.md` pointer.
