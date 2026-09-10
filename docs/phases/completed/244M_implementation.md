# Phase 244M — The shop remembers the machine

**Version:** 1.1 | **Tier:** Large | **Date:** 2026-09-10 (built 2026-09-10)

---

## Goal

The operator asked for two things:

> "each customer/client having a long term memory compiling every interaction
> to build its own database to be able to answer inquiries without even using
> the api, and then on the macro level there would be a higher repository that
> functioned like a hive mind"

Layer (a) is a per-client long-term memory that answers without an API call.
Layer (b) is a cross-shop repository. **This phase builds layer (a) and the
erase path that has to exist alongside it.** Layer (b) is Phase 244O, and the
reason it is a separate phase is in *Cross-tenant is a status change* below —
it is not a deferral for size, it is a different legal posture that needs its
own artifact and its own disclosure.

## Step 0 — what already exists, and the one thing that does not

Six findings, in descending order of how much they change the plan.

**S0-1. The ownership key is a sentinel, so there is no "per-customer" to
compile against today.** `customers` row 1 is literally named `Unassigned`.
All **10 of 10** vehicles carry `customer_id = 1` — the column's `DEFAULT`,
never overwritten. `customer_bikes`, the junction the schema intends for this,
has **0 rows**. And on the single session where both keys are set they
disagree: `diagnostic_sessions[1].customer_id = 2` (Dana Reyes) while its
`vehicles[1].customer_id = 1`. Migration 046 already encodes the convention —
`test_backfill_takes_the_vehicle_customer_but_skips_the_sentinel` — so the
sentinel is known and deliberate, not rot.

> Compiling "per customer" on this key produces **one** memory belonging to
> `Unassigned` containing every bike in the shop. That is worse than no
> feature: it is exactly the cross-contamination the whole design exists to
> prevent, arriving on day one under the name of the feature.

**S0-2. An exact-match response cache already exists, is wired, and already
implements "answer with no API call".** `engine/cache.py` +
`ai_response_cache`, keyed by SHA256 over `kind|canonical-JSON-payload` —
content-addressed, not similarity. `DiagnosticClient.ask()` takes
`offline: bool`, and on a cache miss with `offline=True` it *raises* rather
than calling the API. The operator's "without even using the api" has a
mechanism already; what it lacks is coverage and a subject.

**S0-3. The vision path deliberately bypasses that cache, with a recorded
reason.** `ask_with_images` — the method `/ask` and the sweep both run
through — documents that image-cache keys would have to hash each frame's
bytes, "potentially expensive for 60-frame batches", and defers it. So the
expensive path, the one the operator is watching the cost of, has no reuse at
all. That is Phase 244N, not this one.

**S0-4. `ai_response_cache` has 0 rows.** Same shape as `cost_events` at 244L:
wired, never exercised. Before building on it, 244N must establish that the
existing path actually writes — a cache with a silent write failure looks
identical to a cache that is merely cold.

**S0-5. `FeedbackReader` exists and nothing calls it.** `feedback/learning_hook.py`
exposes `iter_feedback`, `get_accuracy_metrics`, `get_common_overrides`;
the only importer is its own package `__init__`. The integration-gap family
again, fifth instance this track. And `diagnostic_feedback` has **0 rows** —
so the mechanic corrections that research C12 identifies as the crown-jewel
asset **do not exist yet**. The memory's highest-value input is empty.

**S0-6. `service_history` is the per-vehicle event log the product already
models — with 0 rows.** A `CHECK`-constrained `event_type`, mileage, date,
mechanic, parts. It has repo + scheduler + CLI behind it (`advanced/history_repo.py`)
and nothing populates it from the diagnostic flow.

**Net:** three of the four substrates this feature needs are already built and
unfed. The missing piece is not storage. It is (i) a trustworthy subject key
and (ii) a compile pass that turns interactions into retrievable facts.

## What the research changed

Full record: `docs/phases/_research/244M_memory_research.md`. Five load-bearing
claims were adversarially re-checked and **three came back materially
overstated**; the corrections are what drive these decisions.

- **No semantic-similarity matching, anywhere in this phase.** What survived
  verification is narrow but decisive: similarity is an unreliable key for
  *context-dependent* questions, and no threshold generalises across corpora.
  Every question this product answers is context-dependent — "why is it running
  lean" is meaningless without the bike, the mileage and the last repair. What
  did **not** survive is the general "caches degrade as they grow" claim (V1:
  the paper's mechanism is prompt *diversity*, not size) and the 18× contextual
  figure (V2: two unrelated experiments welded together, in a paper grading its
  own rival). We are not entitled to those numbers, and we do not need them —
  the design avoids similarity keys regardless.
- **Rows, never weights.** No fine-tuning, no embedding the memory into model
  parameters. EDPB 28/2024 holds that personal data may remain absorbed in
  parameters and that a regulator may order erasure of the *model*; ICO puts
  machine unlearning at "theoretical application and not any current practical
  usage". Deleting a row is solved. Unlearning a fine-tune is not.
- **The erase path ships in this phase, not after it.** California BAR's
  mandated retention set (16 CCR § 3358) is invoices, estimates and work
  orders — the compiled memory is **not** in it and therefore has no retention
  justification. CCPA § 1798.140(v)(1)(K) makes "inferences drawn to create a
  profile" deletable personal information, which is precisely what a compile
  pass produces. And FTC *Everalbum* / *WW-Kurbo* show the remedy for
  "compiles everything, forever" is destruction plus a forward-looking cap.
  A memory store without an erase path is the defect, not a later feature.
- **Vintage is displayed, and provenance is not decoration.** N=303: citations
  raised trust *even when random*; only 9.77% of cited answers were ever
  checked at the answer level. A `machine_specific` badge on a stale fact buys
  unearned trust from nearly everyone. Every recalled fact carries
  `established_at` and its source, and a fact whose basis has been superseded
  is not returned as current.
- **FDA and ONC are design analogy only.** Both are healthcare instruments —
  certified health IT, and the medical-device definition. A motorcycle
  diagnostic tool is neither, and treating them as binding would be a category
  error (V6). They inform the shape (show the vintage, keep the basis
  reviewable); they impose nothing.

**Cross-tenant is a status change, not a privacy technique.** GDPR Art. 28(10):
a processor that determines its own purposes "shall be considered to be a
controller". CCPA 11 CCR § 7050(a)(3) permits a service provider to improve its
services "provided that the service provider does not use the personal
information to perform services on behalf of another person" — which is the
definition of a hive mind. No hashing, pseudonymisation or noise changes this,
because it is about who decides the purpose. So layer (b) must be a separately
built, separately governed artifact with the vendor openly the controller, its
own lawful basis, and disclosure taken **up front** (FTC flags retroactive
widening specifically). It cannot be this phase's index with its filters
relaxed — and it is not something to reach by accident from here.

## The roadmap already schedules this, and one of its rows is wrong

**This feature is not new to the plan of record.** `docs/ROADMAP.md` carries it
spread across Track N:

| row | as written |
|---|---|
| 318 | Human-in-the-loop learning — "mechanic overrides train the system… retraining pipeline" |
| 320 | Predictive maintenance expansion — "per-customer… failure prediction" |
| 321 | Fleet anomaly detection — "cross-bike pattern recognition, identify *same model same issue* at scale" |
| 324 | Repair success prediction — "will this fix work for this bike?" |
| 326 | Continuous learning pipeline — "**automated model fine-tuning** from accumulated diagnostic feedback" |

Row **321 is the hive mind** in the operator's words, and row **326 specified
fine-tuning** — the one implementation the research argues hardest against.
Weights are where a deletion request stops being routine: EDPB 28/2024 holds
personal data may remain absorbed in model parameters and that a regulator may
order erasure of the model itself, ICO puts unlearning at "theoretical
application", and the FTC has twice ordered model destruction.

**Row 326 has now been rewritten to rows-not-weights.** The plan proposed it and
left the decision to the operator, who took it; the edit landed under this
phase. Row 326 now points at `memory_facts` — a mechanic's correction compiles
as a `mechanic-verified` row that recall already ranks above everything else, so
accuracy improves by retrieval and an erasure request stays a DELETE.

**Row 318 carried the identical defect** — it ended "retraining pipeline" — and
was rewritten in the same pass once the operator asked for it. Its new text says
something 326's does not: **most of 318 already exists and is unfed.**
`diagnostic_feedback` has held a mechanic's actual diagnosis, actual fix and
notes since Phase 116; `FeedbackReader` exposes three read methods and is called
by nothing; and this phase compiles those rows as `mechanic-verified`, the top
of recall's ranking. What is genuinely missing is the **capture surface** —
nothing anywhere prompts a mechanic to record what the fault turned out to be,
which is why the table sits at zero rows and the most valuable input the corpus
could have does not exist.

**On the number.** Phase 245 is already taken — Damon HyperSport/HyperFighter.
This is filed as 244M because the letter-suffix series is this roadmap's only
insertion mechanism, but 244A–244L were all *defects found while building* and
this is a *feature*, so the label is a poor fit. Nothing in this document
depends on it: renumbering into Track N at 318 needs no content change, and is
arguably the more honest home. Flagged as an operator decision.

## Non-goals

- **No cross-shop or cross-customer sharing of anything.** Phase 244O.
- **No caching of vision answers.** Phase 244N, gated on S0-4 first.
- **No embeddings, no vector store, no similarity thresholds.**
- **No fine-tuning or model adaptation on customer data.**
- **No technician monitoring.** Recording staff raises consent, works-council
  and two-party-consent wiretap questions that are wholly separate from
  customer privacy, and the research explicitly could not establish them.
  Nothing in this phase records or profiles a technician.
- **No retention timer yet.** The cap is a product decision; this phase ships
  the erase mechanism the cap will eventually drive.

## CLI

```
motodiag memory attach --vehicle N --customer M     # establish real ownership
motodiag memory compile [--vehicle N] [--since D]   # idempotent
motodiag memory show --vehicle N [--as-of DATE]
motodiag memory ask --vehicle N "what was done to it"
motodiag memory forget --customer M [--dry-run]
motodiag memory stats
```

## Outputs

- `memory_facts` rows, one per established fact, with provenance and vintage.
- `memory show` — a dated, sourced fact list for one machine.
- `memory ask` — a deterministic answer with zero token spend, or an explicit
  "not in memory" that names what would be needed. Never a guess.
- `memory forget --dry-run` — the exact rows an erasure request would remove.

## Logic

**The subject is the vehicle, not the customer.** A machine is the stable
subject of diagnostic memory: bikes get sold, and the machine's history is
continuous across that. Keying on `vehicle_id` also steps around S0-1 entirely
— all 10 vehicle rows are real and distinct, while the customer key is 100%
sentinel. Customer becomes a *derived grouping over* vehicles, which is exactly
what an erasure request needs (`customer → vehicles → facts`) and nothing else
depends on.

**Migration 058 — `memory_facts`.**

| column | note |
|---|---|
| `vehicle_id` | FK, `ON DELETE CASCADE` — the memory of a deleted machine goes with it |
| `fact_kind` | CHECK: `complaint`, `observation`, `repair`, `part-replaced`, `measurement`, `correction` |
| `subject` / `value` | the fact itself, normalised |
| `source` | CHECK, reusing the corpus vocabulary: `mechanic-verified`, `model-generated`, `customer-reported`, `service-record` |
| `origin_table` / `origin_id` | the row this was compiled from — auditable, and the join that makes recompilation idempotent |
| `established_at` | vintage. Displayed, never inferred from `created_at` |
| `superseded_at` | nullable; supersession rather than mutation |
| `fact_key` | SHA256 over (vehicle, kind, subject, origin) — `UNIQUE`, and the reason a re-compile inserts nothing |

Two SQLite specifics this codebase has already been bitten by, both applying
here: `fact_key` must **COALESCE its nullable components**, because NULLs are
DISTINCT in a UNIQUE constraint (Phase 244D); and the idempotency insert uses
`ON CONFLICT DO NOTHING`, **not** `INSERT OR IGNORE`, which also swallows CHECK
violations and would silently drop a typo'd `source` (Phase 235B).

**The compile pass** reads `diagnostic_sessions` (complaint notes),
`analysis_findings` on `videos` (sweep observations), `work_orders` +
`work_order_parts` (repairs and parts), `service_history` and
`diagnostic_feedback` (corrections — empty today per S0-5, and wired anyway so
the first row compiles the moment one exists). It reports **rows inserted, not
items walked** — the Phase 244D loader reported the latter and a re-seed
claimed 970 inserts while inserting nothing.

**Recall feeds the existing `VehicleContext`,** the structure Phase 244C fixed
from a stub. This is the whole payoff: the sweep and `/ask` already accept a
vehicle context and already render it into the prompt. Recall makes that
context carry the machine's actual history instead of just its identity, which
improves the *API* answers as much as it enables the offline ones.
Monotonicity applies — knowing more must never return less.

**As built, the prompt block carries only human-established facts.**
`recall_summary` excludes `model-generated` observations, filtering before the
limit. That was not in the plan; it was forced by the first run against real
data, where ten of vehicle 10's eleven facts were the vision model's own prose
about to be returned to it as history. See Deviation 1. `show` and `ask` are
unfiltered — a person reads the label and weighs it, which is what the label
is for.

**Answering without the API** is deterministic lookup over facts, not reuse of
generated prose. `memory ask` resolves a bounded question grammar — what was
done, when, at what mileage, which parts, what was the last complaint, has this
been seen before — against `memory_facts`, and returns a sourced, dated answer
or an explicit miss. No model, no similarity, no threshold to tune. The class
of question it cannot answer is answered by the API as it is today.

**Erasure** resolves `customer → vehicles → facts` and hard-deletes, with
`--dry-run` printing the exact row set first. A vehicle still owned by the
`Unassigned` sentinel is **not** attributable to a person, and `forget` says so
rather than silently matching every unassigned bike in the shop.

## Key Concepts

- **A default is not a fact.** `customer_id = 1` on every vehicle looks like
  ownership data and is the absence of it. Treating a sentinel as a key is how
  one customer's memory becomes everyone's.
- **The subject of a memory should be the thing that persists.** Machines
  outlive ownership.
- **Deterministic recall beats similarity for context-dependent questions** —
  and it is also the only version of this feature that can state *why* it
  answered what it did.
- **The erase path is part of the store, not a follow-up.** Anything else is
  the posture that attracts the enforcement action.
- **Rows, never weights.** The choice that keeps a deletion request routine.
- **Vintage displayed, because provenance labels earn trust whether or not
  they deserve it.**

## Verification Checklist

- [x] `memory attach` establishes ownership; the sentinel is never written as
      a real owner
- [x] Compile is idempotent — running it twice inserts 0 the second time
- [x] Compile reports rows **inserted**, not items walked
- [x] A fact with a NULL component still dedupes (COALESCE'd `fact_key`)
- [x] A typo'd `source` is **rejected**, not silently dropped
      (`ON CONFLICT DO NOTHING`, not `INSERT OR IGNORE`)
- [x] Recall feeds `VehicleContext` and the sweep prompt shows the history
- [x] Monotonicity: adding a fact never removes one from recall
- [x] `memory ask` answers in-grammar questions with **zero** token spend
      (asserted against the 244L ledger — no `cost_events` row is written)
- [x] `memory ask` returns an explicit miss, never a guess, out of grammar
- [x] Every recalled fact carries `established_at` and `source`
- [x] A superseded fact is not returned as current
- [x] `forget --dry-run` lists exactly what `forget` deletes
- [x] `forget` on a sentinel-owned vehicle refuses and explains
- [x] Deleting a vehicle cascades its facts
- [x] Migration 058 rolls back **without destroying** any pre-existing table
      (the 244L rollback defect, guarded this time from the start)
- [x] Mutation: key the memory on `customer_id` → a guard fails
- [x] Mutation: make `memory ask` call the API → a guard fails
- [x] Mutation: drop `established_at` from recall → a guard fails
- [x] No embedding, vector or similarity call appears anywhere in the phase
- [x] **The prompt block excludes the model's own prior observations** —
      unplanned, found by running it
- [x] Mutation: feed model-generated facts back into the prompt → a guard fails
- [x] Mutation: `INSERT OR IGNORE` instead of `ON CONFLICT` → 3 guards fail
- [x] Mutation: collapse the null-origin sentinel onto id 0 → a guard fails
- [x] Two machines owned by one customer keep separate memories
- [x] Erasing one customer leaves another's memory intact
- [x] `forget` does not touch the mandated records it compiled from
- [x] A missing source table degrades the compile rather than breaking it
- [x] Verified against a **copy** of the real database; production untouched
- [x] Full regression green — **6,417 passed, 0 failed**, 26:24 (first run: 1 failed, the eighth schema pin)

## Risks

- **The memory has almost nothing to compile today.** `service_history`,
  `diagnostic_feedback`, `voice_transcripts` and `extracted_symptoms` are all
  at 0 rows; there are 6 sessions, 5 videos and 6 work orders in total. The
  feature will look thin on this data set and that is not a bug in the feature.
  Mitigation: the checklist asserts *behaviour on seeded fixtures*, and
  `memory stats` reports how much real history exists so the thinness is
  legible rather than mysterious.
- **The corrections that make this valuable do not exist yet.** S0-5. The
  compile path for `diagnostic_feedback` is wired regardless, so value accrues
  from the first correction rather than requiring a later phase — but nothing
  in this phase creates that first correction.
- **A bounded question grammar will be narrower than the operator expects.**
  "Answer inquiries without the api" reads as *any* inquiry; this delivers a
  defined set answered exactly, and everything else falls through to the API
  unchanged. Stated here so it is a known boundary rather than a surprise.
  Widening the grammar is cheap and additive; the alternative — similarity
  matching — is what the research argues against.
- **`vehicles.customer_id` and `diagnostic_sessions.customer_id` disagree.**
  One row today, and they will disagree again. This phase reads ownership from
  one place and records which; the other is left alone rather than "fixed"
  under a memory phase that has no mandate to arbitrate it.
- **Erasure and the BAR retention set overlap on work orders.** A repair fact
  compiled *from* a work order is deletable; the work order itself is a
  mandated record and is not touched. `forget` must delete the compiled fact
  without touching its origin row, and the checklist covers exactly that.
- **BIPA is a hard blocker the moment voiceprints exist.** 740 ILCS 14/15(a)
  compels destruction within 3 years of last interaction, with a private right
  of action. Recording a voice is probably not a voiceprint; *identifying who
  is speaking* likely is. Nothing in this phase identifies a speaker, and that
  is a constraint to carry forward, not a property to assume persists.

---

## Deviations from v1.0

**1. The prompt block excludes the model's own prior observations. This was
not planned, and it is the most important thing the phase learned.**

The plan said "recall feeds the existing `VehicleContext`" and stopped there.
Running the compile against a copy of the real database showed what that
actually meant: vehicle 10 came back with **eleven facts, ten of them
paragraphs of the vision model's own prose from a single sweep**, and all ten
were about to be injected into the next sweep's prompt under the header
*"Known history for this machine"*.

That is a loop with no brake. An early wrong reading — "possible stator cover
leak" — returns as context, biases the next analysis toward itself, and is
written back looking more established each time. The provenance label does not
save it: a label helps a *person* weigh a claim, and the research behind this
phase measured that even people mostly do not check. A model cannot discount
its own prior output at all.

`recall_summary` now excludes `model-generated` facts by default, filtering
**before** applying the limit so a chatty sweep cannot crowd out the one
complaint that matters. `show` and `ask` are unaffected — a person reading them
sees the observations with their label, which is exactly the case labels are
for. Guarded, and the guards fail when the filter is removed.

**2. A guard was vacuous, and its name is what hid it.**
`test_every_answer_line_is_dated_and_sourced` asserted only the source. The
name promised both. A mutation that stripped the vintage out of every answer
line passed it cleanly. It now matches each line against the real
`established_at` of the fact behind it.

Its sibling had a different flavour of the same weakness: the recall-summary
guard tested `"20" in line`, which any subject containing "20" would satisfy.
Also now matched against real dates.

**3. Six mutations run, one initially mis-targeted.** The `-k` filter for the
vintage mutation matched the *answers* guard rather than the *recall* guard, so
the first run reported a pass that meant nothing. Re-run against both paths
separately. Worth recording because the failure mode is invisible: a mutation
that selects the wrong test looks exactly like a mutation the suite caught.

**4. Eight schema-version pins bumped, and the eighth was found by the
regression rather than by me.** `SCHEMA_VERSION == 57` appears in Gate 9,
Gate 11, Gate 12 and four phase files, all maintained in lockstep — that is the
design, since a schema bump has to be acknowledged by every gate.

The eighth is written differently. `test_phase191b_serve_migrations.py` pins
`get_current_version(db_path) == 57`, so **a grep for `SCHEMA_VERSION == 57`
does not find it.** It was the only failure in a 6,417-test regression. The
same-shaped hazard will recur at the next bump, so a note now sits in that
pin's own reason string saying it is spelled differently and will be missed by
the obvious search.

While editing that line: its reason opened *"literal `52` here is the live
SCHEMA_VERSION"* — stale since Phase 240C moved past 52, three bumps ago. The
number in the assertion had been maintained and the sentence explaining it had
not, which is a small version of the defect this whole family is about.
Corrected.

**5. The `recall` function shadows the `recall` module** in the package
namespace, because `__init__` re-exports `recall.recall` under the same name.
`from motodiag.memory import recall as recall_mod` silently binds the
*function*. The test module uses `importlib.import_module` and says why.

**6. A vision-finding confidence floor was added.** A sweep emits
low-confidence guesses freely, which is right for a ranked list a technician
reads and discards, and wrong for a store that will be recalled as "what is
known about this machine". Findings below 0.5 confidence are not compiled.

## Results

| Metric | Value |
|---|---|
| Guards | **76** in `tests/test_phase244M_client_memory.py` (947 LoC) |
| Mutations run | 6, all caught (one after re-targeting) |
| Schema | v57 → **v58** (migration 058) |
| New package | `motodiag/memory/`, 6 modules, 1123 LoC |
| New CLI surface | `motodiag memory` — 6 subcommands, 177 LoC |
| Schema pins bumped | 8 |
| Real-data compile | **31 facts across 10 machines**, idempotent on re-run |
| Regression | **6,417 passed, 0 failed**, 26:24 |

**Verified against a copy of the real database** — never production, which was
confirmed untouched afterwards (still schema 56, no `memory_facts` table, 24
api_keys). Session 6's CBR600F4i compiled to 11 facts:

```
$ motodiag memory compile
  vehicle 1: 15 new fact(s)
  vehicle 10: 11 new fact(s)
  ...
31 new fact(s) across 10 machine(s).

$ motodiag memory compile        # again
0 new fact(s) across 10 machine(s).

$ motodiag memory ask --vehicle 10 --verbose "what was the complaint?"
(intent: complaints)
Complaints recorded:
  - [2026-09-09T19:54] Leaking oil on left side (2026-09-09, customer-reported)

$ motodiag memory ask --vehicle 10 "has this charging fault been seen before?"
No — nothing in this machine's recorded history mentions charging, fault.

$ motodiag memory ask --vehicle 10 "why is it running lean at 6000 rpm?"
Not in memory: that question is outside what can be answered from recorded
facts. […]                                                          exit 1

$ motodiag memory forget --customer 1 --dry-run
Error: Customer 1 is the `Unassigned` sentinel, not a person. […]   exit 1
```

Those five outputs are the phase: an answer with no API call, an honest
negative that names what it searched for, a refusal that does not guess, and a
deletion that refuses to run against a key meaning "unknown".

### Key finding

**Running it found the defect that reading it could not: the memory's first
real content was the model's own output, about to be fed back to the model as
fact.** Ten of vehicle 10's eleven compiled facts were vision prose. Nothing in
the plan was wrong, and nothing in the code was wrong by its own terms — the
compile faithfully recorded what the product had recorded, and recall
faithfully returned it. The defect only exists at the join, and only shows up
against real data, because the fixture I would have written by hand would have
had a sensible mix of human and machine facts.

The second finding is smaller and older: **a guard's name is not a guard.**
`test_every_answer_line_is_dated_and_sourced` checked one of the two things it
claimed, and the mutation walked straight past it. Sixth instance of the
vacuous-guard family in this session, and once again the mutation caught what
reading did not — including, this time, a mutation run that was itself
mis-targeted and reported a meaningless pass.

### Risks — resolution

- **Nothing to compile** — partly wrong, usefully. The real database yielded 31
  facts, not zero. `memory stats` reports how much history exists, and it also
  reports that 10 of 10 vehicles still carry the `Unassigned` sentinel.
- **The corrections that make this valuable do not exist yet** — unchanged.
  `diagnostic_feedback` is still empty; the compile path for it is wired and
  guarded, so the first correction lands without another phase.
- **A bounded grammar is narrower than "any inquiry"** — held, and now visible:
  the miss text names what memory *can* answer instead of failing silently.
- **Ownership disagreement between `vehicles` and `diagnostic_sessions`** —
  unresolved by design. `attach` writes both, `erase_plan` reads both, and
  nothing here arbitrates the pre-existing conflict.
- **New, unplanned:** the self-reinforcement loop above. Resolved by excluding
  model-generated facts from the prompt path, and guarded.
- **The confidence floor filters nothing in today's data, though it is not
  dead.** Deviation 6 added a 0.5 floor on compiled vision findings. Across all
  20 findings in the database the values run **0.55 to 0.99, with 13 distinct
  levels** — real variation, not a constant. None sits below 0.5, so the floor
  admits everything currently recorded, and its guard exercises a synthetic
  fixture rather than live data. That is a weaker statement than "the floor is
  useless": the field discriminates, and a finding below 0.5 would be excluded
  if one appeared.

  **An earlier draft of this section claimed every finding carried 0.99.** That
  came from sampling one video with `LIMIT 1` — video 2, which has exactly one
  finding, at 0.99 — and generalising. Corrected here because the wrong version
  was about to be committed, and because it is the same error the phase is
  otherwise about: a query answered the question asked of it, and the question
  was too narrow.
