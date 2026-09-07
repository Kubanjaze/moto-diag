# Phase 212 — BMW GS adventure line (F-series) — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag` + mobile, branch `phase-212-bmw-gs-adventure`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit (as a workflow)

- **Step 0 ran as four independent agents**: an overlap reader across
  the whole seed, two premise checkers — one asked to *confirm* the
  roadmap row, one asked to *refute* the opposite claim — and a
  contract reader over the Phase 211 tests.
- **The roadmap row is wrong, and both checkers said so without seeing
  each other.** "Paralever final drive" does not exist on any F-series
  GS; every one from the 2000 F650GS single to the 2024 F900GS is
  chain-driven. Paralever is the boxer/K-series shaft swingarm, and the
  text is cross-contamination from the R-series row. That single fact
  invalidates the port of almost every Phase 211 topic — final drive
  bearing, Paralever pivots, splines, dry-clutch seals, belt alternator,
  servo ABS, diode board, brushed rotor. None has an F analogue.
- **Naming traps recorded so no entry lands on the wrong bike:**
  "F650GS" is a 652 cc Rotax single (2000–2007, chain on the right) *and*
  a 798 cc twin (2008–2012); "F800GS" is 798 cc (2008–2018) *and* 895 cc
  (2024+); no twin's displacement matches its badge. Every entry will
  carry an explicit model string — never bare "GS".
- **One real overlap, to be widened not duplicated:** the 211
  fuel-strip entry is scoped to R1200GS but the same part fails the
  same way on the F800 family.
- **Build discipline for this phase:** six independent drafters by
  lens, plain-code dedup against 211, then three refuters per candidate
  with distinct lenses (attribution / invented figures / safety), each
  defaulting to *refuted* when uncertain. An entry survives only if at
  most one refuter objects and the safety refuter does not. Agents
  return data; I write the files.
