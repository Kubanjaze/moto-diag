# Phase 212 — BMW GS adventure line (F-series) — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
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

### 2026-09-07 — Built. The refuters caught what the avoid-list could not.

- **The first content run reported 0 survivors and it meant nothing.**
  45 of 57 agents died on a session limit, and my aggregation counted a
  `null` verdict as `{refuted: true, problem: 'fatal'}` — so an outage
  read as unanimous refutation and killed all 17 candidates. That is a
  harness defect, not a content result. Fixed before retrying: a dead
  refuter is retried once, then **excluded from the vote**; fewer than
  two real verdicts yields `undecided`, reported rather than dropped.
  The resumed run replayed the six drafters from cache and returned
  58/58 agents, **0 undecided**.
- **17 drafted → 14 survived → 12 kept.** Three drops, each caught by
  the lens built for it:
  - **Fuel pump controller on the 798cc twins — fatal on two lenses.**
    A discrete potted FPC module is Hexhead R1200 / K1200 hardware; the
    F-twins drive the in-tank pump through an ECU relay. The entry sent
    a mechanic hunting a part the bike does not have and cited a recall
    never run against those VINs. **The drafter had the explicit
    "do not port R-series hardware onto an F" instruction in front of
    it and did it anyway** — with correct model strings and correct
    year spans, which is what makes that error class dangerous. Safety
    independently rated it fatal: a heat gun beside an under-seat fuel
    tank whose flange the same entry called prone to weeping.
  - **Rotax 652 water-pump seal** — undeclared 3.5-hour estimate, and
    draining coolant with no cold-engine instruction on a pressurised
    system.
  - **F800GS fork seals** — specification-grade figures neither
    declared nor marked for manual confirmation.
- **Two more cut at synthesis** to fit the cap: a weaker duplicate of
  the rear-wheel-bearing entry, and an accessory-socket entry that
  described normal ZFE behaviour rather than a fault.
- **Symptoms had to be normalised.** The drafters returned full
  sentences (mean 85 chars); `find_issues_by_symptom` is a SQL LIKE
  match, so "chain slap" would never have found the chain-slider entry.
  Rewritten to the corpus's short-phrase form (mean 22 chars), and a
  safety caution misfiled inside a symptoms array moved into the fix
  procedure. Format only — no substance changed.
- **The roadmap row was wrong and is corrected**: "paralever final
  drive" → chain. The test file now asserts that ten boxer-only
  components appear nowhere in the F-series file, with a
  counter-assertion that "paralever" *does* still appear in the
  R-series file so the check cannot silently pass on an empty corpus.
- **The 211 fuel-strip entry was widened, not duplicated** — four-line
  diff, 211's tests still green, and 212 asserts no F entry re-tells it.
- 12 entries (2 single-cylinder, 7 F800GS, 3 F750/F850GS); 672 → 684;
  regression 4964 / 0;
  34 phase tests; F9 lint clean.
- **Key finding: one drafting pass would have shipped a confidently
  wrong entry.** What killed it was a second agent whose only job was
  to disbelieve the first. The secondary finding is about harnesses: a
  survival rule that cannot tell "the refuter disagreed" from "the
  refuter died" will report a confident zero.
