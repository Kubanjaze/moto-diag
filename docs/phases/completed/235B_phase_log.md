# Phase 235B — Phase Log

**A `regulation` provenance value for known_issues**
Branch: `phase-235b-regulation-provenance` | Date: 2026-09-08

## Step 0 — existing-code audit

- Migration 051 CHECK-constrains `known_issues.source` to five values; none
  fits a primary legal document. Phase 235 recorded the gap and deferred it.
- `known_issues` is created by SCHEMA_SQL, not by a migration. Dumped live
  rather than read off the DDL: 17 columns, `id ... AUTOINCREMENT`, two
  indexes, no triggers or views, one FK child (`repair_plan_items`).
- `get_connection` sets `foreign_keys=ON`, so `DROP TABLE known_issues` is
  refused while a child row references it — the pragma toggle is required.
- `IssueSource` in `api/routes/kb.py` mirrors the CHECK for OpenAPI codegen;
  omitting a value is a validation error on a real row, not a policy choice.
- Two Phase 211 tests hand-encode the vocabulary and break by design.

## Verification done rather than assumed

Probed on a populated v51 DB with a live FK child: pragma takes effect inside
`executescript`; rows, autoincrement sequence, indexes and the child FK all
survive; `foreign_key_check` clean; pragma restored ON; CHECK still rejects
typos; rollback maps `regulation` → `service-manual` and preserves everything.

## Build

| Surface | Change |
|---------|--------|
| `core/migrations.py` | migration 052, table rebuild + rollback |
| `core/database.py` | SCHEMA_VERSION 51 → 52 |
| `api/routes/kb.py` | `IssueSource` gains `regulation`; trust prose updated |
| `cli/kb.py` | `VERIFIED_SOURCES` gains it; new scope-note branch |
| `knowledge/issues_repo.py` | docstring vocabulary |
| seed content | 1 entry of 8 reclassified |
| `scripts/check_f9_patterns.py` | parser follows table-rebuild renames |
| tests | new 235B file (24), plus 235, 211, gate9, gate11, 191B updated |

## Failures caught during the build

- **F9 reported drift that did not exist**, because its CHECK parser cannot
  see through a table rebuild. Fixed the parser rather than suppressing the
  finding — the rule was blind to every rebuild migration, which is the only
  kind that can change a CHECK.
- **Three schema pins fired**, correctly. Two carried stale provenance
  comments describing migrations several versions old; corrected while bumping.

## Close-out

- Regression: 5760 passed / 0 failed. F9 lint clean.
- Cleared for: roadmap row 235B, implementation.md row + 0.13.45 → 0.13.46,
  merge to master, delete branch.
- **Still open from 223:** the KTM 390/790/890 Adventure line has no roadmap row.
