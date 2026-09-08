# Phase 222 — KTM Duke naked line — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-222-ktm-duke`

---

### 2026-09-07 — Step 0, guard repair, hand-drafted content, close

- **A guard I wrote last phase failed the moment this one landed, and
  that was my error.** Phase 221's `test_this_is_the_first_ktm_file`
  asserted no `known_issues_ktm_*.json` sibling may exist. The fact was
  true and worth recording — KTM had zero entries, the block opened
  there — but the encoding said something else and could not survive the
  block growing. Phase 220's own finding is that a guard should outlive
  the deliverable it was written for; this one was written so that it
  cannot. Rewritten to assert what was meant: the 1290 file keeps its six
  entries and does not collide with a sibling's titles.
- **Two roadmap findings, both from Step 0.** First, the **690 Duke**
  was in neither row 222's list nor row 223's, which names the 690
  *Enduro R*. By body style it is a Duke naked and belongs in 222 — and
  the adapter catalog already carries a `690%` row labelled "690 Duke /
  Enduro", so the model was known to the system while absent from the
  content roadmap. Second, **the LC8c is a parallel twin**: row 224
  reserves its three topics for the "LC8 V-twin", but the 790/890 use
  the LC8c, so as written 224 does not cover the Duke twins' engine.
  Row 222 corrected, rows 223 and 224 annotated, and all three reserved
  topics avoided here so nothing is written twice whichever way 224 is
  later scoped.
- **The specificity bar was recalibrated rather than copied or
  lowered.** Phase 221 required three distinct 1290 terms, and that was
  right for a vocabulary containing MSC, Bosch and Super Adventure. The
  Duke line has none of those, and entries here score two to four on the
  same style of count. Dropping the number would have been the failure
  221 avoided, so the bar changed shape: every entry must name a **model
  or engine designation** — LC8c, LC4, 790 Duke, RC 390 — in its
  **title** as well as its body. Brand-name padding cannot satisfy that,
  and the corpus's existing parallel-twin entry scores zero against it.
- **The first draft had no diagnostic content at all.** All five entries
  were identification, sourcing or cross-reference — a thin shape for a
  known-issues file. One was cut for restating the other three plus
  Phase 221's variant entry, and an **uneven-firing-beat** entry added
  as the file's spine: the LC8c's offset crankpin produces a lope that a
  technician used to an evenly firing twin reads as a misfire, and the
  tell is that designed character is regular in its irregularity while a
  real misfire varies with load and temperature.
- **The manufacturing-origin entry is the one that could have gone
  wrong.** That the 125 and 390 are built by Bajaj in India is a
  legitimate **parts-sourcing and specification** fact and an
  illegitimate proxy for quality. It is written as the former, says
  outright that it is not evidence about the machine, and is guarded by
  a test that fails on quality vocabulary and requires the disclaimer to
  be present.
- **"Super Duke" contains "Duke".** A bare `\bDuke\b` assertion matches
  the entire Phase 221 file. Every model assertion here is anchored to a
  number, with a counter-assertion that the 1290 file does still contain
  the prefix — the trap is real, not hypothetical.
- **Sixth consecutive phase where my own check, not the content, was at
  fault**, and a new family member: **comparison**. It flagged "the
  throttle feel of a V-twin" as asserting the LC8c is one. That
  sentence is the entry's whole purpose — explaining why an experienced
  rider gets it wrong. Similes before the term and attributive uses
  after it are now exempt, alongside negation (216/219) and reported
  speech (221). Verified on eleven hand-built discrimination cases: four
  genuine claims still flagged, seven comparisons and quotations not.
- 751 → 756; 32 phase tests; regression 5229/0; F9 clean.
- **Key finding: a validator over prose must exempt comparison, not just
  negation and reported speech.** Saying what a thing resembles is not
  saying what it is.
