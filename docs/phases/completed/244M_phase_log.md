# Phase 244M — The shop remembers the machine — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10

---

## 2026-09-10 — Research complete

Three research strands, run on the Track K cadence: refuted by default, primary
sources, unverified kept separate from refuted. Recorded in full at
`docs/phases/_research/244M_memory_research.md`.

Then five load-bearing claims were handed to an adversarial verifier, and
**three came back materially overstated**. That is the part worth recording,
because the corrected versions are what the plan is actually built on:

- The "semantic caches degrade as they grow" claim spliced an ablation table
  onto a growth curve from a different experiment. The paper's own stated
  mechanism is prompt **diversity**, not cache size.
- The 18× contextual-query figure welded together two unrelated experiments —
  and came from a paper benchmarking its own rival at a default it elsewhere
  calls "suboptimal". It does not establish a ceiling on semantic caching.
- The ONC source-attribute requirement is about **access by identified users**,
  not display to end users, and belongs to the evidence-based branch — not the
  predictive one an LLM would fall under.

What survives is narrower and still decisive: **similarity is an unreliable key
for context-dependent questions, and no threshold generalises across corpora.**
Every question this product answers is context-dependent. So the design uses no
similarity matching at all — which means it never needed the numbers that did
not survive.

The other correction that mattered: FDA and ONC are healthcare instruments. A
motorcycle diagnostic tool is neither certified health IT nor a medical device.
They are usable as design analogy and nothing more, and the first summary of
this research came close to treating them as binding.

## 2026-09-10 — Plan v1.0 written

**Step 0 found the blocker, and it is not storage.** Three of the four
substrates this feature needs already exist and are simply unfed:
`ai_response_cache` with a content-addressed SHA256 key and an `offline=True`
mode that already refuses to call the API on a miss; `service_history` with a
repo, a scheduler and a CLI behind it; `FeedbackReader`, which nothing calls.
All three at zero rows.

What is missing is a trustworthy **subject key**. `customers` row 1 is named
`Unassigned`, and all **10 of 10** vehicles carry `customer_id = 1` — the
column default, never overwritten. `customer_bikes`, the junction meant for
this, is empty. On the one session where both keys are set they disagree.

Compiling "per customer" against that produces a single memory belonging to
`Unassigned` that contains every bike in the shop — the exact cross-
contamination the feature exists to prevent, arriving on day one wearing the
feature's name. So **the subject is the vehicle**, and customer becomes a
derived grouping over vehicles. That is also the right answer independent of
the sentinel: machines outlive ownership, and a diagnostic history is
continuous across a sale.

**The erase path ships in this phase.** California BAR's mandated retention set
is invoices, estimates and work orders — a compiled memory is not in it and has
no retention justification. CCPA makes "inferences drawn to create a profile"
deletable, which is precisely what a compile pass emits. And the FTC remedy for
"compiles everything, forever" has twice been destruction of the work product.
A store without an erase path is the defect, not a later feature.

**Rows, never weights.** No fine-tuning on customer data. Deleting a row is
solved; unlearning a fine-tune is, per ICO, "theoretical application and not
any current practical usage".

**The hive mind is Phase 244O, and not for reasons of size.** GDPR Art. 28(10)
makes a processor that sets its own purposes a **controller**; CCPA's service
provider carve-out permits self-improvement only "provided that the service
provider does not use the personal information to perform services on behalf of
another person" — which is the definition of what was asked for. It is a status
change, not a privacy technique, so no amount of hashing or noise reaches it.
It needs a separately built and separately governed artifact, its own lawful
basis, and disclosure taken up front. The one piece of good news is that the
control point already exists: `known_issues.source` maps almost exactly onto
shareability, with `mechanic-verified` marking the shop's own labour — the
competitively significant asset. Fourth time this session that reading for
what exists beat building something.

**Fifth instance of the integration-gap family** recorded on the way past:
`FeedbackReader` is implemented, tested, and called by nothing.

**The roadmap already had this, and one row of it is wrong.** Rows 318, 320,
321, 324 and 326 cover what was asked for — 321 is the hive mind almost
verbatim ("identify *same model same issue* at scale"). But **326 specified
"automated model fine-tuning from accumulated diagnostic feedback"**, which is
precisely the approach the research rules out: weights are where a deletion
request stops being routine. Proposing 326 be rewritten to rows-not-weights,
and leaving the call to the operator.

Also: Phase 245 is taken (Damon HyperSport), so this is filed 244M. The
letter-suffix series has so far been defects-found-while-building and this is
a feature, so the label fits badly; renumbering into Track N at 318 would cost
nothing. Flagged rather than decided.

## 2026-09-10 — Build complete

**76 guards, 6 mutations, schema v57 → v58.** Regression numbers below.

**The defect worth the phase was found by running it, not by reading it.**

Compiling against a copy of the real database returned 31 facts across 10
machines. Vehicle 10 — session 6's CBR600F4i, the bike with the oil leak — came
back with eleven, and **ten of them were paragraphs of the vision model's own
prose from a single sweep.** All ten were about to be injected into the next
sweep's prompt under the header *"Known history for this machine"*.

That is a loop with no brake in it. An early wrong reading returns as context,
biases the next analysis toward itself, and gets written back looking more
established each time. The provenance label does not rescue it: a label lets a
*person* weigh a claim, and this phase's own research measured that most people
never check. A model cannot discount its own prior output at all.

Nothing was wrong by its own terms. The compile faithfully recorded what the
product had recorded; recall faithfully returned it. **The defect exists only at
the join, and only against real data** — a hand-written fixture would have had a
sensible mix of human and machine facts and shown nothing. `recall_summary` now
excludes `model-generated` facts from the prompt path, filtering *before* the
limit so a chatty sweep cannot crowd out the one complaint that matters. `show`
and `ask` still surface them to a person, with the label, which is what labels
are for.

**A guard was vacuous, and its name is what hid it.**
`test_every_answer_line_is_dated_and_sourced` asserted only the source; the name
promised both. A mutation stripping the vintage out of every answer line passed
it cleanly. Its sibling tested `"20" in line`, which any subject containing "20"
would satisfy. Both now match against the facts' real dates. Sixth instance of
this family in one session.

**And one mutation run was itself mis-targeted.** The `-k` filter for the
vintage mutation selected the *answers* guard rather than the *recall* guard, so
the first run reported a pass that meant nothing. Worth recording because the
failure mode is invisible: a mutation that selects the wrong test looks exactly
like a mutation the suite caught. Re-run against both paths separately.

**Step 0's prediction held.** The subject is the vehicle, not the customer, and
`memory stats` against real data reported **10 of 10 vehicles still owned by the
`Unassigned` sentinel** — which is why `forget --customer 1` refuses rather than
deleting the entire shop's memory under one person's erasure request.

Seven `SCHEMA_VERSION` pins bumped 57 → 58 across Gate 9, Gate 11, Gate 12 and
four phase files. That lockstep is the design — a schema change has to be
acknowledged by every gate — and it costs seven edits per migration.

**Status:** ✅ Complete

## 2026-09-10 — Roadmap row 326 rewritten

The operator took the decision the plan left open. Row 326 read *"automated
model fine-tuning from accumulated diagnostic feedback"* and now reads
**"accumulate corrections as deletable ROWS, never model weights"**, carrying
the three sources that make the case — EDPB Opinion 28/2024 on data absorbed in
model parameters and a regulator's power to order erasure of the model itself,
ICO on machine unlearning being "theoretical application and not any current
practical usage", and the FTC's two model-destruction orders — plus a pointer
at this phase's `memory_facts` as the thing to build on instead. A mechanic's
correction already compiles as a `mechanic-verified` row that recall ranks
above everything else, so the accuracy gain 326 wanted arrives by **retrieval**,
and an erasure request stays a DELETE.

**Row 318 still says "retraining pipeline"** and carries the identical defect.
Deliberately not touched: the instruction was to fix 326, and widening a roadmap
edit past what its owner asked for is how a roadmap stops meaning what they
think it means. Flagged inside 326's own text so it survives this session.

## 2026-09-10 — Roadmap row 318 rewritten

Same defect, same pass. 318 ended *"retraining pipeline"*; it now says the
feedback loop closes **as deletable rows, not as weights**, and defers to 326
for the EDPB / ICO / FTC sources rather than repeating them.

Writing it surfaced something worth more than the correction. **Most of 318
already exists and is unfed.** `diagnostic_feedback` has carried a mechanic's
actual diagnosis, actual fix and notes since Phase 116. `FeedbackReader` in
`feedback/learning_hook.py` exposes `iter_feedback`, `get_accuracy_metrics` and
`get_common_overrides`, and **nothing calls it** — the fifth integration-gap
instance this track, already recorded in this phase's Step 0. And 244M compiles
those rows into `memory_facts` as `mechanic-verified`, which recall ranks above
everything else.

So 318 is not a modelling phase at all. What is actually missing is the
**capture surface**: nothing anywhere asks a mechanic to record what the fault
turned out to be. That is why `diagnostic_feedback` sits at zero rows, why this
phase's most valuable compile path has nothing to compile, and why "the system
learns from mechanics" has never been true. The roadmap row now says that
instead of describing a retraining pipeline for data nobody collects.

## 2026-09-10 — Regression red on one pin, then green

**First run: 1 failed, 6,416 passed.** The failure was
`test_phase191b_serve_migrations.py`, and it was mine — an eighth schema pin I
had not bumped.

Worth recording *why* it was missed. Seven pins are written
`assert SCHEMA_VERSION == 57`; this one is written
`assert get_current_version(db_path) == 57`. I grepped for the first form,
found seven, bumped seven, and believed I was done. **The search matched the
spelling, not the invariant.** That is the same mistake as the mention-vs-use
family this session keeps hitting, wearing different clothes: a grep answers the
question you typed, not the question you meant.

A note now sits inside that pin's own reason string saying it is spelled
differently and will be missed by the obvious search, because the hazard recurs
at every schema bump and the next person will grep exactly as I did.

Editing the line turned up a second, smaller thing: its reason opened *"literal
`52` here is the live SCHEMA_VERSION"* — stale since Phase 240C, three bumps
ago. The number in the assertion had been dutifully maintained; the sentence
explaining the number had not. Corrected.

**Second run: 6,417 passed, 0 failed, 26:24.**
