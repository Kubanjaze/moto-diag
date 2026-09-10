# Phase 244 — Energica — phase log

**Status:** Planned
**Opened:** 2026-09-09

---

## 2026-09-09 — Plan v1.0 written

Third make-specific electric phase, and the first opened around **named doubts
rather than a general sweep** — Phase 243 established that a doubt assigned as
a required output field beats breadth at a seventeenth of the cost, and Step 0
found two of them sitting in shipped source code.

**Step 0 — content: nothing.** A precise scan for `Energica` returns only Phase
241's HV safety floor. No make-specific content anywhere.

*(My first scan used `\bEgo\b` and `Esse` as tokens and returned sixty-odd
files. `Esse` matches inside "assessed"; `Ego` matches ordinary prose. Recorded
because the false positive was mine and the next reader should not repeat it.)*

**Step 0 — code: two unsourced claims about Energica are already shipping.**

**Doubt A.** `engine/fault_codes.py` defines `ELECTRIC_HV` with the comment
"Zero/LiveWire/Energica HV battery/motor DTCs (HV_, MC_, BMS_ prefixes)" and
repeats the attribution at line 194. Measured: **zero of the 99 seeded DTC
codes use that format**, and its only occurrences anywhere are Phase 111 test
fixtures. So the namespace is a project invention — defensible as an internal
convention — but the comment attributes it to three named manufacturers, and
this track's own work has now contradicted two of them. Phase 242 established
Zero publishes its codes as a numbered owner's-manual table; Phase 243
established LiveWire's are dash-readable but need Digital Technician II to
interpret. Neither uses an `HV_` prefix. Whatever the research finds for
Energica, the comment is wrong about at least two of the three makes it names.

**Doubt B.** `media/sound_signatures.py` asserts "Energica uses an oil-cooled
PMSM (8 pole pairs)" and gives Zero SR/F and LiveWire One as 4 and 8 pole pairs
— inside a signature that instructs a technician to compute motor whine
fundamental as motor_RPM × pole_pairs / 60. Measured: no code consumes the
figure, so nothing computes with it today, but it is written as fact and tells
a human to compute with it. A wrong pole-pair count produces a wrong expected
frequency and a misdiagnosis.

Both doubts are assigned as **required output fields** of the two research
questions rather than left for breadth to surface. Research runs the Track K
cadence (2 questions × 2 lenses = 6 agents) on the canonical lenses in
`docs/phases/RESEARCH_LENSES.md`, with survivors grouped by `source_class`
before any entry is written.

`make = "Energica"` — unambiguous, and it joins 241's HV floor cleanly. No
brand split as at 243, and no combustion namesake to be buried under.

Baseline before any work: **6066 passed / 0 failed** (Phase 243).

Plan v1.0 written to `docs/phases/in_progress/244_implementation.md`.
