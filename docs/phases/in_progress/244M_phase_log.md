# Phase 244M — The shop remembers the machine — phase log

**Status:** Planned
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
verbatim ("identify *same model same issue* at scale"). But **326 specifies
"automated model fine-tuning from accumulated diagnostic feedback"**, which is
precisely the approach the research rules out: weights are where a deletion
request stops being routine. Proposing 326 be rewritten to rows-not-weights.
Not editing it under this phase — a roadmap change is the operator's call.

Also: Phase 245 is taken (Damon HyperSport), so this is filed 244M. The
letter-suffix series has so far been defects-found-while-building and this is
a feature, so the label fits badly; renumbering into Track N at 318 would cost
nothing. Flagged rather than decided.
