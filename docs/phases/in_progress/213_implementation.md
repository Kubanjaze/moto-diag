# Phase 213 — BMW S1000RR / S1000R / S1000XR

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Cover BMW's inline-four line — S1000RR across its generations, the
S1000R naked and the S1000XR adventure-sport — with the failures that
are specific to *these* machines rather than to superbikes in general.
Content is drafted by independent lenses and adversarially refuted
before acceptance, the discipline Phase 212 established and justified.

This is the phase most exposed to generic-electronics duplication:
traction control, IMU and riding modes already appear across ~48 seed
files, and "shift assist pro" — which the roadmap row names — was
written for the F850GS in Phase 212. An S1000 entry has to be about
S1000 hardware or it is a duplicate wearing a BMW badge.

CLI: `motodiag kb list --make bmw`; the guard is
`pytest tests/test_phase213_bmw_s1000.py`.

Outputs:
- `src/motodiag/knowledge/seed/knowledge/known_issues_bmw_s1000.json`
  — ~12 entries, each `source: "model-generated"`
- `tests/test_phase213_bmw_s1000.py`
- Documented known-issue count updated (684 → 684 + N)

## Existing-code audit (Step 0, per CLAUDE.md)

Run inline. Nouns audited: `s1000`, `hp4`, `shiftcam`, `shift assist`,
`quickshifter`, `traction control`, `IMU`, `riding mode`, `semi-active`,
`DDC`.

**1. Greenfield for content.** No BMW inline-four entry exists. Every
`S1000` grep hit is a false positive — `GSX-S1000` (27) and `GS1000`
(4), both Suzuki. The two BMW files hold 24 entries, all boxer or
F-series.

**2. The roadmap row names a topic already written.** Row 213 reads
"…electronics, shift assist pro". Phase 212 shipped *Gear Shift Assist
Pro stops working — shift-lever sensor wiring failure* for the
F750/F850GS, and quickshifter failures are covered again on the Honda
CBR1000RR (sensor, rod adjustment, calibration) and in
`cross_platform_drivetrain` (dog-tooth wear from incomplete shifts).
A third quickshifter entry is only justified if the S1000's HP Shift
Assist Pro fails in a way those three do not describe. Default is to
skip it.

**3. Generic electronics are saturated.** Traction control, IMU,
lean-sensitive intervention, riding modes and semi-active suspension
appear across ~48 files including four litre-class peers
(`honda_cbr1000rr`, `kawasaki_zx10r`, `suzuki_gsx_r1000`, `yamaha_r1`).
An S1000 electronics entry must name BMW-specific hardware — DDC
semi-active damping, DTC/DTC-Pro, the HP4 systems, ABS Pro — and
describe a failure of *that*, not "traction control intervenes early".

**4. What is legitimately S1000-specific** and worth drafting: the
2019+ ShiftCam variable valve mechanism and its cold-start noise; the
K46-generation gearbox and its known second-gear complaints; the
S1000XR's well-documented vibration and BMW's response to it; DDC
semi-active shock failure modes distinct from a conventional shock;
the inline-four's chain and rear-subframe behaviour under XR touring
loads; cam-chain tensioner behaviour across generations.

**5. Contract** (unchanged from 211/212): fourteen fields; severity ∈
{critical, high, medium, low}; `make == "BMW"`; `source ==
"model-generated"` in the JSON and on every row; the phrase "general
knowledge" in every description; short searchable symptom phrases, not
sentences — `find_issues_by_symptom` is a SQL `LIKE` match and Phase
212's drafters had to be corrected on exactly this; and the Phase 208
count guard, which will fail four docs the moment entries land.

## Logic

1. **Draft** — six independent authors by lens: S1000RR 2009–2014
   (K46); S1000RR 2015–2018; S1000RR 2019+ (ShiftCam); S1000R naked;
   S1000XR adventure-sport; BMW-specific electronics and suspension
   (DDC, DTC, ABS Pro, HP4). Each gets the contract, the avoid-list and
   the generation traps, and returns candidates with self-assessed
   confidence and a declared list of every numeric figure used.
2. **Dedup** — plain code, by normalised title, against the 24 existing
   BMW titles and across drafts.
3. **Verify** — three refuters per candidate, distinct lenses, each
   defaulting to refuted when uncertain:
   *attribution* (wrong model or generation; F-series or boxer hardware
   ported onto an inline four; a generic superbike failure relabelled;
   duplicates the three existing quickshifter entries),
   *invented figures* (any voltage, torque, interval, price or part
   number a mechanic would read as a spec — omit, do not guess),
   *safety and procedure* (would following it damage the bike or hurt
   someone; is the diagnostic order cheap-first).
   Survives only if at most one refuter objects **and** the safety
   refuter does not. A dead refuter is retried once then excluded from
   the vote — never counted as a refutation.
4. **Synthesize** — assemble survivors, apply "fixable" refuter notes,
   enforce the contract, cap at 12.
5. **I write the files** and run the regression. Agents return data;
   nothing in the workflow touches the working tree.

## Key Concepts

- **The undecided state.** Phase 212's first run reported zero
  survivors from an outage because `null` was treated as a fatal
  refutation. The harness now distinguishes "refuter disagreed" from
  "refuter died"; anything with fewer than two real verdicts is
  reported as undecided rather than dropped.
- **Attribution is the load-bearing lens here.** In 212 it caught an
  R1200 component written onto an F-series. The equivalent risk in 213
  is a generic litre-bike failure — or an F-series/boxer part — wearing
  an S1000 badge, and four litre-class peers already in the corpus make
  that easy to do accidentally.
- **Symptoms as short phrases**, enforced by test, because the search
  path is `LIKE '%needle%'`.
- Generation naming: S1000RR spans 2009–2011, 2012–2014, 2015–2018,
  2019–2022 (ShiftCam) and 2023+; S1000R from 2014; S1000XR from 2015
  with a significant 2020 revision. Every entry names its generation.

## Verification Checklist

- [ ] The workflow ran 3 refuters per candidate; drafted / survived /
      kept and every drop reason recorded in the phase log
- [ ] Zero candidates left `undecided`, or any that were are reported
- [ ] Every entry: `make == "BMW"`, an explicit S1000RR/R/XR model
      string with generation, `source == "model-generated"`, "general
      knowledge" in the description
- [ ] No F-series or boxer component (Paralever, final drive housing,
      dry clutch, diode board, Rotax, ZFE, boxer) appears in the S1000
      file — asserted per term
- [ ] No fourth generic quickshifter entry unless it is demonstrably
      S1000-specific
- [ ] Symptoms are short phrases; real mechanic queries hit
- [ ] All three BMW files load together without collision
- [ ] Count guard fires on 684 → 684 + N; four docs updated
- [ ] Backend regression green; F9 lint clean

## Risks

- **Four litre-class peers already in the corpus make duplication the
  default failure mode**, not an edge case. The attribution refuter is
  explicitly briefed on it, but a generic entry that survives will read
  as plausible precisely because it is true of every superbike.
- **The S1000 line is electronics-dense and recent**, so the temptation
  to state specific fault codes and calibration figures is high. The
  figures lens is what stands against it; BMW-specific fault codes
  belong to Phase 215 regardless.
- **Three model-generated refuters do not make a service manual.** The
  process removes the obviously wrong and enforces consistency. Every
  entry stays tagged `model-generated`, and the CLI warns on each.
