# Phase 214 — BMW K-series touring — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-214-bmw-k-series`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit (inline)

- **Completely greenfield.** Not one occurrence of K1200, K1300, K1600,
  Duolever or Telelever across 690 entries. **Neither front end is
  covered anywhere in the corpus**, which makes Duolever/Telelever the
  clearest marginal value this phase can add — the opposite of Phase
  213, where everything generic already existed four times over.
- **The verification risk inverts.** Phases 212 and 213 policed
  misattribution: Paralever and servo ABS on an F-series or S1000 are
  hardware those bikes do not have. The K-series genuinely IS
  shaft-driven with Paralever and genuinely did carry Integral ABS, so
  those references are correct here. The risk that replaces it is
  **duplicating the existing R-series file**, which already covers
  Paralever pivots, Integral ABS pump failure, final-drive bearings and
  input-shaft splines.
- **Five R-series entries touch shared hardware**; the precedent from
  Phase 212 applies — widen the existing entry rather than write a
  second one, as was done for the fuel-level strip sensor.
- **A wrinkle in the roadmap row, milder than 212's.** Row 214 lists
  "K1200RS, K1200GT, K1300S, K1600GT/GTL inline-6, Duolever front", but
  the K1200RS (1997-2005) is the longitudinal Telelever generation —
  Duolever arrives with the transverse K1200S in 2005. The row reads as
  a topic list rather than a claim about all four, so it is not wrong
  the way 212's was; an entry putting Duolever on a K1200RS would be.
- **Method:** the same verified workflow the user selected at Phase 213,
  with the attribution refuter re-briefed for the inversion — it is told
  outright that shaft drive, Paralever and Integral ABS are legitimate
  K hardware, and its scepticism moved to generation errors and to
  duplication of the R-series file.

### 2026-09-07 — Built. The inverted guardrail held.

- **20 drafted → 14 survived → 11 kept. 67 agents, 0 errors, 0
  undecided.** Six fatal drops, **every one attribution-for-genericness
  and not one for mentioning Paralever, shaft drive or Integral ABS** —
  exactly the references a Phase 212-style refuter would have killed on
  sight. Telling the refuter outright that those are real K hardware,
  and moving its scepticism to generation and duplication, is what made
  the phase possible.
- **The replacement lens was doing real work, not just permitting
  things.** An in-tank fuel-plumbing entry died because "a Gold Wing, an
  FJR1300 and a Concours all have it"; a transverse-K1200 gearbox entry
  died because its procedure "reads identically on any wet-clutch bike
  with hydraulic actuation" and the corpus covers it three times in
  `cross_platform_drivetrain`. One verdict cited the R-series
  dry-clutch spline entry *by file path* to confirm a candidate's
  cross-reference was accurate.
- **`widen_existing_instead` produced 40 opinions and zero actions —
  which is the finding.** The field existed so a refuter could say
  "widen the R-series entry instead of writing a K one", following the
  Phase 212 fuel-strip precedent. Every BMW-facing suggestion said do
  **not** widen, with reasons: Paralever pivot wear "must NOT be widened
  to cover [Duolever] — Paralever is the rear suspension"; the Telelever
  ball-joint entry has "no existing entry [that] can absorb it". The
  only affirmative suggestions pointed at generic cross-platform entries
  owned by other phases, and attached to candidates dropped anyway. The
  mechanism ran and correctly concluded the K's front ends and driveline
  are genuinely distinct.
- **Duolever and Telelever are now covered for the first time** — no
  entry anywhere in the corpus previously described either, and the
  file states plainly that neither has stanchions to pit or fork seals
  to weep, which is the reflex these entries exist to interrupt.
- **My validator was wrong before the content was.** The first pass
  raised nine failures — "Duolever" on a Telelever bike, "boxer"
  present at all. All false positives: the entries name the other front
  end in explicit scope notes and cite the boxer to *contrast* with it.
  The check now tests what an entry **claims about its own bike** (a
  Duolever *title* must name a transverse model) rather than which
  words appear. Three of my first five search needles were also
  invented rather than read from the shipped data, and missed.
- 11 entries; 690 → 701; 32 phase tests; regression **5032 / 0**; F9
  clean.
- **Key finding: a guardrail that is right for one platform is a
  liability on the next.** "Paralever here is an error" caught a real
  defect in 212 and would have destroyed 214. Rules learned from one
  phase have to be re-derived against the next phase's hardware, not
  inherited.
