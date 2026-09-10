# Phase 244H — The test suite writes to the production database

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

Twice today a regression run applied a schema migration to
`data/motodiag.db` — the real database — without anything asking it to.
Migration 054 was recorded at 06:44:46 and migration 055 later the same way. On
both occasions the migration was *correct*, so nothing was lost. That is luck,
not isolation.

The mechanism is not obscure. `get_connection(db_path=None)` falls through to
`get_settings().db_path`, which points at `data/motodiag.db`, and several CLI
command paths call `init_db()` with no arguments. A test exercising one of those
paths without redirecting it writes to the operator's data.

**The suite already knows this.** At least five test files redirect `init_db`
to a temporary database, with comments explaining that command paths call it
bare — Phase 140's says so outright. The knowledge exists per-file, applied by
whoever remembered. That is a convention, and a convention is a defect that has
not happened yet.

## Non-goals

- **Not rewriting the five files that already redirect.** Their local fixtures
  are correct and more precise than a global default; this adds a floor beneath
  them, it does not replace them.
- **Not changing production defaults.** `get_settings().db_path` pointing at
  `data/motodiag.db` is right for the application. The test environment is what
  needs to differ.

## Logic

**A default set before anything can read it.** `MOTODIAG_DB_PATH` is set at
`conftest.py` **import time**, not in a fixture. `get_settings` is an
`lru_cache`d singleton and modules may read it while being imported, so a
session-scoped fixture would run too late for anything already resolved during
collection. Conftest module level is the earliest hook pytest offers.

The path points into a per-run temporary directory, and `reset_settings()` is
called so any value cached before the assignment is discarded.

**A tripwire, because a default that silently stops working is worse than
none.** An autouse fixture asserts that the resolved `get_db_path()` is not the
production path, and a guard patches `sqlite3.connect` for the duration of a
test to fail loudly if anything opens the real file. The redirect is the fix;
the tripwire is what stops the fix rotting.

**A guard that the operator's database is untouched.** The suite records
`data/motodiag.db`'s modification time and size before and after, and fails if
either moved. That is the property actually wanted — every other assertion here
is a proxy for it.

## Key Concepts

- **A convention is a defect that has not happened yet.** Five files remembered
  to redirect; the sixth is the bug.
- **Import time, not fixture time.** A cached singleton read during collection
  cannot be redirected by a fixture that runs afterwards.
- **The correct migration is the dangerous case.** Both incidents were harmless,
  which is exactly why neither was noticed until a third party looked.
- **Assert the property, not the proxy.** "The production file did not change"
  is the claim; path resolution is evidence for it.

## Verification Checklist

- [x] `get_db_path()` inside a test never resolves to the production database
- [x] A test that calls `init_db()` bare creates a temporary database instead
- [x] Opening the production database during a test fails loudly
- [x] The production file's mtime and size are unchanged across a full run
- [x] The five files with their own redirects still pass unmodified
- [x] The redirect happens at import time, asserted rather than assumed
- [x] Mutation: remove the conftest redirect → the tripwire fails
- [x] Mutation: point the redirect back at production → the guard fails
- [x] Full regression green

## Risks

- **A test may depend on the seeded production corpus without saying so.** Step 0
  found none, but the failure would be a confusing empty result rather than an
  error. The tripwire's message names the cause so it is diagnosable on sight.
- **Import-time environment mutation is a blunt instrument.** It is scoped to
  one variable, set only when unset so an explicit override still wins, and
  documented at the assignment.
- **The tripwire could fire on a legitimate read.** It targets the production
  path specifically, not all of `data/`, and the guard that patches
  `sqlite3.connect` is opt-in per test rather than autouse — a global patch
  would be a second, subtler way to break the suite.

---

## Deviations from Plan

**Step 0 was wrong, and the tripwire disproved it within a minute.** The plan
said no test depends on the seeded production corpus. Four Phase 140 tests
failed the instant the default was redirected, with `no such table: dtc_codes`.

They were not merely *at risk* of writing to real data — **they were reading
it.** Their fixture patched `init_db`, which is the write path, while
`get_connection(db_path=None)` resolves through `get_settings().db_path`
independently. Every query in those tests went to the operator's database and
passed because it happened to be seeded. On a clean checkout they would fail.

That changes what this phase found. Not "tests might touch production" but **a
working suite has been quietly depending on the operator's data.** The fixture
now redirects the setting as well, and a shared `redirect_default_db` fixture
exists so the next author does not have to rediscover that patching `init_db`
covers half the problem.

**I introduced the same class of bug while fixing it.** A guard restored its env
var in a `finally`, which runs *before* `monkeypatch` restores — it cleared the
session default for every test after it and turned four unrelated guards into
errors. Settings are an `lru_cache`d singleton, so a stale entry follows the
next test into whichever database the previous one chose. The cache is now
cleared after every test, which makes the hazard structural rather than a thing
to remember.

## Results

| Metric | Value |
|--------|-------|
| Tests found reading the production database | **4** (Phase 140 CLI tests) |
| Production DB across a full run | **mtime, size and schema version identical** |
| Guards | 15 |
| Mutations run / caught | 5 / 5 |
| Regression | **6246 passed / 0 failed** (baseline 6231; +15 guards), green first run |

Measured before and after a complete 6,246-test run:

```
BEFORE  mtime 1789052818  size 32301056  schema 55
AFTER   mtime 1789052818  size 32301056  schema 55
```

Two earlier runs today silently advanced that same file to schema 54 and then
55.

**Key finding: the correct migration is the dangerous one.** Both incidents were
harmless, so neither surfaced — no failure, no warning, nothing to investigate.
The isolation gap was only visible because I happened to check a schema version
before doing something unrelated. A test suite that writes to real data and
gets away with it teaches nobody anything, right up until the write is
`DELETE`. Phase 244D's migration removed 5,940 rows.

**A convention is a defect that has not happened yet.** Five files already
redirected `init_db` and their comments explained exactly why — Phase 140's said
outright that every command path calls it bare. The knowledge was present,
correct, and applied by whoever remembered. What was missing was a floor.
