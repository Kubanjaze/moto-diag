# Phase 293 — phase log

**Status:** Complete (closed 2026-11-23; migration 092 applied live, equal to the approved diff)

## 2026-11-22 — Step 0, re-measured by the Engineer

On this branch at `fd47e6e` (v1.0, fixed for the operator's K131).

- **The schema:** `SCHEMA_VERSION = 91` (`src/motodiag/core/database.py`
  line 10); migration 091 at `migrations.py` line 7882, 090 at 7854;
  `apply_pending_migrations` 7977, `rollback_to_version` 8010; the file is
  8031 lines.
- **The wiring guard:** `UNREACHABLE_COUNT = 29` (`integration_gaps_counts.py`
  line 28), `ORPHAN_COUNT = 124` (line 68); the six `motodiag.reference`
  entries at `integration_gaps_allowlist.py` lines 87 to 94, as the plan reads.
- **The floor:** `COLLECTED_TEST_FLOOR = 13135` (line 623).
- **The backup:** `MEDIA_DIRS = ("videos", "photos", "audio")`
  (`backup/snapshot.py` line 33).
- **The terms:** `TERMS_VERSION = "1.0"`, `TERMS_DATE = "2026-11-19"`
  (`auth/terms_acceptance.py` lines 20 and 21); both `docs/legal/terms.md`
  and `docs/legal/privacy.md` headed `Version 1.0 — 2026-11-19`.
- **FTS5 in the fence:** the build's SQLite is 3.46.1 and
  `PRAGMA compile_options` lists `ENABLE_FTS5`.
- **The PDF libraries in the build's venv (`.venv`, read-only):** `pypdf`
  6.14.2, `pillow` 12.2.0 and `reportlab` 4.5.1 import; **`pypdfium2` does
  not** (`ModuleNotFoundError: No module named 'pypdfium2'`; nothing named
  `*pdfium*` under `.venv/lib/python3.14/site-packages`). No other PDF
  renderer is on the machine (`pdftoppm`, `gs`, `mutool`, `qpdf`: none on
  PATH; no `fitz`, `pdfplumber`, `pdfminer` or `pikepdf` module). No virus
  scanner is on PATH (`clamscan`, `clamdscan`: none), which the plan's
  tests do not need: they use stub scanners.
- **K128's row:** `docs/decisions.md` on this branch ends at K127; K128 is
  quoted from `293_step0.md`, as the plan says.

## 2026-11-22 — item 1a: the deploy tool reads a table without a rowid by its key (K131)

Built first and in its own commit, as the plan says, so it can reach master
through its own pull request before the database step.

- **`.claude/skills/deploy/deploy.py`:** `_rows`, called by `dump()`. A table
  whose `sqlite_master` definition ends `WITHOUT ROWID` is read by its
  primary key's columns (`pragma table_info`'s `pk`, in key order) and keyed
  by that value, or by a tuple of them for a key of more than one column;
  every other table by rowid as before. A table named like a shadow table
  but defined with a rowid stays keyed by rowid (a test holds it).
  `diff()`, `check_scope`, `report` and `exact` read the keys unchanged.
- **`scripts/f158_census.py`** (a deviation: the plan does not name it). The
  end-to-end case, the dry run on an FTS5 index, went red with
  `no such column: rowid` at `f158_census.py` line 74: the census the dry
  run runs on its copy also read every table by rowid. It now names a row of
  a table without a rowid by its key's first column. The dry run on live
  would have failed the same way, so the item is not done without it.
- **The end-to-end case** builds the page table and the FTS5 index in the
  stand-in migration, as 092 does (the index's content table is new with
  it). Found while writing it: `dump()` reads an external-content FTS5
  table's own rows through its content table, so an index over a table
  that already held rows would read as rows added to the index. 092's
  content table is new and empty, so its dry run shows none; nothing was
  changed for it.
- **`SKILL.md`** (step 2) and **`CHANGELOG.md`** (a dated entry naming K131).
- **The known-bad fixture:** `.claude/skills/deploy/fixtures/without_rowid.sql`.
- **Tests:** `tests/test_phase293_deploy_without_rowid.py`, 6. Seen red on
  the old code (both files stashed): 4 failed, 2 passed; the two that pass
  on both are the known-bad fixture's failure under the old read and the
  rowid control. With the change: 6 passed. The existing deploy, census and
  seed-parity tests (`-k "deploy or f158 or verify_live or server_writes or
  what_the_change or seed_parity or 381_content"`): 289 passed.
- **`COLLECTED_TEST_FLOOR`** 13135 to 13141, by a diff of collected ids
  against `fd47e6e`: +6 -0, all in the new file.

## 2026-11-22 — stopped: the build machine cannot read PDFs

The plan's renderer (`manuals/render.py`) and the last of `check_pdf`'s
checks open, render and read each page with `pypdfium2`, and its tests
(`test_phase293_checks.py`, `test_phase293_render_search.py`, the upload,
review, command-line and restore tests, which all need a manual that
renders) run them on PDFs made in the test. `pypdfium2` is not in the
build's venv, the venv is read-only, there is no network, and nothing else
on the machine renders a PDF page (Step 0, above). Those tests cannot be
made green here, and making them skip would leave the upload, the render,
the search and the review untested in the regression of record. A stand-in
for the library inside the tests would test the code against a fake, not
against `pypdfium2`, which is a change to what the plan's tests prove.

So the phase stops (rule 1, a test it cannot make green), with item 1a
committed. Nothing else of the plan is built: no migration, no route, no
change to the terms.

## 2026-11-22 22:12 EST — the operator's answer to the stop of 2026-11-22 20:20 EST

Quoted by the fleet's dispatcher, verbatim, from issue #86: the comments the operator's own account (`Kubanjaze`) posted after the Chief Engineer's stop (test-cannot-be-green). No other account's words are quoted.

**2026-11-23T03:12:00Z:**

> Option 1, done: pypdfium2 5.15.2 installed in the fleet's build setup, no other package changed.

## 2026-11-22 23:00 EST — resumed on the operator's answer

Applied literally: the build's venv now imports `pypdfium2` 5.15.2
(`importlib.metadata.version('pypdfium2')`, from
`.venv/lib/python3.14/site-packages/pypdfium2`), and `pip freeze` lists the
same packages as Step 0 otherwise (`pypdf` 6.14.2, `pillow` 12.2.0,
`reportlab` 4.5.1 among them). Nothing else in the answer, and nothing else
was asked of it. The build resumes from `15889f7` with item 1a committed.

## 2026-11-22 — migration 092 (`fa6c261`)

- **The shadow tables, measured:** on a fresh database at 92,
  `manual_pages_fts_config` holds 1 row (`version`) and
  `manual_pages_fts_data` 2; `_idx` and `_docsize` hold none. The two
  without a rowid are `_config` and `_idx`. No `manual_pages_fts_content`.
  `tests/test_phase293_migration.py` measures this and holds the scope
  file to it; `deploy.check_scope` on the 91 to 92 diff reports no problem.
- **The rollback** drops the triggers, the FTS table (its shadow tables with
  it), `manual_pages`, `manual_reviewers`, the two indexes and the twelve
  columns; `DROP COLUMN` was tried first on a column with `REFERENCES` and
  one with a `CHECK` (SQLite 3.46.1) and both drop. A Phase 117 row keeps
  every field through the migration and the rollback, and migrating again
  works.
- **The first `--full` run failed** on `RUFF_FINDINGS` (1111 against 1108):
  three lines of the migration's SQL over 100 characters. Wrapped before the
  first commit; not a bug fix, the code was never committed that way. The
  second `--full` passed: 5437 passed, 36 skipped (1530.9 s).
- The 715 tests that name `manual_references` or `MIGRATIONS` passed
  before the commit.

## 2026-11-22 — the library (`4b58135`)

- **Built:** `src/motodiag/manuals/` (`__init__` with the library's seven
  refusals, `storage`, `checks`, `scan`, `render`, `review`), the
  `manual_references` repo and models extended, `api/routes/manuals.py`
  (both routers), `errors.py`'s rows, `app.py`'s two routers, `openapi.py`'s
  two tags, `cli/manuals.py` and `main.py`'s registration,
  `TierFeatures.manual_storage_bytes`, `MEDIA_DIRS`.
- **The checks on planted files:** the good file and an owner-password-only
  file pass; the PNG, JavaScript, attachment, Launch action and locked
  file each give exactly their own reason.
- **The quality counts** after the code, by `scripts/code_quality.py`'s
  `counts()`: ruff 1108, mypy 202, complex 25, big 5, helpers 19,
  swallowed 22, every one at its pin. Two new mypy errors were fixed before
  the commit (`add_page`'s `lastrowid`, the upload's response read through
  `_manual_in_shop`).
- **The wiring gate** (`test_phase209B`, `244U`, `244W`): the six
  `motodiag.reference` entries out (`UNREACHABLE_COUNT` 29 to 23);
  `reference/video_repo.py`'s `add_video` and `update_video` reported as
  live orphans and listed as substrate for 296; `diagram_repo` and
  `photo_repo` reported as module islands and listed as substrate for 294
  and 295 (`MODULE_ISLAND_COUNT` 9 to 10). Not foreseen by the plan:
  `motodiag.engine.repair` left the islands, because the now-live
  `reference/models.py` names its own `SkillLevel`, a name
  `engine/repair.py` also defines, and the gate matches by name. Its
  `RepairProcedureGenerator` became a live orphan, listed as
  unwired-feature with the island entry's reason (`ORPHAN_COUNT` 124 to
  127), and `test_phase244W`'s count of engine islands went from 5 to 4 with
  the reason in a comment. A deviation; v1.1 names it.
- **Two test bugs while writing the API tests,** not code bugs: the
  upload's 201 is written before the background render runs, so the test
  reads `rendered_pages` from the row after it; and `reportlab` stamps each
  PDF with its time, so a duplicate is made by reusing one byte string.
- **Before the commit:** the fast whole-tree passed (3002 passed); the 40
  test files that name the routers, tags, `cli.commands`, `MEDIA_DIRS` or
  `TIER_LIMITS` ran, 935 passed, and the only red was Gate 11's two
  snapshot tests (the app's copy of the description, expected).

## 2026-11-22 — the terms 1.1, the guides, the floor (`57ccd3c`)

- **The date is 2026-11-23,** not the 22nd: `tests/test_phase408_site.py`
  dates an uncommitted page by today in UTC (already the 23rd at 23:35 EST)
  and a committed one by its commit's day, so a page changed that late on
  the 22nd could not pass before and after its commit. The headers,
  `TERMS_DATE` and the sitemap say 2026-11-23, and the commit was made with
  `TZ=UTC`, so its day is the 23rd too. 334's rule (the day the file is
  committed) holds in UTC.
- **`tests/test_phase334_terms_routes.py`:** one test,
  `test_a_new_version_must_be_accepted_again`, its two literals `"1.0"`
  made the version captured before the monkeypatch; the rest of the file
  is unchanged and green.
- **`pyproject.toml`:** `pypdfium2>=4` and `pypdf>=4` in `vision`;
  `test_phase209_packaging.py` green.
- **`COLLECTED_TEST_FLOOR`** 13141 to 13255, by a diff of collected ids
  against `ebe52ed` (13142 collected there): +114 in the eight new files,
  -4 and +3 in the wiring gate's parametrised entries.

## 2026-11-22 — the mutations and the old code

- **`293_mutate.py`, 25 mutations: 25/25 red** (`293_mutate.out`).
- **The new files on the old code** (each copied into a worktree at
  `ebe52ed`, run with that tree's `src/` first on the path): migration 3
  failed, 6 errors, 2 passed (the FTS5 compile option and the empty
  "before" state, controls); checks, render_search, manuals_api, review,
  cli and backup_restore each fail at import; terms 10 failed, 1 passed
  (the Backblaze sentence, a control).
- **Controls run green on this branch,** in one run, 564 passed:
  `test_phase194_commit0_photo_upload.py`, `test_phase172_rbac.py`, every
  `test_phase303*.py` (the permission tests: `manage_shop` still the
  owner's and the service writer's), `test_phase334_legal_texts.py`,
  `test_phase334_terms_routes.py`, `test_phase345_snapshot_restore.py`,
  `test_phase404_bike_limit.py`, `test_phase404_plan_names.py`,
  `test_phase408_site.py`, `test_phase209B_integration_gaps.py`. Gate 11
  (`test_phase205_gate11.py`) waits for the app's copy.

## 2026-11-22 — the seven readings, as built

1. The reviewer is a table of user ids (`manual_reviewers`), not a fifth
   `SHOP_ROLES` value; `require_reviewer` is the API's only way in.
2. The uploading roles are `owner` and `service_writer`, through
   `manage_shop`; the tech is 403 (tested).
3. The limit is the shop's plan's, by `shop_plan`; GB is 1024³; a rejected
   or taken-down file counts until it is deleted, and the refusal says so.
4. The page images are made again after a restore (`manuals render`), not
   backed up.
5. A duplicate is judged within one shop; another shop's identical file is
   stored again (tested).
6. The terms' clause leaves out "(for a company, its own shops)" (tested).
7. A publisher's complaint is recorded by the reviewer as `taken_down`.

Choices the plan left to the build, each shipping the same behaviour: a
refusal's wording; `kind` defaults to `service_manual` in the upload's tag;
the page route takes `size=full|thumb`; the search answers at most 100 hits
(20 by default), a request bound and not a plan limit; the upload's
temporary file is `.manual_upload_*.pdf` at the data folder's top, outside
the four backed-up folders.

## 2026-11-23 — the full whole-tree, before the regression of record

`wholetree.sh --full`: 1 failed, 5470 passed, 36 skipped (17:31). The one
failure is Bug fix #1.

### Bug fix #1 — 2026-11-23 — a second pin of the islands table still held `engine.repair`

- **Issue:** `tests/test_phase244Z_shelved_content.py::TestStillShelved::test_the_module_is_still_on_the_islands_table[repair]`
  failed: `motodiag.engine.repair` is no longer in `MODULE_ISLANDS`.
- **Root cause:** the library's commit (`4b58135`) took `engine.repair` off
  the islands table (the now-live `reference/models.py` shares the name
  `SkillLevel`, and the gate matches by name) and moved its generator to
  `ORPHANS`, updating `test_phase244W` and `integration_gaps_counts.py`, but
  not 244Z's own list of modules it expects on the table. The table is
  pinned in more than one file, and the fast whole-tree does not run 244Z.
- **Fix:** 244Z's test keeps its six ids and its intent (nothing in a
  shelved module reaches a user): for `repair` it asserts the module is off
  the islands table and that `RepairProcedureGenerator` is on `ORPHANS` as
  `unwired-feature`; the other four still assert the islands table. The
  collected count is unchanged, so the floor is unchanged.
- **Files:** `tests/test_phase244Z_shelved_content.py`.
- **Verified:** 244Z, 244W and 244U, 86 passed; the same test on the
  previous commit's file, 1 failed, 11 passed.

**Commit.** `17b2b58` ("Phase 293: Bug fix #1").

## 2026-11-23 — the first regression run, not of record

`regression.sh` at `17b2b58` failed (not of record): 13148 passed, 2 failed,
105 skipped (38 min 2 s wall). Both failures are Bug fix #2. The full
whole-tree before it had passed at `17b2b58` (5471 passed, 36 skipped);
`test_phase356_workflow_run.py` is not one of its files.

### Bug fix #2 — 2026-11-23 — Phase 356's table dump read a WITHOUT ROWID table by rowid

- **Issue:** `tests/test_phase356_workflow_run.py`'s
  `test_a_run_leaves_every_table_as_it_was` and
  `test_a_planted_write_is_seen_by_the_dump` failed with
  `sqlite3.OperationalError: no such column: rowid`.
- **Root cause:** the file's `_dump` reads every table in a fresh database
  `ORDER BY rowid`. Migration 092's FTS5 index makes
  `manual_pages_fts_idx` and `manual_pages_fts_config`, which are WITHOUT
  ROWID: the same fact item 1a taught the deploy tool, not carried to the
  one test that dumps every table.
- **Fix:** `_dump` orders a WITHOUT ROWID table by its primary key
  (`PRAGMA table_info`), every other table by rowid as before. The
  comparison is unchanged.
- **Files:** `tests/test_phase356_workflow_run.py`.
- **Verified:** the file, 32 passed; the previous commit's file on this
  code, 2 failed, 30 passed. Every other `ORDER BY rowid` in `tests/`
  names its tables and passed in the same regression run.

**Commit.** `0f821e1` ("Phase 293: Bug fix #2").

## 2026-11-23 — the regression of record, at `0f821e1`

`wholetree.sh --full` at `0f821e1` passed first: 5471 passed, 36 skipped
(1112.6 s wall). Then `regression.sh` on the clean tree, its record exactly
as it printed it:

Regression of record: 13150 passed, 0 failed, 105 skipped, 0 errors at `0f821e1` (38 min 15 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
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
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
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
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
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
Line coverage of record: 88.61% at `0f821e1` (the pin is 88.00%): 0.61 points above it; raise COVERAGE_PERCENT to lock it in

The coverage pin is left at 88.00%: the plan does not ask for it to be
raised, and a pin above the count is not required by the ratchet.

## 2026-11-23 — stopped for the database step

The plan has "## The database step", so the phase is not closed here. Every
phase document stays in `docs/phases/in_progress/`. Migration 092 goes to
the live database through the deploy step, from the scope file
`293_deploy_scope.json`, after the regression above and before the
close-out commit.

## 2026-11-23 — the operator's answer, and migration 092 on live

The dry run ran on a copy on the home desktop (`293_dryrun_diff.md`,
sha256 `91c7638cd7e74979a6075242fa9149360ec5e2704169de3648293adf4d1a283b`,
at `7c0eaaa`; backup `motodiag_pre293_20261123_220543.db`; scope problems
none; F158 census on the copy 41). The file's sha256, read again on this
branch with `sha256sum`, is the one the answer names. Asked at
2026-11-23T22:05:58-05:00, the operator typed, verbatim
(`293_deploy_answer.md`):

> yes

The operator then applied migration 092 to live and checked it, and the
dispatcher checked it again with `verify-live`. `293_live_diff.md`, live
after the apply against the backup:
- **scope problems:** none;
- **equals the approved exact diff:** yes;
- **set aside as written by the running API:** 0;
- **other differences, listed:** 1, `stripe_event_cursors` row 1's
  `polled_at` (03:05:29.874 to 03:05:50.124 UTC), the payments feed's own
  poll time between the backup and the check, not the migration's; it is
  listed and not a scope problem, as 405 made the check;
- **F158 census on live:** 41, as on the copy.

What it added: the columns of `manual_references` (its definition
changed, no row), the tables `manual_pages` and `manual_reviewers`, the
index `manual_pages_fts` with its four working tables, three indexes,
three triggers; SQLite's own first rows in `manual_pages_fts_config` (1)
and `manual_pages_fts_data` (2); and `schema_version` row 92
(2026-11-24 03:06:00 UTC). No existing row changed or was removed.

## 2026-11-23 — the close-out

No code changed after the regression of record: every commit after
`0f821e1` changes documents only (`git diff --stat 0f821e1 HEAD` lists the
three deploy files and this log). The close-out moves the phase's files,
the three deploy files and the scope file to `docs/phases/completed/`,
writes v1.1, the ROADMAP row, the root `phase_log.md` pointer and the root
`implementation.md` row, and the handoff
`docs/handoffs/2026-11-23_293_closed.md`, which carries the steps after
the merge.

- **The root version is 0.13.146,** not 0.13.143: this branch's copy of
  `implementation.md` reads 0.13.142, and master's already reads 0.13.145
  (372B, merged after this branch was cut). The merge brings master in.
- **The bug-fix register** now names each fix's commit by its hash
  (`17b2b58`, `0f821e1`), where the entries said "the commit that carries
  this entry".
- **What the handoff's blocks were tested on**, in `/fleet/run/`:
  - each block's inner script passes `bash -n`;
  - step 5 (the reviewer), with `HOME` a stand-in: a clone of this branch
    as the server's folder, wrappers for its `python` and `motodiag`
    (symlinks to `.venv/bin` did not find the venv's packages, a fault of
    the stand-in), `live.json` naming a fresh database at 92 with 44
    bulletins and one account. An empty name, an unknown name and (after
    deleting the bulletins) an empty bulletin table each printed SOMETHING
    IS OFF. The real name took a backup, granted, listed it and printed
    ALL GOOD, and a second paste printed "already reviews" and ALL GOOD;
  - step 7 against no settings file, the switch absent and
    `export MOTODIAG_TERMS_REQUIRED=1`: red, ALL GOOD, red;
  - step 4: `GET /v1/terms` from this code answers
    `{"version":"1.1","date":"2026-11-23",…}` and `/healthz`
    `{"status":"ok","schema_version":92,…}`. The 68-byte test file,
    scanned through `scan_file` with a stub `clamdscan` on PATH, gave
    `infected | …: Eicar-Signature FOUND`, which the block's `case`
    matches.
  The parts that read GitHub, Cloudflare, the desktop's services or the
  app's checkout could not be run from here (no network, no desktop), and
  the handoff says so.

## 2026-11-23 — fix round 1: step 6 waits for the operator's review

The first review found that the handoff's step 6 block opened the app's
pull request and merged it in the same paste, with no point at which the
operator could look at it, where item 10 says the merge comes "after the
operator's review". A document fix, not a code change: the block now
prints the pull request's link and reads an answer from the terminal
(`/dev/tty`, since the block's own input is the paste); only `yes` runs
`gh pr merge`, and anything else prints SOMETHING IS OFF with the pull
request left open. A second paste returns to the same question. The step's
introduction says so, and Deviations item 8 records that the review is
kept. Tested in `/fleet/run/`: the block passes `bash -n`; the answer
check with `yes` reached the merge, with `no` and with no input it printed
SOMETHING IS OFF. No code changed, so the regression of record stands.

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| Regression of record: 13150 passed, 0 failed, 105 skipped at 0f821e1, coverage 88.61% | kept | "Regression of record: 13150 passed, 0 failed, 105 skipped, 0 errors at `0f821e1` (38 min 15 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)" | docs/phases/completed/293_phase_log.md p. 284 | 2 · none · kept |
| COLLECTED_TEST_FLOOR 13135 to 13141 to 13255 | kept | "COLLECTED_TEST_FLOOR = 13255" | tests/test_phase255B_collected_test_floor.py p. 637 | 2 · none · kept |
| Item 1a: six tests, 4 red on the old code | kept | "Seen red on the old code (both files stashed): 4 failed, 2 passed" | docs/phases/completed/293_phase_log.md p. 63 | 2 · none · kept |
| UNREACHABLE_COUNT 29 to 23, MODULE_ISLAND_COUNT 9 to 10, ORPHAN_COUNT 124 to 127 | kept | "ORPHAN_COUNT = 127" | tests/support/integration_gaps_counts.py p. 75 | 2 · none · kept |
| test_phase244W's engine islands 5 to 4 | kept | "assert len(engine) == 4" | tests/test_phase244W_module_islands.py p. 145 | 2 · none · kept |
| The search answers 20 hits by default and at most 100; kind defaults to service_manual | kept | "limit: int = Query(20, ge=1, le=100)," | src/motodiag/api/routes/manuals.py p. 338 | 2 · none · kept |
| The upload's temporary file is .manual_upload_*.pdf at the data folder's top | kept | "fd, name = tempfile.mkstemp(dir=settings.data_dir, prefix=\".manual_upload_\", suffix=\".pdf\")" | src/motodiag/api/routes/manuals.py p. 273 | 2 · none · kept |
| Storage limits 2, 20 and 50 GB in TIER_LIMITS (K119) | kept | "manual_storage_bytes=20 * 1024**3," | src/motodiag/cli/subscription.py p. 120 | 2 · none · kept |
| MEDIA_DIRS gains manuals and only manuals | kept | "MEDIA_DIRS = (\"videos\", \"photos\", \"audio\", \"manuals\")" | src/motodiag/backup/snapshot.py p. 36 | 2 · none · kept |
| TERMS_VERSION 1.1 dated 2026-11-23 | kept | "TERMS_DATE = \"2026-11-23\"" | src/motodiag/auth/terms_acceptance.py p. 21 | 2 · none · kept |
| An unknown username exits 1 with "no user named …; nothing was changed" | kept | "raise click.ClickException(f\"no user named {username!r}; nothing was changed\")" | src/motodiag/cli/manuals.py p. 26 | 2 · none · kept |
| decide refuses approval while rendering and needs a reason for rejected/taken_down | kept | "if decision in (\"rejected\", \"taken_down\") and reason is None:" | src/motodiag/manuals/review.py p. 85 | 2 · none · kept |
| Live: no scope problems, equal to the approved diff, F158 census 41 | kept | "**F158 census on live:** 41, as on the copy." | docs/phases/completed/293_phase_log.md p. 401 | 2 · none · kept |
| Root implementation.md at 0.13.146 (Deviation 10) | kept | "**Version:** 0.13.146 | **Date:** 2026-11-23" | implementation.md p. 3 | 2 · none · kept |
| K128's row is not on this branch's decisions.md | kept | "K127" | docs/decisions.md p. 133 | 2 · none · kept |
| ROADMAP row 293 closed with date and regression line | kept | "**CLOSED 2026-11-23.** Built by the fleet" | docs/ROADMAP.md p. 542 | 2 · none · kept |
| F292 cited for the bulletin check in step 5 | kept | "A `motodiag` command run on live writes into it through `init_db`, whose bulletin seed fills an empty table" | docs/FOLLOWUPS.md p. 6764 | 2 · none · kept |
| Step 6 merges only after the operator types yes (Deviation 8) | kept | "[ \"$ANS\" = yes ] || bad \"you did not type yes; the pull request is open and not merged" | docs/handoffs/2026-11-23_293_closed.md p. 471 | 2 · none · kept |
| The ticked item says "the three error codes in errors.py", and "seven refusals" in __init__.py | killed | "the three error codes in `errors.py`" | docs/phases/completed/293_implementation.md p. 224 | 2 · wording · open F298 |
