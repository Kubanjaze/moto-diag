# Phase 215 — BMW electrical + FI dealer mode

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Close the BMW block by servicing the backlog the previous four phases
deferred here: BMW fault codes, the ZFE central electronics, and the
GS-911 — the tool that actually reads a BMW motorcycle. Unlike 211–214
this is not purely a knowledge-base phase; it touches three data
surfaces, and the riskiest deliverable is the one where inventing a
single number sends a mechanic down the wrong path.

CLI: `motodiag code <dtc>`, `motodiag hardware compat recommend --make
BMW`; the guard is `pytest tests/test_phase215_bmw_electrical.py`.

Outputs:
- `src/motodiag/knowledge/seed/dtc_codes/bmw.json` — BMW fault codes
- GS-911 added to `hardware/compat_data/adapters.json` and
  `compat_matrix.json`
- `known_issues_bmw_electrical.json` — ZFE, dealer mode, and the
  read-access problem
- `tests/test_phase215_bmw_electrical.py`
- Documented known-issue count updated

## Existing-code audit (Step 0, per CLAUDE.md)

**1. The DTC seed is thin and the Harley file sets the safe pattern.**
55 codes total: `generic.json` (35, `make` absent) and
`harley_davidson.json` (20, `make: "Harley-Davidson"`). Every Harley
code uses a **standard OBD-II prefix** — thirteen P0xxx, seven in the
manufacturer-defined P1xxx range, plus `U1016` and `B1004`. The pattern
is therefore: real code numbers, make-specific *causes and fixes*.
`dtc_repo.get_dtcs` resolves make → generic → any, so a BMW row shadows
the generic one for a BMW bike automatically. Fields:
`code, description, category, severity, make, common_causes,
fix_summary`; `category` ∈ SymptomCategory (13 values), `severity` ∈
{critical, high, medium, low, info}. The loader pre-deletes by
`(code, make)` so re-seeding is idempotent.

**2. GS-911 is absent from a catalog that already knows about BMW.**
24 adapters, 110 compat rows, **12 of them BMW** — and they already
describe the problem this phase is about: `elm327-generic-bt-clone` is
marked *incompatible* on the S1000RR because "BMW proprietary CAN
session layer that rejects generic ELM327 handshake", and several rows
point at BimmerCode for coding. What is missing is the actual BMW
motorcycle dealer-level tool. `compat_matrix` rows carry a
`verified_by` URL — provenance already exists on this surface.

**3. The deferral backlog is real but narrow.** Phases 211–214 wrote
`dtc_codes: []` on every entry and their tests assert it, with the
R-series Integral ABS entry explicitly forward-referencing "the Phase
215 dealer-mode entry". So what is owed is: BMW fault codes, and an
entry about reading them.

**4. The accuracy risk is sharper here than in any previous phase.** A
knowledge-base entry that is vaguely wrong wastes an hour. **A fault
code that is wrong sends a mechanic to the wrong component with false
confidence**, because a code number reads as a fact, not an opinion.
BMW motorcycles emit standard OBD-II P0xxx codes for emissions-related
faults — those are shared and safe. BMW *proprietary* fault codes, the
ones GS-911 and ISTA read, use a different numbering entirely and are
not P-codes. I will not invent numbers in the manufacturer-defined
P1xxx range or transcribe proprietary BMW codes I cannot vouch for.

## Logic

1. **DTC content, tightly bounded.** Draft only codes the drafter is
   confident about, with BMW-specific causes and fixes — the Harley
   pattern. A dedicated **fabricated-code refuter** asks of every entry:
   is this code number real, does the description match its standard
   OBD-II meaning, and is the BMW-specific content actually
   BMW-specific? Default to refuted. Expect a small file; a short,
   correct DTC list is worth more than a long plausible one.
2. **The format itself is documented as knowledge, not invented as
   data.** That BMW proprietary codes exist, are not P-codes, and need
   GS-911/ISTA to read is a *known issue* entry — which is honest and
   useful — rather than a set of fabricated code rows.
3. **GS-911 catalog entry**, following the adapters.json schema, plus
   compat_matrix rows scoped per BMW family, with the existing rows'
   framing (what generic ELM327 hardware cannot do) as context.
4. **ZFE and dealer-mode known_issues** entries, same three-refuter
   pipeline as 212–214, with the attribution lens briefed that this is
   a cross-model electrical phase so entries may legitimately span the
   R/F/S/K families — but must not restate the ZFE accessory entries
   Phase 212 already wrote for the F-series.
5. **I write the files** and run the regression.

## Key Concepts

- **A wrong code number is worse than a missing one.** This is the
  phase's governing constraint and the reason for a fourth refuter
  lens. The `figures` lens in 213–214 already killed entries for
  unverifiable recall identifiers; a DTC number is the same class of
  claim with a shorter fuse.
- `dtc_repo.get_dtcs` make precedence means a BMW row automatically
  shadows the generic one — so a BMW P0117 entry must *add* BMW
  content, not restate the generic description.
- `UNIQUE(code, make)` plus the loader's pre-delete makes re-seeding
  idempotent; a duplicate code within the file is the failure mode to
  test for.
- The compat_matrix `verified_by` URL field is the provenance
  mechanism on the hardware surface, parallel to `source` on
  known_issues.
- Phase 212 already covered ZFE *accessory* behaviour (tripped
  electronic fuses, heated grips, non-CAN accessories) for the
  F-series. This phase covers the ZFE as a *diagnostic subject*, not a
  re-telling.

## Verification Checklist

- [x] **11 DTC rows drafted, 10 kept, 1 dropped**; 5 issue entries
      drafted, 4 verified, 3 in the final file. 41 agents, 0 errors
- [x] Every code is standard-format; **no P1xxx invented**; no BMW
      proprietary code smuggled in as a P-code — asserted
- [x] No duplicate code in the file; every row `make == "BMW"`
- [x] Seven rows shadow a generic code, and each is asserted to differ
      from the generic causes *and* fix — with a counter-assertion that
      at least one row genuinely shadows, so the check is not vacuous
- [x] `get_dtcs("P0335", make="BMW")` returns the BMW row;
      `make="Honda"` still returns the generic row — verified live
- [x] GS-911 in `adapters.json` with a schema identical to a peer row;
      5 compat rows, all `make: bmw`, each with a `verified_by` value
- [x] `hardware compat seed --yes` then `compat list` shows **25
      adapters**
- [x] The dealer-mode entries cover the read-access problem (ELM327 vs
      GS-911) and do not restate Phase 212's three ZFE accessory
      entries — asserted on titles
- [x] All five BMW files load together to **44 BMW entries**, no title
      collision
- [x] DTC seed 55 → 65; known issues 701 → 704; count guard fired,
      four docs updated
- [x] 24 phase tests; F9 lint clean; backend regression green

## Risks

- **Fabricated fault codes are the single biggest hazard in the whole
  of Track K so far.** A code is a lookup key a mechanic trusts. The
  mitigation is a dedicated refuter and a deliberately small file; if
  the honest output is six codes, it is six codes.
- **BMW proprietary codes are genuinely out of reach.** Documenting
  that fact is the correct deliverable, and it risks reading as a
  shortfall when it is accuracy.
- **GS-911 pricing and capability change.** The adapter row states
  capability qualitatively and defers pricing to the vendor rather
  than freezing a figure that will rot.


## Deviations from Plan

**The fabricated-code lens found nothing fabricated — the shadowing
lens is what did the work.** Only one DTC row was dropped, and not for
being invented: **P0135** was killed because the corpus's existing
generic O2 coverage in `cross_platform_fi.json` already gives a
heater-resistance range, the heat-damaged-routing cause and the
aftermarket-exhaust eliminator path *with make-specific detail for four
other manufacturers*, while the BMW row offered only generic O2-heater
causes. The verdict's phrase is the one worth keeping: the row was
"strictly weaker than the generic row it would shadow — a BMW owner
hitting P0135 would lose the resistance spec and gain nothing." That is
a failure mode I had not anticipated when writing the plan. I framed
shadowing as "must add value"; the real hazard is that a make-specific
row can *subtract* value by hiding better generic content.

**One issue entry was dropped for triple duplication.** The CAN-bus
entry was refuted as a generic CAN playbook, as a restatement of
`harley_electrical`'s "CAN bus communication fault — 2011+ models"
(which does it better, with real U0100/U0121 codes and 60/120/0-ohm
interpretation), *and* as a diluted version of Phase 212's ZFE trio.
The verdict also caught a model-scope error I would have missed: its
"F-series, K-series … 2004–2026" span sweeps in the pre-CAN F650GS
single and the longitudinal K1200RS, neither of which is a CAN-bus
bike.

**A fourth verified issue was cut at synthesis**, leaving three.

**I acted on the GS-911 draft's own uncertainty list rather than
shipping it whole.** The agent was required to declare what it was
unsure of and produced fifteen items, two of which were consequential
enough to change the data:
- `supports_mode22` was flipped **true → false**. The drafter wrote
  "arguably wrong … the GS-911 reads live data via BMW proprietary
  service requests, NOT generic OBD Mode 22", and that flag feeds the
  adapter recommender.
- The **R1300GS compat row was dropped** — self-described as "the most
  speculative item here … inferred, not sourced … NOT verified".

The remaining `verified_by` strings are honest about their own limits
("surfaced in search; page not opened"), which is the right state for a
provenance field to be in.

## Results

| Metric | Value |
|--------|-------|
| DTC codes | 55 → 65 (10 BMW) |
| Known issues | 701 → 704 |
| Adapters | 24 → 25 |
| Compat rows | 110 → 115 |
| BMW entries across five files | 44 |
| DTC drafted → kept | 11 → 10 (1 dropped on shadowing) |
| Issues drafted → verified → kept | 5 → 4 → 3 |
| Agents / errors | 41 / 0 |
| Phase tests | 24 |
| Backend regression | 5056 passed / 0 failed |

**Key finding: a make-specific row can be worse than no row at all.**
The plan's stated risk was fabrication — inventing a code number that
sends a mechanic to the wrong component. That risk did not materialise;
what did was subtler and more interesting. Because make-specific rows
resolve *before* generic ones, a mediocre BMW row does not merely fail
to help — it **hides** the better generic row that would otherwise have
answered the question. Precedence turns "adds nothing" into "actively
subtracts", and any lookup with make→generic fallback has this property.
