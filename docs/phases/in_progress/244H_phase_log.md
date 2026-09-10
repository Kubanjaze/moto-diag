# Phase 244H — Test-database isolation — phase log

**Status:** Planned
**Opened:** 2026-09-10

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
