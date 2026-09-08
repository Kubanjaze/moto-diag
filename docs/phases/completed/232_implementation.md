# Phase 232 — Aprilia Dorsoduro / Shiver / SR Max

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Cover Aprilia's 90-degree V-twin pair — the Dorsoduro supermoto and the
Shiver naked — and settle what to do with the SR Max scooter that shares
their roadmap row.

CLI: `motodiag kb list --make aprilia`; guard is
`pytest tests/test_phase232_aprilia_dorsoduro.py`.

Outputs:
- `known_issues_aprilia_dorsoduro.json`
- `tests/test_phase232_aprilia_dorsoduro.py`
- Roadmap row 232 corrected as the research dictates
- Documented known-issue count updated (832 → 837)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. Aprilia now has one file — Phase 231's eight RSV4 and Tuono
entries.** This phase must not collide with it, and the two share a make
but not an engine: 231 is the 65-degree V4, this is the 90-degree
V-twin. The vee angle, the cylinder numbering and the rider-aid package
are all different, so nothing carries across and the guard asserts no
symptom resolves to both files.

**2. The research for this phase was already run.** Phase 231's capped
6-agent workflow carried two questions, one per phase, and both findings
were refuted by two lenses each. This phase writes from the survivors of
that run rather than launching a second one — the point of pairing.

**3. The row groups a scooter with two motorcycles.** Row 232 reads
"V-twin supermoto (Dorsoduro), naked (Shiver), scooter (SR Max)". The
first two are one engine in two chassis. The **SR Max is a maxi-scooter
with a single-cylinder engine and a continuously variable transmission**
and shares nothing with them. That is a machine-class difference before
it is a model difference, and it decides whether a workshop can quote the
job at all — so it is written as its own entry rather than absorbed.

**4. What the research established that the corpus lacks.** The Shiver's
ride-by-wire is an early, unusual implementation whose **self-learning
routine runs at every key-on**, so a weak battery produces a throttle
fault before the machine moves. And the widely repeated claim that these
bikes suffer chronic fuel-pump and charging failure is **not supported by
any of three national recall databases** — while two genuine safety
campaigns, on the gearbox output shaft and the front brake master
cylinder, are. That negative finding is worth as much as the positive
ones, because it changes what a shop tells a used buyer.

**5. Boundaries.** 231 owns the V4 machines, 233 and 234 the MV Agustas,
235 the tooling and fault codes for both makes. Aprilia and MV adapter
rows stay guarded at zero. `dtc_codes: []` throughout.

**6. Content is not pipelined across the phase boundary.** Phase 231's
regression failed on the Phase 208 doc-count guard because this phase's
content file was written into the tree while that regression ran — the
documented figure is tied to the **live** seed count, which is a
whole-tree invariant. The file was backed out and restored here after
231 was committed.

## Logic

1. Write from the refutation survivors of the paired run.
2. Keep the scooter as its own entry, stating the machine-class
   difference plainly.
3. Validate: designation bar with a corpus-wide counter-assertion, no
   symptom shared with the RSV4 file, the negative recall finding
   asserted, deferral boundaries, adapter rows at zero.

## Key Concepts

- **One engine, two chassis** — and a scooter that is neither.
- **A negative finding can be the most useful entry** when folklore says
  otherwise.
- **Longitudinal vee means front and rear cylinders**, and per-cylinder
  codes are read onto the wrong one by transverse habits.
- Claim checks run on assertion-bearing fields only (twelve phases).

## Verification Checklist

- [x] Every entry names a Dorsoduro/Shiver/SR Max designation in title
      and body, with a corpus-wide counter-assertion
- [x] No symptom resolves to both Aprilia files
- [x] The scooter's machine-class difference is stated explicitly
- [x] The negative recall finding is present and says which campaigns
      *do* exist
- [x] No campaign numbers (the Phase 231 decision, carried forward)
- [x] No 231 content (RSV4/Tuono/aPRC/V4), no MV content, no 235 content
      (tooling, codes); `dtc_codes: []`
- [x] Aprilia and MV adapter rows still zero
- [x] Regression green; F9 clean

## Risks

- **Collision with the Phase 231 file** is the sharpest hazard — same
  make, different engine, and the temptation is to reuse framings.
- **The negative finding could be over-claimed.** It says the databases
  consulted hold no such campaign, not that no such failure occurs.
- **No independent reader**, as in 217–231.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 832 → 837 |
| Entries | 5, all `service-manual` |
| Research runs launched by this phase | **0** — written from Phase 231's paired run |
| Campaign numbers in the file | 0 (the Phase 231 decision, carried forward) |
| Phase tests | 31 |
| Backend regression | 5623 passed / 0 failed |

**Pairing paid off.** This phase launched no research of its own: Phase
231's capped 6-agent run carried a second question written for this
phase, and both findings were refuted by two lenses each. Two phases,
one run, the cap respected on each — and the second phase costs only the
writing.

**The most useful entry is a negative finding, and it needed care.**
Chronic fuel-pump and charging failure is widely claimed for these
machines and appears in none of three national recall databases. Stated
carelessly that becomes "these bikes are fine", which is the mirror of
the folklore it corrects. Stated carefully it is: no such campaign in the
databases consulted, and here are the two campaigns that *are* there — a
gearbox output shaft that can let the front sprocket fastening loosen
with the rear wheel able to lock, and a front brake master cylinder that
can drag or self-apply with no brake light. An absence is only useful
next to the presences, because the frame-number check needs a target.

**The scooter was separated rather than absorbed.** The row groups the
SR Max with two motorcycles; it is a maxi-scooter with a single-cylinder
engine and a continuously variable transmission, which is a machine-class
difference before it is a model difference and decides whether a
workshop can quote the job at all.

**Key finding: an absence is only useful next to the presences.**
