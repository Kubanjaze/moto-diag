# Phase 220 — Ducati electrical + FI

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Close the Ducati block by servicing the fault-code backlog that Phases
216–219 deferred here, and by covering the Marelli ECU, the DDA data
logger, Ducati's CAN behaviour and the DDS access problem.

This is the direct analogue of Phase 215 (BMW electrical), and inherits
its governing constraint: **a wrong fault code is worse than a missing
one**, and — the finding that actually mattered there — a make-specific
DTC row that merely restates the generic row does not just fail to
help, it **hides** the better generic answer.

CLI: `motodiag code <dtc>`; guard is
`pytest tests/test_phase220_ducati_electrical.py`.

Outputs:
- `src/motodiag/knowledge/seed/dtc_codes/ducati.json`
- `known_issues_ducati_electrical.json`
- `tests/test_phase220_ducati_electrical.py`
- Documented known-issue count updated (740 → 745)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. The adapter surface is already covered — unlike Phase 215.** When
215 ran, the GS-911 was absent from a 24-adapter catalog and adding it
was a real deliverable. Ducati is different: **8 compat rows across 8
adapters** already exist, including the OEM `ducati-dds-readiness-tool`
("Factory Ducati dealer tool. Full access to Panigale / Monster /
Multistrada diagnostic and service functions"). The catalog also already
records the access problem this phase describes — the
`elm327-generic-bt-clone` row is marked *incompatible* on the Panigale
because "CAN-FD on newer variants (V4) breaks counterfeit ELM327
silicon". **Nothing is added to the adapter catalog**; duplicating a
covered surface is exactly what the last five phases have been rejecting.

So this phase touches **two** surfaces, not three: the DTC seed and
known_issues.

**2. The DTC seed and the shadowing hazard.** 65 codes exist: 35
generic, 20 Harley, 10 BMW. `get_dtcs` resolves make-specific **before**
generic, so a Ducati row shadows the generic row for a Ducati bike.
Phase 215 dropped its only rejected code (P0135) for precisely this —
the BMW row would have hidden a generic entry that carried a
heater-resistance range and eliminator guidance it did not. Every
Ducati row here must earn its shadow.

The 35 generic codes are known and listed, so each Ducati row is written
against the specific generic row it will hide.

**3. Ducati-specific angles that genuinely add over generic.** The
strongest is **cylinder identity on an L-twin**: a Ducati's cylinders are
horizontal (front) and vertical (rear), not left/right or 1/2 by
position, and a misfire or injector code naming "cylinder 1" sends a
mechanic to the wrong one if they read it as an inline engine. Others:
the **TPS reset** that Ducati requires after throttle-body work and
which needs a tool; the in-tank pump and relay arrangement; the charging
weakness on older air-cooled bikes; and the idle actuator.

**4. Proprietary codes are documented, not invented.** Ducati's own
fault numbering, read by the DDS and Ducati-capable tools, is not the
P-code space. As in 215, its existence and the "no codes found is not no
fault" trap are written as knowledge; no proprietary number is
transcribed and no P1xxx is invented.

**5. What 216–219 deferred here**: Marelli ECU internals and mapping,
DDA+, Ducati CAN format, the DDS tool, regulator/rectifier and stator as
an electrical category, TPS reset via tool, and every fault code. All
four phases kept `dtc_codes == []` and their tests assert it.

## Logic

1. Write `ducati.json` with a small number of standard-format codes,
   each stating **why it shadows** — a Ducati cause or fix the generic
   row cannot give. Prefer codes where the L-twin cylinder-identity
   point or a Ducati component makes a real difference.
2. Write electrical/FI knowledge entries covering the read-access
   problem, the Marelli ECU and sanctioned up-mapping, the DDA as a
   *logger* rather than a diagnostic tool, the immobiliser, and the
   TPS-reset requirement.
3. Validate mechanically: code format, no invented P1xxx, no
   proprietary numbers, shadow justification against the generic file,
   deferral boundaries now *inbound* (this phase may finally write
   codes), symptom format.

## Key Concepts

- **Earning the shadow** is the phase's governing test, carried
  directly from 215.
- **L-twin cylinder identity** is the single most useful Ducati-specific
  fact a fault code can carry here.
- The DDA is a **data logger**, not a fault reader — a distinction shops
  and owners routinely collapse.
- Claim checks run on assertion-bearing fields only, with bidirectional
  negation and named-system exemptions (the 217–219 lessons).

## Verification Checklist

- [x] Every DTC row is standard format; no invented P1xxx; no Ducati
      proprietary number transcribed
- [x] Every shadowing row differs from the generic row's causes **and**
      fix — asserted against `generic.json`, with a counter-assertion
      that at least one row genuinely shadows
- [x] `motodiag code` resolves the Ducati row for a Ducati and the
      generic row for another make — verified live
- [x] Nothing added to the adapter catalog; its Ducati rows unchanged
- [x] Knowledge entries cover the read-access problem and name the DDS
- [x] No adapter-catalog duplication and no re-telling of 216–219
      content; no title collision across the five Ducati files
- [x] Symptom needles quoted from the shipped data
- [x] Regression green; F9 lint clean

## Risks

- **Fabricated codes remain the sharpest hazard**, and unlike a prose
  entry a wrong code is a lookup key a mechanic trusts. The file is
  deliberately small.
- **Shadowing is the subtler hazard** and the one that actually bit in
  215. Each row is written against the generic row it displaces.
- **No independent reader**, as in 217–219. My own checks have now
  produced false positives in four consecutive phases — always on
  correct content, never by passing something false, but that is an
  observation rather than a guarantee.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 740 → 745 |
| Ducati known issues (five files) | 41 |
| DTC rows added | 6 — all shadowing a generic row deliberately |
| DTC seed total | 35 generic / 10 BMW / 6 Ducati / 20 Harley |
| Adapter catalog rows added | 0 — the surface was already covered |
| Phase tests | 23 |
| Backend regression | 5168 passed / 0 failed |

**The audit changed the shape of the phase before any content existed.**
Phase 215's third deliverable was an adapter entry, because the GS-911
was genuinely missing from the catalog. Ducati is not missing: eight
compat rows across eight adapters, the OEM DDS among them, and the
counterfeit-ELM327 failure on newer CAN already recorded. So this phase
shipped two surfaces instead of three, and a test now asserts the
catalog's Ducati rows are **unchanged** — the deliverable that was
dropped is guarded, not merely skipped.

**Every code earns its shadow, and the mapping is guarded against
itself.** All six rows displace a generic row, so each is asserted to
differ from it in both causes and fix, with a live check that a Honda
still resolves to generic. The strongest content is L-twin cylinder
identity — cylinder 1 horizontal/front, cylinder 2 vertical/rear —
which the generic misfire rows cannot say. Because both rows restate
that mapping, a regex now requires every statement of it to agree; one
reversed sentence would be worse than silence, since it is the sentence
the mechanic acts on.

**Key finding: a guard should outlive the deliverable it was written
for.** The most useful assertion in this phase covers something the
phase deliberately did *not* build. Step 0 found the adapter surface
already covered, and the natural response — write nothing and move on —
would have left the next phase free to duplicate it. Encoding the
finding as a test turns a one-time audit result into a standing one.
