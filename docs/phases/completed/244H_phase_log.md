# Phase 244H — Test-database isolation — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-10 — Plan v1.0 written

Opened after noticing, twice in one day, that a regression run had applied a
schema migration to the operator's real `data/motodiag.db`. Migration 054 was
recorded at 06:44:46 and migration 055 the same way later. Neither was requested;
both were discovered only because I checked the schema version before doing
something else.

**Both migrations were correct, which is the part worth dwelling on.** Nothing
was lost, so nothing complained, and the isolation failure would have gone on
indefinitely. The dangerous version of this is a test that exercises a
destructive path — and Phase 244D's migration deleted 5,940 rows.

The mechanism is ordinary: `get_connection(db_path=None)` falls through to
`get_settings().db_path`, and several CLI command paths call `init_db()` bare.
Any test touching one of those without redirecting writes to real data.

**The suite already knew.** Five test files redirect `init_db` to a temporary
database, and their comments explain why — Phase 140's says plainly that every
command path calls it with no arguments. So the knowledge existed, per file,
applied by whoever remembered at the time. That is a convention, and a
convention is a defect that has not happened yet.

The fix has to land at conftest **import** time rather than in a fixture:
`get_settings` is an `lru_cache`d singleton that modules may read while being
imported, so a session-scoped fixture runs too late for anything resolved during
collection.

And it needs a tripwire, because a default that silently stops working is worse
than no default at all. The property actually wanted is "the operator's database
did not change", so the suite will assert that directly — mtime and size across
a full run — rather than settling for path resolution as a proxy.


---

## 2026-09-10 — Built

`MOTODIAG_DB_PATH` is now set at conftest **import** time, before any module can
resolve it, with an autouse tripwire that fails the moment a bare path resolves
back to the operator's database.

**The tripwire disproved Step 0 within a minute.** The plan said nothing
depended on the seeded production corpus. Four Phase 140 tests failed
immediately with `no such table: dtc_codes` — they had been *reading* real data,
not merely risking a write to it. Their fixture patched `init_db`, the write
path, while `get_connection(db_path=None)` resolved through the settings on its
own. Those tests passed for months because the operator's database happened to
be seeded, and would fail on a clean checkout.

A shared `redirect_default_db` fixture now exists so the next author does not
have to rediscover that patching `init_db` covers half the problem.

**The same class of bug appeared while fixing it.** A guard restored its env var
in a `finally`, which runs before `monkeypatch` restores; it wiped the session
default for every test after it. Settings are an `lru_cache`d singleton, so the
stale value followed later tests into whichever database the previous one chose.
The cache is now cleared after every test — structural, not remembered.

**The property was measured, not argued.** Across a complete 6,246-test run the
production database's mtime, size and schema version were byte-identical:

```
BEFORE  mtime 1789052818  size 32301056  schema 55
AFTER   mtime 1789052818  size 32301056  schema 55
```

Two runs earlier the same day had silently advanced that file to schema 54, then
55.

15 guards, 5/5 mutations caught, regression **6246 passed / 0 failed** (baseline 6231; +15 guards), green first run.
