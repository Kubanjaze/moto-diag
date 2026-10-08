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
