# Phase 242 — Zero Motorcycles (S/DS/SR/FX/FXE and the SR/F, SR/S, DSR/X platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-09

## Goal

The first make-specific electric phase. Zero is the volume electric
motorcycle maker and the one a general workshop is most likely to see; today
the product knows nothing about it — no knowledge entries, no DTC file, no
compatibility rows, no parts, and the vehicle identifier has never heard the
name. Phase 241 laid the make-agnostic HV safety floor. This phase adds what is
*specific* to Zero: the Z-Force powertrain and its generations, the IPM motor
and belt final drive, the Zero app as the diagnostic route, the charging
system, and the failure patterns owners and the regulator have actually
recorded.

**The boundary this phase must hold, stated before any content exists:** 241
printed no machine-specific figure because it opened no manufacturer document.
242 is the first phase where a pack voltage, a discharge wait, an interval or a
torque *could* legitimately appear — **and only from a Zero document the
research actually opened and the entry names**, per the Phase 238 rule. A
figure the research cannot attribute to a named Zero document is withheld with
the absence stated, exactly as 241 did. Aggregator sites, forum recollection
and spec-sheet roundups are not documents.

Phases 246 (BMS), 247 (inverter), 249 (thermal) own the generic electric
systems. Anything here about those must be Zero-specific — a Zero failure
pattern, a Zero part, a Zero procedure — or it belongs to them.

CLI: no new commands. Content reaches mechanics through `kb search`,
`kb symptom`, `diagnose`, and — if a compat row is justified — `hardware compat`.

Outputs:
- `known_issues_zero.json` — as many entries as survive refutation, not a target
- `dtc_codes/zero.json` **only if** Zero's fault codes are documented in a
  primary source the research opens; otherwise the absence is recorded
- compat/adapter rows **only if** a diagnostic route can be verified against a
  vendor document
- `tests/test_phase242_zero.py`
- the research record, with every rejected claim and why

## Logic

### Step 0 — what exists (audit complete)

Nothing. `grep` for Zero, Z-Force, ZF14, Cypher across every knowledge, DTC,
compat, parts and template file returns only Phase 241's HV file. The vehicle
identifier's only "zero" hits are token-cost comments. One workflow template
applies to electric and it is the generic PPI. No Zero document is on disk
anywhere the search reached — discipline 9 was checked and came back empty.
The substrate (powertrain, EV DTC categories, `applicable_powertrains`) is the
same Phase 110/111 substrate 241 sits on. So: greenfield *content* on an
extension *substrate*.

### The research workflow (this is the build's first step, and it is orchestrated)

Track K's cadence was 2 questions × 2 refuter lenses = 6 agents. Under
ultracode this phase runs the same discipline at scale, and the discipline —
not the count — is the point. Every claim is a candidate until a refuter fails
to kill it.

**Stage 1 — multi-modal sweep**, parallel, each finder blind to the others:
- *by manufacturer document*: owner's manuals, service bulletins, the Zero
  support knowledge base, published specifications — what Zero itself states
- *by regulator record*: recall campaigns by **mechanism** (no campaign
  numbers — the Phase 231 rule holds across tracks)
- *by owner community*: the recurring failure patterns owners report, labelled
  as such
- *by tooling*: the Zero app, the diagnostic port, what third-party tools can
  and cannot read
- *by platform generation*: what changed between Z-Force generations and which
  models carry which, so an entry's `year_start`/`year_end` are defensible

Each finder returns structured claims with a `source_class` —
`manufacturer-document`, `regulator-record`, `community-report`, or
`not-established` — and, for a document, its name.

**Stage 2 — adversarial refutation**, pipelined per claim, three distinct
lenses because a claim can fail three ways:
- *does the source exist and say this* — the phantom-source lens that caught a
  Citroën campaign passed off as a motorcycle recall in Track K
- *is the figure attributed* — any number must trace to a named Zero document
  or be marked withheld
- *is this Zero-specific* — or is it generic BMS/inverter/thermal content that
  belongs to 246/247/249

A claim survives only if no lens refutes it. Refuters default to refuted when
uncertain.

**Stage 3 — completeness critic**: what modality was not run, what claim was
never checked, what document was cited and never opened. Its output is the
next round's work if it names anything material.

**Stage 4 — synthesis** into entries, with provenance set from `source_class`:
`service-manual` only for a named manufacturer document; `forum` for
community patterns, carrying `Forum tip:` per rule 3; `model-generated`
otherwise. Recall mechanisms from the regulator record are `service-manual`,
as Track K filed them.

### The build after the research

Entries written from surviving claims only. `make` is `"Zero"` — reachable,
and a `make=Zero` query returns this file **and** 241's HV floor together,
which is the intended reading order once 240C's ranking puts the critical
safety entries first. `model` names the platforms. Titles must not collide
with 241 or anything corpus-wide.

## Key Concepts

- **A figure carries its document or it is withheld** (Phase 238, hardened at
  241). The test is per entry: any printed figure requires a named Zero
  document in the description.
- **Refuters default to refuted.** Roughly 60% of Track K's audit findings did
  not survive verification; that layer is the point, not an obstacle.
- **No campaign reference numbers** (231). Recalls by mechanism.
- **Scope by ownership**: 246/247/249 own the generic systems.
- **Reachability is correctness** (240B S2); **ordering is real** (240C).
- **The Zero app is the diagnostic route, and the compat schema has no
  app-based transport.** Whether and how to represent it is a finding of the
  research, not an assumption of the plan.

## Verification Checklist

- [x] Every printed figure names its Zero document; every withheld figure
      states the absence
- [x] Every claim in every entry traces to a research finding that survived
      all three refuter lenses; the rejected claims are recorded with reasons
- [x] No generic BMS/inverter/thermal content — each entry is Zero-specific
- [x] No campaign reference number anywhere
- [x] `make` is `"Zero"`; a make-filtered lookup returns the file, and returns
      241's HV entries above it
- [x] Provenance per entry matches its `source_class`; forum-tip biconditional
- [x] DTC file and compat rows shipped only with vendor-document backing, or
      their absence recorded
- [x] Count guards and the four user docs move together
- [x] Every new guard mutation-tested
- [x] Full regression at or above 6031, 0 failed

## Risks

- **The research fabricates a document.** The single largest risk, and the
  reason for the source-exists refuter lens with refuted-by-default.
- **Scope drift into 246/247/249.** A Zero BMS fault pattern is in scope; how
  BMS cell balancing works is not. The third refuter lens exists for this.
- **The figure boundary erodes under pressure.** Zero publishes specs widely,
  and a nominal pack voltage feels safe to print. It is printed only from a
  named Zero document, or not at all.
- **The Zero app has no place in the hardware schema.** `adapters.json` has no
  app transport and `compat_matrix` keys on an adapter slug. Forcing it in
  would misrepresent the route; the plan leaves this to the research.
- **Model naming.** The roadmap row names the older lineup (S/DS/SR/FX/FXE);
  the SR/F, SR/S and DSR/X are the current platform. Year ranges must be
  defensible per model from a document, or wide and stated as such.
- **Corpus count moves again**, and four user docs with it — the 208 guard.

---

## Deviations from Plan

**I wrote a refuter prompt that biased the whole research run, and it had to be
repaired before any content was written.** The figure lens was specified as
"every number must trace to a named Zero Motorcycles document". That is the
right standard for a manufacturer-document claim and the wrong one for every
other class: a recall record's model years, build windows and unit counts come
from the **regulator**, not from Zero. The lens therefore could not pass any
regulator or community claim containing a number, and it refuted all of them.
The first run's result — 29 survived, every single one `manufacturer-document`,
zero recalls, zero community patterns — looked like a clean corpus and was an
artefact of my own prompt.

A repair run re-judged the 25 claims that had passed the source and scope
lenses and died only on that bug, using a source-class-aware standard.
**11 recovered: 8 recall claims and 3 community patterns.** Without it this
phase would have shipped a Zero file with no recall coverage at all, including
no stop-riding campaigns.

**The refuters corrected substance, not just attribution, and the corrections
were safety-relevant.** Every one of the 11 came back with a `corrected_claim`.
Four that materially changed what a mechanic is told:

- The 2013 water-ingress campaign covers the **FX and XU only**, not the full
  2013 line — and its remedy is **removal and return of the battery modules**,
  not the sealing operation the original claim described.
- The 2020 front-brake-switch record describes **no** failure mode in which the
  brake light stays on — the original claim said it did. It does record that
  **cruise control will not cancel** on front-brake application, which the
  original missed entirely.
- The 2023-24 key-switch campaign's remedy is a **firmware update**, dealer or
  over-the-air. The original claim implied harness work, which is what a shop
  reading the mechanism would quote.
- The 2012 pack-fire campaign's remedy is the owner's **choice** of repurchase
  or trade-assist, and the record carries a **park-it advisory** the original
  claim did not mention.

**14 claims stayed rejected after the repair, on judgement rather than
infrastructure.** Six were recall claims whose verifiers opened the Part 573
reports and found the claim wrong on substance — one flagged simply
"REMEDY IS WRONG AND SAFETY-CRITICAL". Those are not in the file.

**Five claims are unverified rather than refuted**, because their refuters died
when the run hit a session limit. They are recorded as debt, not shipped. One
of them — the cross-platform belt-tension comparison — turned out to matter, so
the entry that covers it was written from the two platform manuals directly
rather than from the unverified comparison.

**The completeness critic never ran** (same session limit), so coverage is
unverified. Recorded as debt.

**One test I wrote had the same bug as the refuter prompt.** The guard requiring
a printed figure to name a Zero document used a `DOC` pattern listing only Zero
publication types — so a recall entry, whose figures legitimately come from a
regulator, would have failed it. Widened to accept a regulator record. The bug
was mine twice in one phase, in two different places, from the same wrong
assumption.

**No DTC file and no compat rows shipped.** The tooling research established
that the diagnostic route is the dash error list, the Zero app and Zero's own
dealer unit, and that Zero does not publish a machine-readable fault-code
vocabulary — the codes are a numbered table in the owner's manual, which is
knowledge-base content, not a `dtc_codes` file. The plan left this to the
research and the research answered it. Recorded rather than forced.

## Results

| Metric | Value |
|--------|-------|
| Claims swept / unique after dedup | 5 finders, 76 raw / **75 unique** |
| Survived first run | 29 — all `manufacturer-document` (the bug) |
| Recovered by the repair run | **11** of 25 re-judged (8 recalls, 3 community) |
| Rejected on judgement | 55 |
| Unverified (refuter died) | 5, recorded as debt |
| Entries shipped | **17** — 16 `service-manual`, 1 `forum` |
| Recall campaigns covered | **8**, all by mechanism, **no reference numbers** |
| Corpus | 927 → **944**; four user docs moved with it |
| Severity mix | 3 critical, 7 high, 7 medium |
| Guards | 16, all six families mutation-tested |
| Mutation scenarios | 6, all caught (one required redoing — my first attempt left a marker in an unstripped field) |
| Corpus-globbing guards swept | 654 passed |
| Regression | **6047 passed / 0 failed** (baseline 6031; +16 guards) |

**Key finding: the refuter layer is only as good as the standard it applies,
and a single wrong clause in one prompt silently deleted an entire evidence
class.** The run looked successful — 29 well-attributed claims, every figure
traced to an opened document. What it had actually done was refuse every recall
in Zero's history on a technicality, and the shape of the result (100% one
source class) was the only visible symptom. Track K's lesson was that findings
need verification; this phase's is that the verifier needs its own standard
checked, because a verifier that is wrong in one direction fails silently and
looks rigorous while doing it.
