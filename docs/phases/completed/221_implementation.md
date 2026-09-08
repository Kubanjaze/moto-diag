# Phase 221 — KTM 1290 Super Duke / Super Adventure

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Open the KTM block with the 1290 platform: the LC8 V-twin bikes, their
variants, and the MSC rider-electronics suite.

CLI: `motodiag kb list --make ktm`; guard is
`pytest tests/test_phase221_ktm_1290.py`.

Outputs:
- `known_issues_ktm_1290.json`
- `tests/test_phase221_ktm_1290.py`
- Roadmap row 221 corrected (variant naming — see below)
- Documented known-issue count updated (745 → 751)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. KTM has zero known-issue entries.** 745 entries across nine makes —
Suzuki 148, Honda 142, Kawasaki 140, Harley 119, Yamaha 111, BMW 44,
Ducati 41 — and **no KTM**. The only two mentions anywhere are
incidental: a WP shock swap suggested in a DR650 suspension entry. So
unlike every phase since 211, there is no same-make file to collide
with. This phase opens a block.

**2. The duplication hazard is the topic, not the make, and it is
severe.** The corpus already holds **19 rider-electronics entries** —
"cornering ABS / TC false intervention" (Harley RevMax), "electronics
suite complexity" (H2, R1, MT-10, R6), "IMU and sensor calibration"
(ZX-10R, ZX-6R, GSX-R1000, Z900, ZX-14R, HSTC on the CBR1000RR). The
RevMax entry is the generic form of exactly what a KTM cornering-ABS
entry would say: IMU sensitivity, wheel-speed contamination, cold tires.
This is the Phase 213 hazard, where twelve of eighteen candidates died
because litre-bike content was already told six times over.

So the genericness test runs **backwards**, as in Phase 219: every entry
must **name** 1290-specific hardware or nomenclature rather than merely
avoid a shared topic. Expect to cut candidates.

**3. What the corpus cannot already say: MSC.** `MSC` appears **zero
times** in 745 entries, and "stability control" once (a BMW read-access
entry). The distinction is real and diagnostic, not cosmetic: KTRC,
S-DMS, HSTC and KTRC-alikes are **in-house Japanese systems**, while MSC
is **Bosch-supplied** and KTM was first to production with it. A
mechanic who knows the Bosch generation knows the sensor set and the
conventions; a mechanic who reads "cornering ABS" learns nothing about
which parts are on the bike.

**4. The roadmap row conflates two model lines' variants.** Row 221
reads "R/GT variants" while naming both the Super Duke and the Super
Adventure. **R** and **GT** are the Super Duke's variants; the Super
Adventure's are the base bike, **S**, **R** and **T** — there has never
been a Super Adventure GT. This is a milder error than the four Ducati
row corrections, which named mechanisms the engines do not have: this is
a conflation and an omission, not a wrong mechanism. It still matters,
because the variant determines the parts — a Super Adventure R runs a
21-inch front wheel and different suspension from an S. Row corrected at
close-out to name both lines' variants separately.

**5. The adapter catalog has a real KTM gap, and this phase does not
fill it.** Four KTM rows across three adapters, every one `partial` or
`read-only`, and **no full-access option** — compare BMW's 17 rows with
the GS-911 and Ducati's 8 with the OEM DDS. That is a genuine gap of the
kind Phase 215 filled. But **Phase 225 owns KTM tooling** by roadmap row,
so filling it here would pre-empt that phase rather than duplicate a
covered surface. The row count is guarded at 4 so the decision is
recorded, and roadmap row 225 is annotated with the gap so it cannot be
lost. This is the inverse of Phase 220: there the catalog was already
covered, here it is deliberately left for its owner.

**6. Deferral boundaries, inbound and outbound.** Phase 224 owns LC8
common issues — **cam chain tensioner, electric start, valve clearance
intervals** — so none of those are written here even though they are the
1290's best-known failures. Phase 225 owns the ECU, tuning software and
fault codes, so every entry carries `dtc_codes: []`. Phases 222 and 223
own the Duke line and the enduro singles, so no 125/390/690/790/890/450
content.

## Logic

1. Draft 1290-platform entries and **cut any that a mechanic could get
   from one of the 19 existing rider-electronics entries**. Fewer strong
   entries beats a padded file; Phase 213 cutting 12 of 18 was the right
   outcome, not a failure.
2. Anchor the file on what only a KTM entry can say: MSC as a Bosch
   supplier system, MTC as its traction half, variant-determined
   hardware, and mode behaviour that reads as a fault but is not.
3. Validate mechanically: specificity (every entry names 1290 hardware),
   deferral boundaries (224/225/222/223), catalog row count, symptom
   format, provenance.

## Key Concepts

- **The genericness test runs backwards** (the Phase 219 shape): with 19
  rider-electronics entries in the corpus, an entry that merely avoids a
  shared topic is not enough — it must name 1290 hardware.
- **MSC is supplier-provided, not in-house.** That is the single fact
  that separates this file from the Japanese electronics entries.
- **A gap left for its owner is guarded like a gap already covered** —
  the Phase 220 lesson applied to the opposite situation.
- Claim checks run on assertion-bearing fields only, with bidirectional
  negation and named-system exemptions (the 217–219 lessons).

## Verification Checklist

- [x] Every entry names 1290-specific hardware or nomenclature — asserted
      against a term list, with a counter-assertion that the generic
      RevMax entry would **fail** that same test
- [x] No entry restates the existing cornering-ABS/TC-intervention entry
- [x] MSC is described as Bosch-supplied and distinguished from the
      in-house Japanese systems
- [x] Both model lines' variants are named correctly and separately; no
      "Super Adventure GT"
- [x] No 224 content (cam chain tensioner, electric start, valve
      clearance), no 225 content (ECU, tuning, fault codes),
      `dtc_codes: []` throughout
- [x] No 222/223 models (125/390/690/790/890/450)
- [x] Adapter catalog KTM rows unchanged at 4; roadmap row 225 annotated
      with the gap
- [x] Symptom needles quoted from the shipped data
- [x] Regression green; F9 lint clean

## Risks

- **Duplication is the sharpest hazard this time**, not fabrication. The
  topic is the most-covered one in the corpus, and the temptation is to
  write ten entries that each restate the RevMax entry in KTM colours.
  The counter-assertion — that the RevMax entry fails this phase's own
  specificity test — is the check that matters.
- **Variant claims are parts claims.** Getting Super Adventure S versus R
  wrong sends someone to the wrong wheel size. Variants are stated only
  where confident.
- **No independent reader**, as in 217–220.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 745 → 751 |
| Candidates drafted / shipped | 11 / 6 |
| Cut for genericness | 5 (semi-active suspension, tyre circumference, engine heat, 75° V-twin, cruise control) |
| Distinct 1290 terms per entry | 4–7 (bar is 3) |
| Same check applied to the generic RevMax entry | **0** |
| Adapter catalog rows added | 0 — gap left for Phase 225, guarded at 4 |
| Phase tests | 29 |
| Backend regression | 5197 passed / 0 failed |

**The hazard inverted, and the test inverted with it.** Every phase since
211 guarded against fabrication. Here KTM had zero entries but the topic
was the corpus's most-covered — 19 rider-electronics entries, with the
Harley RevMax "cornering ABS / TC false intervention" entry already
saying what a KTM cornering-ABS entry would say. So the check is Phase
219's shape: entries must **name** 1290 hardware, counted as distinct
terms so repetition cannot satisfy it, with the RevMax entry run through
the same check as a counter-assertion. It scores zero.

**The check caught my own first draft, which is the point of having it.**
Five of seven entries scored a single distinct term, all of it from the
title — generic bodies wearing a KTM badge. The response was to cut and
rewrite, not to lower the bar: the tyre-circumference entry went entirely
because its mechanism is universal and filing it under a make hides it
from everyone else, and two others were rewritten with real KTM anchoring
rather than sprinkled keywords.

**MSC is what justifies the file.** It appeared zero times in 745
entries. It is a **Bosch supplier system** KTM put into production first,
unlike the in-house Japanese systems the corpus already documents — so
the sensor set and the conventions follow the Bosch unit, which is a
different diagnostic starting point from a make-proprietary black box.

**Key finding: a validator over prose must exempt reported speech, not
just negation.** The check flagged "if a customer or a listing **says**
Super Adventure GT" as asserting a bike that does not exist. Phase 218
handled reports by treating symptoms as reports; this shows a report can
sit inside an assertion-bearing field, because a fix procedure's job
includes telling a mechanic what a customer will say. Quoting an error is
not making it. The exemption was verified not to neuter the check — a
planted "The Super Adventure GT uses a 19-inch front wheel" is still
caught.
