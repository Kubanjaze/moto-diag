# Phase 373 — Warranty work on the invoice (F188) — phase log

**Status:** 🚧 In progress
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
