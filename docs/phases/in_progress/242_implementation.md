# Phase 242 — Zero Motorcycles (S/DS/SR/FX/FXE and the SR/F, SR/S, DSR/X platform)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-09

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

- [ ] Every printed figure names its Zero document; every withheld figure
      states the absence
- [ ] Every claim in every entry traces to a research finding that survived
      all three refuter lenses; the rejected claims are recorded with reasons
- [ ] No generic BMS/inverter/thermal content — each entry is Zero-specific
- [ ] No campaign reference number anywhere
- [ ] `make` is `"Zero"`; a make-filtered lookup returns the file, and returns
      241's HV entries above it
- [ ] Provenance per entry matches its `source_class`; forum-tip biconditional
- [ ] DTC file and compat rows shipped only with vendor-document backing, or
      their absence recorded
- [ ] Count guards and the four user docs move together
- [ ] Every new guard mutation-tested
- [ ] Full regression at or above 6031, 0 failed

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
