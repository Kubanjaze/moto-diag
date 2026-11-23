# Phase 293 — phase log

**Status:** Paused (stopped for the operator: the build machine cannot read PDFs)

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
