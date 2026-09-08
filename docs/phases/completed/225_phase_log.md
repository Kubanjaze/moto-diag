# Phase 225 — KTM electrical + engine management — Phase Log

**Status:** ✅ Complete — closes the KTM block
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-225-ktm-electrical`

---

### 2026-09-07 — Step 0, researched and refuted facts, three surfaces, close

- **Step 0 was corpus-internal and complete before any research ran.**
  Four KTM compat rows, all partial or read-only; no KTM DTC file; the
  four earlier KTM tests forbidding `ECU|Keihin|TuneECU|Tuneboy|remap|
  reflash|P0xxx` as this phase's inbound fence; the 1290 file already
  making the generic read-access point. Three facts in the row's own
  wording were unverified — Keihin, Tuneboy, "PowerParts
  cross-platform" — plus the cylinder numbering 224 had refused to
  guess.
- **Ultracode was on, so the external facts went to a workflow rather
  than memory.** Five research agents with web access, each finding
  refuted by two lenses (source quality; contradiction search), with
  212's lesson built in: retry once, then `undecided`, never a fake
  verdict. **15/15 agents returned, 0 died.** Four findings survived
  both refuters. The tooling finding was refuted on its function-list
  detail only — identity, coverage and hardware held — and the
  refuters supplied the corrected per-model list.
- **The cylinder mapping was settled from KTM's own document, not a
  forum.** The research cited an unattributed transcription and a forum
  post for "cylinder 1 is the rear". Not enough to ship a misfire row.
  I fetched the official 950/990 repair manual and read the error table
  on p. 162 myself: P0201 injector **rear** / P0202 front, P0351 coil
  rear / P0352 front, P0130 lambda rear / P0150 front, P0122/P0123 TPS
  blink 06, P0560 supply voltage. The fifth refuter independently
  downloaded the same PDF and confirmed it, and added KTM's own P1590 =
  side-stand switch — which retroactively explained a 790 owner report.
  For the LC8c the side is **unknown**, and the rows say so.
- **A refuter caught an overreach in my draft.** I had written the
  TuneECU reset sequence as the fix "after throttle-body work". The
  contradiction refuter went back to the primary source: it is
  documented after a **map load**, on the 990/RC8 only; the
  throttle-cable adjustment is a cable-clearance procedure; and the
  CAN-bus 1050–1290 bikes get **no adjustments at all**. P0120, P0122
  and the throttle entry were corrected before the test was written,
  and the test now asserts the corrected wording.
- **Three roadmap corrections in one row.** "Keihin FI" holds for the
  LC8 from the 990, the LC4 690 and the EXC-F — and fails for the LC8c
  and every Bajaj-built bike (Bosch), the TPI two-strokes (Continental)
  and the TBI two-strokes (Vitesco). "Tuneboy" lists KTMs as a tune
  editor; TuneECU is the diagnostic tool, Keihin-era and pre-Euro 5
  only. "PowerParts cross-platform" is not a KTM term — it is shared
  article numbers across KTM, Husqvarna and GasGas. Fourth naming
  correction in the block.
- **Three surfaces shipped.** Eight DTC rows, six shadowing and every
  one differing from generic; blink codes asserted against the manual's
  set; P0560 rather than P0562 because that is the code KTM sets; the
  Dynojet orange-to-front harness trap named. Seven knowledge entries
  on the tool landscape, none restating the 1290 file's generic point.
  And **the adapter gap 221 left is filled**: `tuneecu-ktm-android`
  with 14 compat rows, every one citing TuneECU's own list — 3 full, 5
  partial (the CAN bikes: no adjustments, so not `full`), and 6
  **incompatible**, so a shop checking a 790 is told no rather than
  finding nothing. The 990% row is year-bounded so the Bosch 990 Duke
  cannot fall into it. The price is labelled as an EUR conversion.
- **221's guard was inverted deliberately.** It asserted four rows and
  no full-access option. It now asserts the four original rows survive
  unchanged and that the gap is closed. A guard should outlive the
  deliverable it was written for; this one outlived the *absence* it was
  written for.
- **No validator false positive** — the claim checks here were targeted
  regexes against sourced facts rather than the general prose helper.
  And one mechanical error of mine: I gave three DTC rows a category
  the enum does not have; the loader rejected it, and generic's own
  category for the same codes was the fix.
- 766 → 773; 33 KTM entries across five files; 45 phase tests;
  regression 5331/0; F9 clean.
- **Key finding: research changes what a phase can honestly say, in
  both directions.** It put a cylinder mapping on the table that 224
  had rightly refused to guess, and took a throttle-body claim off the
  table that I would otherwise have shipped.
- **Block closes with one open item**: the 390/790/890 Adventure line
  still has no roadmap row.
