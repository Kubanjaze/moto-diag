# Phase 375 — Warranty deductibles — phase log

**Status:** ✅ Complete (2026-10-07)
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

### 2026-10-07 — v1.0, F196 widened

`375_implementation.md` v1.0, committed and pushed (`436a72b`) before any
code. F196 widened by the operator's addition 3 and closed: bug fix #2
below. libfaketime 0.9.13 was installed with Homebrew to fix the whole
process's clock; its control is in the entry.

### 2026-10-07 — The build

Migration 084, `tax_deductible_rules` (resolve, `deductible-rule set`,
`confirm`, `status`), `warranty add/update --deductible-cents` and `list`,
`claim cover`'s refusal, the invoice, the packet and `claim show`.
373's, 376's and Gate 16's warranties record `--deductible-cents 0`; their
figures, and 376's byte-identical export hash (D4), hold. The third
bug fix (a 376 migration test bound to the head) was found when 084 was
written.

**Decisions taken while building, not stops:**
- **D8. The deductible's lines follow the shop-supplies line,** and the
  supplies percentage is computed before them. Covered work is outside
  the supplies base today, and the deductible is covered work. Test:
  `test_the_customers_own_lines_keep_their_supplies_and_the_deductible_does_not`
  (supplies 750 on the customer's 7500, not on 10000).
- **D9. `shop tax confirm` keeps each deductible reading's notes** after
  its "re-checked at" line. The other rule tables replace theirs, but
  addition 1's open questions must survive a re-check. Mutation T2.
- **D10. The claim's lines are stored net.** `amount_cents` is what the
  claim claims for the line, and `deductible_cents` is the customer's
  share. So 373's claim entries, the export's balance check
  (`export.py:554`) and 376's shortfall invoice and settlement entries
  need no change, and 4A follows from them. Mutation I8 (gross
  `covered_cents`) is red.
- **D11. The deductible's tax is its own rounding,** while the customer's
  invoice is taxed once over all its taxable lines. On an invoice with
  other taxed lines the two can differ by a cent. 376's job shows it: the
  invoice's tax is 211 (6.25 % of 3370), where 156 + 54 = 210. Total tax
  on the repair is then 657 against 656 without a deductible: the rounding
  of two separate computations, as D11's cent in 373. Recorded as a risk.
- **D12. The packet says "the claim asks for nothing"** when the deductible
  is the whole covered work, rather than comparing the warranty's
  deductible with the amount applied, which can be in another currency.
- **D13. The deductible is converted to the invoice's currency** as a flat
  supplies charge is. No test exercises a conversion: no warranty test
  runs in another currency. Recorded as a risk.
- **The guards, both working as documented:**
  - the push guard refused `git commit … && git push` in one command, so
    neither ran, and they were run separately;
  - the edit guard refused `sed -i` on a patch file in the scratchpad
    ("blocked wherever it points"), so the hunk split for bug fix #3 was
    done by a Python script writing only to the scratchpad.

  Neither guard was changed.

**Tests:** `tests/test_phase375_deductibles.py`, 39 tests. 244G's scanner
over all of `tests/`: 0 hits. Its control, a planted `read_text()` of a
`.py` file asserted on, is reported (the first plant read a file without
`.py` and was not, which is the scanner's documented shape). Mutations
are 20/20 red (`375_mutate.out`). The first run was 19/20: I9 survived,
since no test invoiced a claim whose warranty had no deductible on record.
`test_a_claim_covered_before_the_deductible_was_recorded_refuses_the_invoice`
was added, and I9 is now red. `COLLECTED_TEST_FLOOR` 10645 → 10685, by a
diff of collected ids against master `ca8ea1a` in a worktree: +39, and gate
15's `[83]`; none removed.

`wholetree.sh --full`: 4047 passed on the staged build, and again on
`c49db73` (regression.sh refused the staged tree's record, as the memory
on clean-tree records said it would).

### 2026-10-07 — The regression of record

Regression of record: 10685 passed, 0 failed, 0 skipped, 0 errors at `c49db73` (25 min 45 s wall, `python -m pytest -n auto --dist load`, exit 0)

It ran 21:37–22:03 EDT on 2026-10-07: an evening, not a month's last day,
with F196's lines cleared.

### 2026-10-07 — Live

Through the deploy skill, from the branch, after the regression:
- **The scope** (`375_deploy_scope.json`): `schema_version` +1,
  `tax_deductible_rules` +3, two objects added, three tables' SQL changed.
- **The dry run:** exactly that, no existing row changed or removed,
  scope problems none, F158 census 36. Backup
  `~/backups/motodiag/motodiag_pre375_20261007_220325.db`; retain-5
  removed `motodiag_pre370_20261006_110434.db`. Committed `a533a19`.
- **Not a rule-1 stop:** the prompt's scope is new columns, a new table
  and new rule rows after a backup, and the migration's own
  schema_version row. No existing row changed.
- **`apply-live`:** preflight passed. Live now equals the approved exact
  diff: 5866 rows, 121 tables, integrity ok, schema 84, and the three
  readings are valid until 2027-10-07.

No refute pass ran: the phase ships code, tests, three rule rows quoted
from their sources, and a schema migration, not content rows.

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

**Commit.** `83b4834`

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

**Commit.** `23ed8cc`

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

**Commit.** `d5d25e5`
