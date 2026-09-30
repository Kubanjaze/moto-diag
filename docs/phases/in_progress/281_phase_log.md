# Phase 281 — Track O batch 3: recalls, VIN decoding, tax rates and exchange rates — phase log

**Status:** 🚧 In progress
**Branch:** `phase-281` (Opus session, main checkout, the only writer)

---

### 2026-09-30 — Opened: Track O batch 3

The prompt is `docs/prompts/281_track_o_batch3.txt` (merged in
`5cde0c3`). The operator's words it carries, verbatim:

> 1, 2, 3, 5 as recommended.

> 4: check row 288 — which jurisdiction does it name, and where is the first real shop? tax follows the shop. if it's MA (flat statewide), start there, not CA. either way: every rate stored with its effective date and source, and a check that fails when a rate is past its stated validity.

> note for the batch 3 prompt when you write it: first outbound calls in the app. tests use recorded fixtures, never live endpoints; the app degrades cleanly when a service is down (shown to the user, never silently empty); no live API call during the build except one smoke call per service, logged.

> i will be in MA and i mean, i intend to be in all 50 states or wherever they can download it , idk how that would work

> we will just wait until it reports and then go with whats recommended based on that

Batch 3 is rows 281 (NHTSA recall refresh), 287 (VIN decoder), 288 (tax
rates) and 289 (exchange rates). The tax plan the operator accepted: a
model not tied to one state or country; Massachusetts shipped verified
from the Department of Revenue's own text; every other shop enters its
own rate with its source and effective date; a check fails once a rate is
past its stated validity; automatic rates for every address paused.

Read first: the 275 handoff (`docs/handoffs/2026-09-30_275_closed.md`),
the triage report (`docs/reports/2026-09-28_track_o_triage.md`), rows
281, 287, 288 and 289, and 275's documents in `docs/phases/completed/`.

The first commit: **row 281 🚧**, carrying the batch.

### 2026-09-30 — Step 0, and the stop

`281_step0.md`; the regulators' and services' pages, quoted with URLs and
dates, in `281_sources.md`. No service API was called. What it found:
- **Every measured fact in the prompt holds** (S0-1). Two more: no live
  bike has a VIN, and 36 test calls rely on the zero default.
- **F184 filed** with the `finding` skill (`next_f_number.sh`: F183 in
  this file, F181 in the mobile file): the zero tax default.
- **Two corrections** (S0-2): these are not the app's first outbound
  calls (push, the AI SDKs and Stripe already call out), but the first to
  public data services; and **F103**, filed by Phase 251 in the mobile
  file, is a binding constraint on any recall sync. Its requirements are
  met by the design in S0-4 and S0-5; it is closed in the mobile session.
- **Massachusetts:** 6.25% on parts, effective 2009-08-01 (the DOR guide,
  TIR 09-11); labour and a diagnostic fee not taxable (830 CMR
  64H.1.1(2)(a)1, (5)(a)); **no DOR page names a shop-supplies charge**, so
  none is shipped and a Massachusetts shop records its own rule. No page
  states a validity for the rate.
- **The ECB's page says its rates are "for information purposes only.
  Using the rates for transaction purposes is strongly discouraged."**
- **How the pages were read:** nhtsa.gov and mass.gov refuse curl (403,
  with or without a browser User-Agent). mass.gov was read with headless
  Chrome's `--dump-dom`; nhtsa.gov refused that too, so NHTSA's recall
  service is described from this project's own recorded responses
  (`~/research/motodiag/`, 2026-09-20) and F103. macOS has no `timeout`,
  so Chrome ran under `perl -e 'alarm 60; exec @ARGV'`; no Chrome process
  was left running.
- **The edit guard blocked one command:** a loop writing
  `> $n.dom.html`, a redirect to a path held in a variable. It was redone
  with literal paths. The guard was right to refuse what it cannot
  resolve, and was not loosened.

Decided (with the reasons in `281_step0.md`): stdlib `urllib` and one
outbound module; a network guard in `conftest.py`; recalls refreshed only
on request and stored with their fetch; severity only from NHTSA's own
park flags, else "not rated"; no green all-clear from zero results; VIN
decodes stored per VIN; a shop's jurisdiction in its own table, so
`shops` is not altered; the invoice records its rate and source.

The ledger, in this commit:
- **Rows 367 and 368 ⏸️**, split from 281 (recall reimbursement claims)
  and 288 (automatic rates for every address), each with its reason. The
  numbers were free: no row in either ROADMAP, no phase document and no
  handoff names them; the same search finds row 366 in three documents.
- The header reads 368 numbered.
- Rows 281, 287, 288 and 289 are rewritten after the operator's answers,
  since question 3 decides what 289 builds.

**Stopped for the operator (rule 1: real forks and new thresholds).**
Four items in `281_step0.md` ("Questions for the operator"): (1) the
invoice API's `tax_rate`: remove, required, optional, or unchanged; (2)
the validity windows no source states: Massachusetts's rate (12 months
from the last check proposed) and the ECB's rates (through the 4th day
proposed); (3) whether ECB rates may convert an invoice; (4) a note with
a default: no app route for VIN decoding or recalls.

### 2026-09-30 — The operator's pick, F185, and v1.0

The operator's answer, pasted into the session as one block, verbatim:

> 1: A. Also file a finding: with the field gone, a tax-exempt sale (a resale or exempt-organization certificate, for example a town's police bikes) can't be invoiced. It waits until a real shop needs it.
> 2(a): 12 months, as proposed, and every invoice and `tax status` print the date the rate must be re-checked by.
> 2(b): through the 5th calendar day, not the 4th. After Easter the next ECB rate comes out Tuesday at 16:00 CET, which is Tuesday morning in Massachusetts and the 5th day after Thursday's rate.
> 3: A.
> 4: no route, as the default.
> The diagnostic-fee rule is the build's own reading, not a stated rule. Ship it with that said in its source, so `tax status` shows it as a reading of 64H.1.1(2)(a)1.

- **2(b) corrects Step 0's arithmetic.** Thursday's rate; Good Friday
  and Easter Monday are TARGET closing days; the next rate is Tuesday
  16:00 CET, 10:00 in Massachusetts (EDT), day 5 after Thursday. So an
  ECB rate is valid through `rate_date + 5 days`.
- **F185 filed** with the `finding` skill (`next_f_number.sh`: F184 here,
  F181 in the mobile file): a tax-exempt sale cannot be invoiced once
  tax comes only from the record. Not fixed in this batch, as asked.
- **The diagnostic rule** carries `basis = 'reading'` and its clause, and
  `tax status` prints it as a reading of 64H.1.1(2)(a)1.
- Rows 281, 287, 288 and 289 are rewritten to what the batch builds.

v1.0 is `281_implementation.md`.
