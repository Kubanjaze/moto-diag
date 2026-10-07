# Phase 373 — Warranty work on the invoice (F188) — phase log

**Status:** ✅ Complete (2026-10-06)
**Branch:** `phase-373` (Opus session, main checkout)

---

### 2026-10-06 — Opened

The operator's prompt is `docs/prompts/373_warranty_work_on_the_invoice.txt`
(merged `4ee55a5`). The last session's state is
`docs/handoffs/2026-10-06_292_closed.md`. Row 373 went 🚧 before Step 0;
`roadmap_check.py` exit 0.

### 2026-10-06 — Step 0, and the stop

`373_step0.md`; the tax sources, quoted, in `373_sources.md`. Every
measured fact in the prompt re-verifies (S0-1), including live at 19:44
on a copy: 0 warranties, 0 claims, 0 invoices, 6 work orders, 0 exports.
The copy also answers 292's open H1 question: no Xero file was ever
written from live.

The prompt asks for a stop at Step 0 with six questions. Question 3 is
also a rule question in its own right: the Massachusetts sources agree the
customer pays no tax on a covered part, and do not settle whether the
claim carries the tax or the shop bears it, for a plan the shop did not
sell (S0-4).

**The edit guard** blocked a shell loop that redirected to `$u.html`: "the
edit guard cannot tell where the redirect `>` `$u.html` writes … Use a
literal path." That is its documented scope. The fetch was rewritten as a
script in the session scratchpad that writes its own files. The guard was
not changed.

Decisions taken without a stop are S0-6 D1–D5.

**The operator's choices, verbatim (2026-10-06):**

> 1a. 2a; for a denied or part-approved claim, the shop decides each time
> (claim settle), with void and regenerate tested unchanged and a second
> invoice allowed only for a settled claim's shortfall. 3: T2, but first
> read the five unread rulings and search DOR directives and TIRs for
> warranty or service contracts; if any contradicts T2, stop and show me
> what it says. 4: new row. 5a. 6: command line only.

### 2026-10-06 — Question 3's further reading, and a second stop

`373_sources.md`, "The operator's further reading": the five unread
rulings, three more rulings and two directives the new searches returned,
and the Division of Insurance's guide. No TIR returned addresses parts
under a warranty or a service contract. LR 83-67 agrees with (5)(g). **LR
85-1 says "Whether an automobile upon which work is performed is under
warranty is irrelevant for sales tax purposes"**, which contradicts T2's
premise on its face, so per the operator's instruction the session stopped
and showed it.

**The operator's answer, verbatim (2026-10-06).** The decision first
arrived as pasted text; the session asked whether it was the operator's
own (rule 1) and named its conflict with LR 03-8. The pasted decision:

> Not (i). (5)(g)'s text covers the service enterprise that is itself the
> party to the service contract ("the service enterprise also agrees to
> supply the necessary parts... for a specified contract price"); a shop
> repairing under someone else's plan isn't that party. Gate 16's job is
> 79-19's own facts (a maker's plan bought through the dealer, paying the
> repair bill), and 79-19 and 85-1 say the parts are taxable whether or
> not covered. So key the rule on who owes the repair: if someone else
> pays (maker's warranty, maker's plan, third-party contract), tax the
> covered parts and add the tax to the claim; if this shop sold the
> service contract itself, the shop bears the tax as the consumer per
> (5)(g), with nothing on the claim. The warranty records which. Store it
> as the jurisdiction rule with all the sources, and put this reasoning in
> the log: it's a reading, to be confirmed by the shop's accountant before
> a real warranty job.

The confirmation:

> yes, mine. (b)

So, (b): a maker's warranty included in the bike's price follows LR 03-8
(no tax, nothing on the claim); someone else's plan or contract has its
covered parts taxed and the tax added to the claim (LR 79-19, LR 85-1); a
contract this shop sold follows (5)(g) (the shop bears the tax as the
consumer, nothing on the claim). **This is a reading of the sources, to
be confirmed by the shop's accountant before a real warranty job.** The
operator's reasoning, as given: (5)(g) speaks of the service enterprise
that is itself the party to the contract; a shop repairing under someone
else's plan is not that party; and the Gate 16 job is 79-19's own facts.

### 2026-10-06 — v1.0

`373_implementation.md` v1.0. Rows 375 (deductibles, the operator's
choice 4) and 376 (claim settlements in the export) added, both 🔲, and
then F190 filed with the finding skill for 376, so the row was in place
before the finding cited it. `finding_check.py` and `roadmap_check.py`
exit 0.

Decisions taken here, not stops, with the reason for each in v1.0's
Decisions: D6, the provider is a name on an A/R line in QuickBooks, not a
new account kind; D7, settlements are not exported (F190); D8, a claim
denied before its invoice is ignored by it.

**The edit guard** refused a command that appended F190 and then ran
`sed -i` on `docs/FOLLOWUPS.md`'s header; the guard refuses the whole
command, so the append did not run either (counted: 0 `### F190` before,
1 after the re-run). `sed -i` is blocked wherever it points: its
documented scope. The header was changed with the Edit tool.

### 2026-10-06 — The build

Migration 081, the warranty's payer (`warranty add --payer`, `warranty
update`), `claim cover`, the invoice reading its claims, the claim's tax
from `tax_warranty_rules`, `claim settle` and the shortfall invoice, the
packet, and the claim in both export files. 274's claim tests moved off
`--claimed-cents` (two tests; the amount claimed now reads "not
recorded" until an invoice derives it). Gate 16 inverted: 87 passed
(80 before).

**Decisions taken while building, not stops:**
- **D9. `warranty set-payer` became `warranty update --payer --provider`.**
  A claim's receivable names the provider, and no command could record a
  provider on a warranty already added: the export's refusal would have
  had no remedy. `claim cover` now requires both on record.
- **D10. A settled claim keeps its lines off the order's invoice
  whatever its status.** Found while writing mutation S2: a denied claim
  settled by billing the customer, then the original invoice voided and
  generated again, would have billed the covered lines a second time
  (once on the shortfall invoice, once on the regenerated one). This was
  the phase's own new code, before any commit, so it is not a register
  entry; the test is
  `test_after_a_settlement_regenerating_does_not_bill_the_covered_lines_again`.
- **D11. A part approval's shortfall is billed with the customer's own
  tax**, recomputed from 281's rules on the day, not the claim's tax in
  proportion. In the test case the provider is 3500 cents short and the
  customer pays 3501 (pre-tax 3426, tax 75): the cent is the rounding of
  two separate tax computations. Recorded in the test's docstring.
- **D12. Gate 16 adds a seventh plant, F188 itself** (the claim priced,
  and the customer still invoiced for every line); the inverted test
  catches it. The Xero tax plant is now checked through job B, because
  job A's customer invoice carries no tax.

**My own arithmetic was wrong once:** the first draft of
`test_a_claim_past_draft_is_not_priced_differently` expected 24250 cents
at 11000 an hour; 1.5 h × 11000 + 8000 + 500 is 25000, which the code
printed. The test was corrected; the code was right.

**244G's scanner** over `tests/`: 0 findings. **209B's integration gaps:**
166 passed; no new module, so no allowlist entry.

### 2026-10-06 — Mutations, the dry run, `--full` and the regression of record

**Mutations:** `373_mutate.py`, 23/23 red: covering (3), the invoice (9),
settlement (5), the export (4), the tax rule (2).

**The build commit** `227915a`, after `wholetree.sh --full` on the staged
tree: 3988 passed in 86 files (13 min 55 s). Gate 16 is not a whole-tree
member (292's note); the regression runs it.

**Migration 081's dry run** (`deploy.py dryrun 373`): live before 5855
rows in 114 tables, integrity ok; backup
`~/backups/motodiag/motodiag_pre373_20261006_210540.db`; on the copy,
`schema_version` +1 and `tax_warranty_rules` +3 (the three Massachusetts
rules), every other table 0 changed and 0 removed; no scope problem; F158
census 36, the same as 273's and 281's. No existing row changes, so the
apply is not a rule-1 stop: new tables, new columns, the migration's own
`schema_version` row and new rows loaded after a backup. The diff is
committed as `4025073`.

`wholetree.sh --full` on `4025073`: 3988 passed (14 min 28 s). Then
`.claude/skills/closeout/regression.sh` on a clean tree:

Regression of record: 10556 passed, 0 failed, 0 skipped, 0 errors at `4025073` (31 min 30 s wall, `python -m pytest -n auto --dist load`, exit 0)

No refute pass ran.

### 2026-10-06 — Migration 081: live

`deploy.py apply-live 373`, from the branch before the close-out commit,
as 273 did: `apply-live` reads the scope and the diff from
`in_progress/`, so they were moved to `completed/` after it. Preflight
passed; applied `[81]`; after (live): 5859 rows, 117 tables, integrity
ok; scope problems none; **`373_live_diff.md`: equals the approved exact
diff: yes**; F158 census on live 36. Read afterwards on a copy made
through SQLite's backup API from a read-only connection: schema 81;
`foreign_key_check` empty; warranties 0, claims 0, claim lines 0,
invoices 0, export claims 0, work orders 6; the three warranty rules
(`maker_with_bike` 0 stated, `other` 1 reading, `shop_contract` 0
stated).

### 2026-10-06 — Close-out

v1.1 written, no open boxes. F188 marked closed in `docs/FOLLOWUPS.md`.
Row 373 ✅, `**CLOSED 2026-10-06.**`, with the regression line; the
history row and version header in `implementation.md`; the documents and
the deploy scope, dry-run diff and mutation file moved to `completed/`;
handoff `docs/handoffs/2026-10-06_373_closed.md`.

## Bug-fix register

### Bug fix #1 — 2026-10-06 — 274's migration test read every later column as a change

- **Issue:** with migration 081 in the tree,
  `tests/test_phase274_migration.py::TestMigration076::test_existing_rows_are_unchanged_either_way`
  failed: `AssertionError: warranties`, the row after the migrations
  carrying one more value (`None`) than before.
- **Root cause:** the test rolls back to 075, inserts rows, applies every
  pending migration, and compares `SELECT *` before and after. Any later
  migration that adds a column to a watched table (081 adds
  `warranties.repair_payer`) changes the row's width without changing a
  value 076 found. The forward-compat family: a schema assertion pinned to
  the head as it stood.
- **Fix:** compare the columns 076 found (`as_found`): each row cut to the
  width it had before. A changed value in those columns still fails; the
  rollback half still compares whole rows.
- **Files:** `tests/test_phase274_migration.py`.
- **Verified:** red before the fix with 081 present (the failure above);
  green after, 10 passed in `test_phase274_migration.py`.

**Commit.** `c5d5215`
