# Phase 375 — Warranty deductibles — phase log

**Status:** 🚧 Step 0, stopped for the operator (2026-10-07)
**Branch:** `phase-375` (Opus session, main checkout)

---

### 2026-10-07 — Opened

The operator's prompt is `docs/prompts/375_warranty_deductibles.txt`
(merged `ca8ea1a`). The last session's state is
`docs/handoffs/2026-10-07_376_closed.md`. Row 375 went 🚧 before Step 0
(`4f8a3e6`); `roadmap_check.py` exit 0; `wholetree.sh` fast mode, 1582
passed, exit 0.

### 2026-10-07 — Step 0, and the stop

`375_step0.md`; the sources, quoted, in `375_sources.md`. Every measured
fact in the prompt re-verifies (S0-1), including live at 19:54 EDT on a
copy: 0 warranties, claims and claim lines; 3 warranty rules; 1
settlement rule; schema 83.

**The sources.** Three searches restricted to mass.gov; six pages read
(79-19 and 03-8 again, 830 CMR 64H.1.1, 80-17, 85-8, and the Division of
Insurance's service-contracts page). No source rules on a warranty
deductible by name. 79-19's ruling 3 holds the tax on covered parts whole
"whether or not the charges are partially or fully covered", on facts
that include a deductible. 03-8's no-tax is conditioned on "no
additional consideration from the retail customer". 85-8 taxes an
unsplit charge whole. G.L. c. 64H § 1 is blocked ("Socket is closed"),
as § 33 was for 376.

The pages were read directly in this session, not through Subconscious:
six pages whose passages had to be quoted exactly is not bulk reading
(rule 2), which is how 373 and 376 read theirs.

**zsh** did not split `$F` holding a command and its arguments ("no such
file or directory"); the fetches were re-run through a shell function.
Not a defect.

The prompt asks for a stop at Step 0 with four questions. Q2 is also a
rule question in its own right: the tax on a deductible is a reading of
sources that do not name it.

Committing Step 0 found F196 (fast mode red at 20:01 EDT on a docs-only
commit). Its fix went first, in its own commit (`83b4834`); the register
entry is below.

**The operator's choices, verbatim (2026-10-07).** The decision arrived as
pasted text; the session asked whether it was the operator's own (rule 1),
and the operator answered "Yes, mine; apply it".

> 1A, 2A, 3A, 4A. Three additions:
> - Each tax_deductible_rules row's notes say what its sources leave open,
>   for the accountant: 03-8's condition for the maker's warranty; for a
>   shop contract, whether a deductible is a "separate charge" under
>   (5)(g), and 80-17's adjustment.
> - The handoff names what 1A and 2A leave out: a plan whose deductible is
>   per visit, or includes tax.
> - F196's search missed two month-based lines: test_phase274_pnl.py:23
>   (MONTH) and test_phase281_intake_month.py:35 (the first of the month).
>   Widen it to every test that turns the real clock into a day or month (I
>   count 7 lines in 4 files on phase-375), and check each at 21:00 EDT on a
>   month's last day with a fixed clock. Fix any that fails the way bug fix
>   #1 did, or leave F196 open naming it.
> Carry on to v1.0 and the build.

## Bug-fix register

### Bug fix #1 — 2026-10-07

- **Issue:** `wholetree.sh` fast mode went red at 20:01 EDT on the Step 0
  commit, which was docs only:
  `test_phase275_accounting_export.py::TestQuickBooksOnline::test_an_invoice_made_by_the_invoice_command_exports`,
  "no invoices to export for shop id=1 from 2026-10-08 to 2026-10-08".
  Filed as F196 with the finding skill before this entry cited it.
- **Root cause:** the test takes the export's range from
  `datetime.now(timezone.utc).date()`. Since 377 the export selects by the
  shop's day, which after 20:00 EDT is a day behind UTC. The opening
  commit's fast run at 19:5x passed 1582 tests; the same test failed at
  20:01.
- **Fix:** the test exports the shop's day of the invoice's own
  `issued_at` (`core.timestamps.local_day`), so it reads no clock to
  choose the range. The `datetime` import it no longer uses is removed.
- **Files:** `tests/test_phase275_accounting_export.py`;
  `docs/FOLLOWUPS.md` (F196).
- **Verified:** at 20:02 EDT, in the window that failed, the file gives
  19 passed. The control is the red at 20:01 on the old line, in the same
  window. The search for the pattern (F196) found 5 lines in 3 files;
  the other two files pass in the window (70 passed with this file
  before the fix, 1 failed).
- **Commit:** this entry's own commit.

### Bug fix #2 — 2026-10-07

- **Issue:** F196 widened (the operator's addition 3). At 2026-10-31
  21:00 EDT, with the whole process's clock fixed, 8 tests of
  `tests/test_phase274_pnl.py` fail, for example
  `TestShopNet::test_net_subtracts_the_months_expenses`: `assert {} ==
  {'shop': (49000, 5400, 13000, 30600)}`.
- **Root cause:** `MONTH` and `TODAY` are the UTC clock's month and day
  (`2026-11` at that moment). Since 377 the P&L counts the shop's month,
  which is still `2026-10`, so the report the test asks for is empty. It is
  the same family as bug fix #1: the real clock turned into a UTC day.
- **Fix:** `TODAY` is the shop's day of now (`core.timestamps.local_day`)
  and `MONTH` its first seven characters. The test still runs on today's
  date, because the fixture's invoices are generated now; it no longer
  reads a different calendar from the report.
- **Files:** `tests/test_phase274_pnl.py`; `docs/FOLLOWUPS.md` (F196).
- **Verified:** the method is libfaketime 0.9.13 (Homebrew), `TZ=America/New_York
  faketime '<moment>'`. Its control: Python's local and UTC clocks,
  `date.today()` and SQLite's `datetime('now')` all read the faked moment.
  The census's six files plus 275's give 8 failed, 129 passed at
  2026-10-31 21:00 before the fix, and 137 passed after it at that moment,
  at 2026-10-07 21:00, at 2026-12-31 21:00 (the year line) and at
  2026-11-01 00:30.
- **Commit:** this entry's own commit.

### Bug fix #3 — 2026-10-07

- **Issue:** with migration 084 written, 376's
  `TestMigration083::test_only_the_two_rebuilt_tables_change_and_no_row_moves`
  fails: `warranties`, `warranty_claims` and `warranty_claim_lines` show
  as changed by "083".
- **Root cause:** the test rolls back to 82 and then applies every pending
  migration, so it measures 083 and every later migration together. That
  is the same family as 373's bug fix #1 (274's migration test), the
  working rule "a rollback peels every successor" read the other way.
- **Fix:** the test applies 083 alone (`apply_migration(get_migration_by_version(83))`).
- **The third bug, and the shared cause (the working rule).**
  - #1 and #2 share one cause, a test turning the real clock into a UTC
    day or month. They were searched by a rule and checked under a fixed
    clock (F196, closed).
  - #3 is another family. Its census: 22 test files call
    `rollback_to_version` and `apply_pending_migrations`. Run with 084 in
    place, 784 tests pass and only this one fails, so no other migration
    test is bound to the head.
- **Files:** `tests/test_phase376_settlement_export.py` (the two 083
  hunks only; the `--deductible-cents 0` hunk goes with the build).
- **Verified:** the 083 tests give 3 passed with 084 present. Before the
  fix, 1 failed.
- **Commit:** this entry's own commit.
