# Phase 213 — BMW S1000RR / S1000R / S1000XR

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

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

- [x] The workflow ran 3 refuters per candidate: **18 drafted → 18
      after dedup → 6 survived → 6 kept**, **0 undecided**, 61 agents,
      0 errors. Every drop reason is recorded below
- [x] All 12 drops were **fatal on attribution** — no other lens cast a
      fatal verdict on any candidate
- [x] Every entry: `make == "BMW"`, explicit model string with
      generation, `source == "model-generated"`, "general knowledge" in
      the description
- [x] No foreign-platform component (Paralever, Telelever, final drive
      housing, crown wheel, dry clutch, diode board, Rotax, ZFE, boxer,
      cardan) appears — asserted per term, with a counter-assertion
      that the R-series and F-series files still own those terms
- [x] No fourth quickshifter entry — asserted on titles
- [x] `dtc_codes` empty on every entry; BMW fault codes stay Phase 215's
- [x] ShiftCam never attributed before 2019; XR vibration never
      attributed to the revised 2020+ bike — both asserted
- [x] Symptoms arrived contract-clean (mean 28 chars, max 39) with **no
      manual normalisation needed**, unlike Phase 212
- [x] All three BMW files load together to 30 with no title collision
- [x] Count guard fired on 684 → 690; four docs updated
- [x] 36 phase tests; F9 lint clean; backend regression green

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


## Deviations from Plan

**Six entries, not the ~12 the plan projected — and that is the
result, not a shortfall.** 18 candidates were drafted and 12 were
killed, every one of them **fatal on attribution**. No other lens cast
a single fatal verdict. The plan named duplication as this phase's
default failure mode; the refuter agreed, twelve times.

The drops divide into two kinds:

1. **Generic superbike failures wearing a BMW badge (the majority).**
   The clearest is *"Second gear jumps out under load on early
   S1000RR (K46)"* — the refuter's verdict was that worn engagement
   dogs, worn selector forks and a tired detent spring are "the
   archetypal sport-bike transmission complaint — equally true of a
   ZX-10R, R1 or GSX-R1000", with no BMW part nomenclature, no
   K46-specific detail, and a diagnostic sequence that is generic
   workflow rather than model knowledge. Four separate DDC
   semi-active-suspension entries died the same way: attribution
   mechanics *clean* — right generation, right option availability, no
   ported hardware — but "strip the BMW badge and the entry is the
   standard semi-active-suspension failure story."
2. **Unverifiable recall claims.** Two entries rested on specific NHTSA
   campaign identifiers asserted rather than confirmed for this model,
   one of which also ported a cracked fuel-pump-flange story from the
   boxer and big-tourer families onto the K67 sportbike tank. An entry
   whose entire diagnostic value is a recall number has to have the
   number right.

**Two whole lenses produced no survivor.** The RR 2015–2018 and S1000R
drafts were entirely refuted, so those generations are simply **absent
from the file rather than invented**. The synthesizer said so
explicitly instead of padding to the cap, which is the correct
behaviour: it cut nothing, because there was nothing above the bar.

**The symptom contract worked.** Phase 212's drafters returned full
sentences and I normalised ~60 strings by hand. Moving the rule into
the JSON schema field description — with the reason stated ("matched
with SQL LIKE against a mechanic's typed query, so a sentence never
matches") — produced compliant output first time: mean 28 characters,
max 39, zero manual edits.

**The undecided state was carried forward and never fired.** 61 agents,
0 errors, 0 undecided — so no candidate's fate was decided by an
outage, which was the defect that made Phase 212's first run
meaningless.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 684 → 690 |
| S1000 entries | 6 (2 K46, 2 ShiftCam, 2 S1000XR first-gen) |
| Drafted → survived → kept | 18 → 6 → 6 |
| Fatal drops, all on attribution | 12 |
| Generations with no survivor | RR 2015–2018, S1000R |
| Undecided | 0 |
| Agents / errors | 61 / 0 |
| Phase tests | 36 |
| Backend regression | 5000 passed / 0 failed |

**Key finding: a saturated corpus makes "specific enough to be worth
adding" a much harder bar than "true".** Every one of the twelve
rejected entries was plausibly *correct*; they were rejected for being
correct about motorcycles in general rather than about these
motorcycles. With four litre-class peers already in the seed, the
marginal value of a generic litre-bike entry is zero and its cost is a
mechanic's trust — so the honest output of this phase is six entries
and two openly empty generations, not twelve padded ones.
