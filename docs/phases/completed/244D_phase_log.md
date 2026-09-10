# Phase 244D — known_issues deduplication + idempotent loading — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-10 — Plan v1.0 written

Opened out of Phase 244C, which found the defect by accident: a live guidance
run for a Honda CBR600F4i was handed 20 corpus rows containing **two distinct
facts**, and reported — accurately — that the corpus covered only fuel injector
issues and float bowl fuel leaks. The corpus was not narrow. It was stored ten
times over.

`known_issues` holds 6,600 rows for 660 distinct issues, uniformly 10× each. No
uniqueness constraint exists on the table and `add_known_issue` is a plain
INSERT, so every run of the seed loop duplicates everything.

**Step 0 turned up three things that changed the plan.**

*The seed files are clean.* 970 entries, 970 distinct `(make, model, title)`,
no collisions. So the duplication is purely a load-time defect and the key is
sound — checked rather than assumed, because designing a constraint around an
unverified key is how you get a migration that cannot be applied.

*A naive constraint would have shipped looking correct.* **43 entries — 430
rows — carry `model IS NULL`, and SQLite treats NULLs as distinct in a UNIQUE
constraint.** Inserting the same NULL-model row three times under
`UNIQUE(make, model, title)` with `INSERT OR IGNORE` yields three rows; under a
unique expression index over `(make, COALESCE(model,''), title)` it yields one.
Demonstrated before writing the migration. Without that, 4.4% of the corpus
would have gone on multiplying behind a constraint that looked like a fix.

*The local database is stale, not just duplicated.* It holds 660 of the 970
seeded entries and only five makes — every European and electric make from
Tracks K and L is missing. So guards must be built against fixtures derived
from the seed files, never against `data/motodiag.db`, or they would certify a
migration on a corpus that is not the real one.

**One finding deliberately left out of scope.** The `make` column carries
multi-make strings and, in at least one row, a full sentence:
`"BMW and Ducati have listed adjustments; KTM, Triumph, Aprilia, Moto Guzzi have none"`.
That pollutes Phase 244C's resolver vocabulary, which reads `SELECT DISTINCT
make`. It is a real defect and it is not this phase's; folding it in would mean
two unrelated data migrations under one set of guards.


---

## 2026-09-10 — Built

Migration 054 rebuilds `known_issues`, keeping `MIN(id)` per
`(COALESCE(make,''), COALESCE(model,''), title)` and adding a UNIQUE expression
index on the same key. Verified through the project's own migration runner on a
copy of the live database, not just raw `executescript`: version 53 → 54
recorded, 6,600 → 660 rows, all three indexes present, and a duplicate insert
now raises `IntegrityError`.

The rebuild re-declares `idx_known_issues_sort` in its Phase 240C **expression**
form. Recreating the older `severity DESC` form would have undone migration 053
without any error, because SQLite only uses an expression index when the ORDER
BY expression matches it. `EXPLAIN QUERY PLAN` is asserted, not assumed:
`SCAN known_issues USING INDEX idx_known_issues_sort`.

**The regression came back red with nine failures, and one was a real bug.**
The plan called for `INSERT OR IGNORE`. That suppresses every constraint
violation, CHECK included — so a typo in `source` would have been dropped in
silence instead of raising, losing a row and its provenance without a signal.
Two guards from other phases caught it: `test_the_check_rejects_a_typo` in
Phase 211 and Phase 235B, both written for unrelated reasons.

**This phase's own 21 guards did not catch it.** They tested uniqueness
thoroughly and never the interaction with a neighbouring constraint. That is
the finding worth carrying: **idempotency and integrity are different
properties, and the cheapest way to get the first silently costs the second.**
`INSERT OR IGNORE` reads as "skip duplicates" and means "skip anything the
database objects to" — a distinction invisible in any test that only inserts
valid rows, which was every test written here. Now `ON CONFLICT DO NOTHING`,
with four guards pinning the difference and a mutation confirming they fire.

**A fourth mention-versus-use failure.** One of those new guards asserted that
`INSERT OR IGNORE` does not appear in the source, and fired on the comment
written to explain why it is not used. Repaired the same structural way as the
SafetyChecker tripwire earlier today: read string constants out of the AST,
where comments do not exist. Four instances in one session is no longer bad
luck — **this codebase's guards routinely match source text, and any guard that
matches an identifier as text will eventually fire on the prose explaining
it.** Worth its own sweep.

**One bug caught by inspection rather than by a guard.** Made idempotent, the
loader still counted items walked rather than rows inserted, so a repeat load
reported the file's full length. A re-seed announcing "970 inserted" while
inserting nothing would have been indistinguishable from success. It now
measures the table before and after.

Four schema-version contract pins updated — Gates 9, 11, 12, Phase 191B. They
behaved exactly as designed, stopping the bump and demanding confirmation that
a migration accompanied it. F9 lint then caught that this phase's own pin was
missing its `contract-pin` marker.

Regression **6161 passed / 0 failed**.

**Not done, deliberately: the re-seed.** The database holds 660 of 970 entries
and five of fourteen makes. Loading the rest is now safe and idempotent, but it
changes the operator's data and is theirs to run.
