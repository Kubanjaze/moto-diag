# Phase 220 — Ducati electrical + FI — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-220-ducati-electrical`

---

### 2026-09-07 — Step 0, hand-drafted content, close

- **Step 0 removed a deliverable rather than adding one.** Phase 215
  (BMW electrical) shipped an adapter entry because the GS-911 was
  genuinely absent from the catalog, and I expected the same shape here.
  It is not: **eight Ducati compat rows across eight adapters** already
  exist, including the OEM `ducati-dds-readiness-tool`, and the catalog
  already records that CAN-FD on newer variants breaks counterfeit
  ELM327 silicon — the exact access problem this phase describes. So
  this phase touched **two** surfaces, not three.
- **The dropped deliverable is guarded, not just skipped.** A test
  asserts the catalog's Ducati rows are unchanged and that the DDS is
  still among them. Otherwise the next phase to look at Ducati tooling
  finds no record of why nothing was written and duplicates it.
- **Six DTC rows, every one shadowing deliberately.** `get_dtcs`
  resolves make-specific before generic, so a Ducati row that restates
  the generic one hides it — the finding that made 215 drop P0135. Each
  row is asserted to differ from the row it displaces in **both** causes
  and fix, and a live check confirms a Honda still resolves to generic.
- **L-twin cylinder identity is the content that justifies the file.**
  Cylinder 1 is the horizontal front cylinder, cylinder 2 the vertical
  rear — a mechanic reading P0301 as an inline engine's left-hand pot
  works on the wrong one. No generic misfire row can say this.
- **The mapping is guarded against itself.** Both misfire rows restate
  it, so a regex requires every statement of it to agree. One reversed
  sentence would be worse than saying nothing, because it is the
  sentence acted on. Verified it bites: a planted reversal is caught.
- **No proprietary number transcribed, no P1xxx invented** — the same
  line 215 held. Ducati's own fault numbering is described as a format
  and as the "no codes found is not no fault" trap; the five knowledge
  entries carry `dtc_codes: []`.
- **Five Ducati files now coexist**: monster, panigale, multistrada,
  desmo, electrical — 41 entries, no title collision.
- **My validator did not produce a false positive this phase**, ending
  a four-phase run. Worth recording without reading much into one
  sample; the claim-checking helpers from 217–219 were carried over
  unchanged and simply had less prose to run against.
- 740 → 745; 23 phase tests; regression **5168 / 0**; F9 clean.
- **Key finding: a guard should outlive the deliverable it was written
  for.** This phase's most useful assertion covers something it
  deliberately did not build.
