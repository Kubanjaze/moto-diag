# Phase 214 — BMW K-series touring — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
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
