# Phase 231 — Aprilia RSV4 / Tuono V4 — Phase Log

**Status:** ✅ Complete — opens the Aprilia + MV Agusta block
**Started:** 2026-09-08 | **Completed:** 2026-09-08
**Repos:** `Kubanjaze/moto-diag`, branch `phase-231-aprilia-rsv4`

---

### 2026-09-08 — Step 0, paired research, close

- **Aprilia had zero entries** across 824 — the four apparent hits were
  the Honda CBR600F file's "F2/F3/F4" generation labels, checked rather
  than counted. But the *topic* is saturated: V4 in 10 files, traction
  control and Öhlins in 15 each. So the backwards genericness test ran at
  full strength, with the counter-assertion swept corpus-wide.
- **Research was paired across two phases for the first time.** One
  capped 6-agent run answered both this phase's question and Phase 232's,
  since they share a make and the same sources — halving the number of
  runs across the block without exceeding the cap on any one.
- **Fifth consecutive block in which a badge is not a capacity.** No
  Aprilia V4 has ever displaced 1100cc: "1100" means 1077cc on the Tuono
  and the 2019–20 RSV4 1100 Factory, and 1099cc only from the 2021 RSV4.
  The two steps differ in kind — 1000→1077 is **bore only**, 1077→1099 is
  **stroke only** — so crankshafts and rods are affected by the later
  change and not the earlier. And Aprilia sold two displacements of the
  same model concurrently, so neither badge nor model year settles it.
- **A phantom recall number changed how the file cites campaigns.** The
  research attached a UK reference to a brake campaign; that number is a
  *Citroën* recall in the UK dataset, and the real campaign was a
  Canadian one given a UK prefix. Rather than curate a corrected list,
  the file cites **no campaign numbers at all** — entries describe what a
  campaign covers and route the reader to the frame number, which is the
  action to take anyway and which cannot go stale.
- **The best finding is a search failure rather than a fault.** A refuter
  checking the "UK-only" claim on the connecting-rod recall found a US
  counterpart the original search had missed, because the regulator files
  it under the make spelled **"APRILLA"**. A correctly spelled by-make
  lookup therefore returns clean on a machine whose published remedy is
  **engine replacement**. Second time a regulator's own data has been the
  hazard, after the Phase 228 index defect.
- **Eight entries**, two rated critical — the misspelled-make engine
  campaign and the front brake family. Also: **cylinder 1 is the left
  REAR** on the 65-degree longitudinal V4 with banks alternating, so a
  cylinder-1 code sends a mechanic backwards; the cam drive is chain to
  the intake cam with a gear pair to the exhaust and bank service
  positions at 150° and 450° rather than even increments; **three normal
  aPRC behaviours that read as faults**, including a dyno run latching
  the rider-aid lamp and the pit-lane limiter flashing the *immobiliser*
  lamp; recalibration after wheel, tyre or sprocket work; and charging
  failures as owner consensus rather than a campaign, with two
  non-interchangeable generator families that cannot be distinguished
  without pulling the cover.
- **Twelfth mention-versus-use slip**: a boundary check for the PADS
  diagnostic tool matched brake *pads*. Case-sensitive now.
- **Aprilia and MV adapter rows guarded at zero** for row 235, with a
  counter-assertion that other makes demonstrably have rows.
- 824 → 832; 34 phase tests; regression 5591 passed / 1 failed, then fixed — the single failure was the Phase 208 doc-count guard catching **my own error**: I wrote Phase 232's content file into the tree while this phase's regression was running, so the live seed count became 837 while the docs said 832. The guard is doing exactly its job. The file was backed out, the count re-verified at 832 and the failing test re-run green; the clean full-suite figure is recorded at Phase 232, which runs over the same tree plus that file; F9 clean.
- **I broke the regression myself, and the guard caught it.** To save
  wall-clock across a ten-phase run I began writing Phase 232's content
  while this phase's regression was still going. The Phase 208 guard ties
  the documented knowledge-base figure to the **live** seed count, so the
  extra file made the docs wrong by five. Content cannot be pipelined
  across a phase boundary for exactly that reason; the doc count is a
  whole-tree invariant, not a per-phase one. Backed out, re-verified,
  and the practice abandoned.
- **Key finding: a clean recall search can be a data artefact.**
