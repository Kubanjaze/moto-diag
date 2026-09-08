# Phase 225 — KTM electrical + FI

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Close the KTM block: the fault-code backlog that 221–224 deferred here,
the adapter-catalog gap 221 left for this row, the TuneBoy/TuneECU naming
question, the ECU-supplier question the row's own title raises, and the
read-access problem in KTM terms.

Direct analogue of 215 (BMW) and 220 (Ducati). Inherits their governing
constraint — **a wrong fault code is worse than a missing one**, and a
make-specific row that restates the generic row **hides** it.

CLI: `motodiag code <dtc>`, `motodiag kb list --make ktm`; guard is
`pytest tests/test_phase225_ktm_electrical.py`.

Outputs (three surfaces — unlike 220, the adapter gap here is real):
- `src/motodiag/knowledge/seed/dtc_codes/ktm.json`
- `known_issues_ktm_electrical.json`
- `adapters.json` + `compat_matrix.json`: one KTM-capable tool, if the
  research establishes one with real provenance
- `tests/test_phase225_ktm_electrical.py`
- Roadmap row 225 corrected as the research dictates; block summary
- Documented known-issue count updated (766 → 773)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. The adapter gap is real and this row owns it.** Four KTM compat
rows across three adapters — `obdlink-mx-plus` (1290, partial),
`autel-ap200bt` (690 and 390, read-only), `els27-forscan` (1290,
read-only) — every one `partial` or `read-only`, every one citing
`ktmforum.com`, and **no full-access option**. BMW has 17 rows with the
GS-911; Ducati 8 with the OEM DDS. 221 guarded the count at 4 and left
it here. `adapters.json` holds 25 records with a fixed schema (slug,
brand, model, chipset, transport, price, protocols, bidirectional,
mode22, reliability, known_issues, notes); `compat_notes.json` has no
KTM entries. Phase 215's tests are the template for adding a tool:
exists, matches a peer's schema, mode22 false, compat rows make-only.

**2. The DTC seed has no KTM file.** 35 generic, 10 BMW, 6 Ducati, 20
Harley. Every KTM row written here shadows a generic row and must earn
it — the 215/220 finding.

**3. What 221–224 deferred here, by test.** All four forbade
`ECU|Keihin|TuneECU|Tuneboy|remap|reflash|P0xxx` and kept
`dtc_codes: []`. That is this phase's entire inbound scope, and the four
test files are the fence: nothing written here may make those four
fail, and nothing they forbade may remain unwritten without a reason.

**4. What already exists in KTM terms and must not be restated.** The
1290 file already says an emissions-level scan will not see MSC faults
and that "no codes" from such a tool is not evidence. So the
read-access entry here cannot be the generic point — it has to be the
KTM tool landscape: what reaches KTM's proprietary memory, what does
not, and what the dealer uses.

**5. Two facts in the row's own wording are unverified, and one more in
its title.** 221 flagged that TuneBoy and TuneECU are different products
and row 230 names TuneECU for Triumph. The row's title says "Keihin FI"
— whether Keihin is the supplier across the whole range, or only part
of it, decides whether that is the fourth naming correction in this
block. And "PowerParts cross-platform" is a phrase whose meaning I do
not know. **None of these is written from memory.** They are being
researched by agents with web access and each finding adversarially
refuted by two lenses (source quality; contradiction search), with
212's lesson built in: a dead agent yields `undecided`, never a verdict.

**6. Cylinder numbering is the sharpest DTC question.** 220's strongest
content was L-twin cylinder identity. 224 declined to assert KTM's
numbering because I could not support it. A KTM misfire row that names
the physical cylinder is worth having **only if research settles it
with a source**; otherwise the row is not written.

## Logic

1. Research the external facts; accept only findings that survive both
   refuters. `undecided` is reported, not dropped.
2. Write DTC rows only where a KTM-specific cause or fix is established;
   each against the generic row it shadows.
3. Write the knowledge entries on the tool landscape, the ECU supplier
   picture, the TPS-reset requirement if established, immobiliser, and
   PowerParts as the research defines it.
4. Add the adapter record only with real provenance in `verified_by`.
5. Validate mechanically against 215/220's checks plus the 221–224 fence.

## Key Concepts

- **Earning the shadow** — from 215 and 220.
- **Research before writing** for anything external; provenance in the
  record, not in my head.
- **The fence**: four earlier test files define what this phase owns.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223).

## Verification Checklist

- [x] Every DTC row standard format; no invented P1xxx; no KTM
      proprietary number transcribed
- [x] Every shadowing row differs from the generic row in causes **and**
      fix, with a counter-assertion that at least one genuinely shadows
- [x] `motodiag code` resolves the KTM row for a KTM and generic for
      another make — verified live
- [x] No cylinder numbering asserted unless research established it with
      a cited source; if asserted, the mapping is guarded against
      self-contradiction (the 220 regex)
- [x] Adapter record matches a peer's schema; compat rows KTM-only;
      `verified_by` real; the 221 row-count guard updated deliberately
- [x] TuneBoy/TuneECU and Keihin resolved from research; row 225
      corrected accordingly
- [x] Nothing here makes tests 221–224 fail; nothing they forbade is
      left unaddressed without a stated reason
- [x] Read-access entry adds the KTM tool landscape, not the generic
      point the 1290 file already makes
- [x] Symptom needles quoted from shipped data; regression green; F9
      clean; block summary written

## Risks

- **Fabricated codes and a fabricated adapter record** are the sharpest
  hazards, and the second is new: an adapter with wrong coverage sends a
  shop to buy the wrong tool. Both are gated on research with sources.
- **Research agents can be confidently wrong.** Two refuter lenses and
  the `undecided` state are the mitigation, not a guarantee.
- **The fence can be too tight.** If 221–224's forbidden lists block a
  legitimate mention here, the fix is to write it here — that is what
  the fence is for.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 766 → 773 |
| KTM entries across five files | 33 |
| DTC rows | 8 (6 shadowing, all differing; 2 new standard codes) |
| Adapter records / compat rows | 1 / 14 (3 full, 5 partial, 6 incompatible) |
| Research agents / refuters / died | 5 / 10 / **0** |
| Findings survived / refuted-on-detail / undecided | 4 / 1 / 0 |
| Roadmap corrections in the row | 3 (Keihin → four suppliers; Tuneboy → TuneECU; PowerParts cross-platform defined) |
| Draft claims removed by refutation | 1 (reset sequence "after throttle-body work") |
| Phase tests | 45 |
| Backend regression | 5331 passed / 0 failed |

**Research changed what the phase could honestly say, in both
directions.** Phase 224 refused to assert KTM's cylinder numbering
because I could not support it. This phase can: KTM's own repair manual
puts the rear cylinder first for every cylinder-indexed code, and two
independent agents read the same page. And the same process removed a
claim — the TuneECU reset "after throttle-body work" — that I would have
shipped from memory, because a refuter went back to the primary source
and found it says *after a map load* and nothing about throttle bodies.

**The tooling finding's refutation was the useful kind.** Both refuters
opened TuneECU's own Basic guide and found the per-model function tabs
say less than the finding claimed: no adjustments of any kind on the
CAN-bus bikes. That is exactly the difference between a `partial` and a
`full` compat row, and the catalog now reflects the source, not the
summary of the source.

**What was not asserted, on purpose.** No branded dealer-tool name (KTM
itself says "the diagnostics tool"). No ABS hex-code format (no source).
No LC8c cylinder side (ten searches, nothing). No USD price presented as
native. Each absence is a test.

**Key finding: an electrical phase's facts are external, and external
facts should be fetched, refuted and cited — not recalled.** 215 and 220
were written from memory with careful hedging. This one was written from
sources with the hedging *removed* where the source allowed and
*sharpened* where it did not. The difference shows in the misfire rows.
