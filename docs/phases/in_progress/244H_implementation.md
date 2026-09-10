# Phase 244H — The test suite writes to the production database

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

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

- [ ] `get_db_path()` inside a test never resolves to the production database
- [ ] A test that calls `init_db()` bare creates a temporary database instead
- [ ] Opening the production database during a test fails loudly
- [ ] The production file's mtime and size are unchanged across a full run
- [ ] The five files with their own redirects still pass unmodified
- [ ] The redirect happens at import time, asserted rather than assumed
- [ ] Mutation: remove the conftest redirect → the tripwire fails
- [ ] Mutation: point the redirect back at production → the guard fails
- [ ] Full regression green

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
