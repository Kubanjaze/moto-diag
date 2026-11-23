# Phase 293 — phase log

**Status:** In progress (built; the database step waits for the operator)

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
- **Commit:** the commit that carries this entry ("Phase 293: Bug fix #1").

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
- **Commit:** the commit that carries this entry ("Phase 293: Bug fix #2").

## 2026-11-23 — the regression of record

After `wholetree.sh --full` at `0f821e1` (5471 passed, 36 skipped), on a
clean tree:

Regression of record: 13150 passed, 0 failed, 105 skipped, 0 errors at `0f821e1` (36 min 46 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
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
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
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
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Line coverage of record: 88.61% at `0f821e1` (the pin is 88.00%): 0.61 points above it; raise COVERAGE_PERCENT to lock it in

The migration waits for the operator: the live apply comes next, then the
close-out.
