# Phase 221 — KTM 1290 Super Duke / Super Adventure — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-221-ktm-1290`

---

### 2026-09-07 — Step 0, hand-drafted content, close

- **KTM had zero entries, but the topic is the corpus's most-covered.**
  745 entries across nine makes and not one KTM — yet **19
  rider-electronics entries** already exist, and the Harley RevMax
  "cornering ABS / TC false intervention" entry is already the generic
  form of what a KTM cornering-ABS entry would say. The hazard this
  phase faced was **duplication, not fabrication** — the inverse of
  every phase since 211.
- **So the genericness test runs backwards** (the Phase 219 shape):
  every entry must **name** 1290 hardware rather than merely avoid a
  shared topic, counted as **distinct terms** so repeating "KTM" cannot
  satisfy it. The counter-assertion is what makes it mean anything —
  the RevMax entry is run through the same check and scores **zero**.
- **My own check caught my own first draft.** Five of seven entries
  scored a single distinct term, all of it from the title: the bodies
  were generic content wearing a KTM badge. I cut the
  tyre-circumference entry outright — its mechanism is universal and a
  make file is the wrong home for it, where a Honda owner would never
  find it — and rewrote two others with real KTM anchoring rather than
  keyword-stuffing to clear a threshold. **11 candidates drafted, 6
  shipped.** Semi-active suspension was cut early: four entries already
  exist, including the Panigale Öhlins one.
- **MSC is the fact that justifies the file.** It appeared **zero
  times** in 745 entries. Motorcycle Stability Control is a **Bosch
  supplier system** that KTM put into production first, unlike the
  in-house Japanese systems (KTRC, HSTC, Motion Track) the corpus
  already documents — so the sensor set and conventions follow the
  Bosch unit, not a KTM black box.
- **The roadmap row conflated two model lines.** It read "R/GT
  variants" while naming both bikes. GT is a **Super Duke**
  designation; the Super Adventure has base, S, R and T, and **never a
  GT**. Milder than the four Ducati corrections, which named mechanisms
  the engines do not have — this is a conflation, not a wrong
  mechanism. It still matters: a Super Adventure S runs a 19-inch front
  and the R a 21-inch.
- **The adapter gap is left for its owner and guarded anyway.** Four
  KTM rows, all `partial` or `read-only`, **no full-access option** —
  a genuine gap of the kind Phase 215 filled for BMW. But Phase 225
  owns KTM tooling, so filling it here would pre-empt that phase rather
  than duplicate a covered surface. The row count is guarded at 4, a
  counter-assertion confirms BMW and Ducati demonstrably *do* have
  full-access rows, and roadmap row 225 is annotated. This is the
  inverse of Phase 220, where the surface was already covered.
- **Fifth consecutive phase where my validator produced a false
  positive**, and a new member of the family: it flagged "if a customer
  or a listing **says** Super Adventure GT" as asserting the bike
  exists. Phase 218 handled reports by treating symptoms as reports,
  but a report can sit inside an assertion-bearing field — a fix
  procedure telling a mechanic what a customer will say is the obvious
  case. Reported speech is now exempt, and verified not to neuter the
  check: a planted "The Super Adventure GT uses a 19-inch front wheel"
  is still caught.
- 745 → 751; 29 phase tests; regression **5197 / 0**; F9 clean.
- **Key finding: a validator over prose must exempt reported speech,
  not just negation.** Quoting someone's error is not making it.
