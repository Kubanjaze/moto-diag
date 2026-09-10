# Phase 244 — Energica — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-09 | **Closed:** 2026-09-09
**Repo:** https://github.com/Kubanjaze/moto-diag

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

---

## 2026-09-09 — Build complete

**Both named doubts were refuted.** 6 agents, 0 errors, ~720K subagent tokens.
28 claims, 23 survived, 0 unverified; 18 manufacturer-document, 2
regulator-record, 2 community-report, 1 not-established — no lens skew.

**Doubt A.** Energica publishes 110 fault codes in its owner's manual in
standard SAE J2012 form — P/B/C/U plus four alphanumerics, no underscore, no
prefix — and supports OBD Modes 1-4 and 9 under the EU repair-information duty,
so a generic scan tool reads and clears them. That makes Energica the one make
of the three where an ordinary tool works, which is the most operationally
useful thing in the phase. A full-text search for the `HV_` family across the
manual, the manufacturer's diagnosis sheet and an owner-compiled table returned
zero hits.

The researcher also identified *how the error was made*: "HV" and "BMS" appear
in Energica's table in the DESCRIPTION column, never the code label — P1010 is
"HV+ CONTACTOR SHORT CIRCUIT", P0516 is "BMS TEMPERATURE SENSOR SHORT CIRCUIT
FAULT". Pattern-matching description text yields prefixes nobody uses.
`fault_codes.py` now documents the namespace as internal and records what each
make actually emits.

**Doubt B.** No Energica source states a pole count anywhere — zero occurrences
of "pole" in the 126-page manual, none in archived or current spec tables,
none in secondary coverage. Three further defects sat behind the missing
number: wrong motor type for most of the range, wrong physics for the symptom
(the formula gives the electrical fundamental, not audible whine), and motor
rpm not derivable from wheel speed. Withdrawn from `sound_signatures.py`, with
all four findings recorded where the figure used to be.

**I was wrong about the blast radius and my own guard caught it.** Plan v1.0
said the pole-pair figure "is not consumed by any code". A public function
computes exactly this, with per-make worked examples in its docstring. My grep
had excluded `sound_signatures.py` while looking for uses *outside* the
signature text, which hid the function in the same file.

**Four of five guards were vacuous on first write.** The figure guard asked
whether *some* document was named rather than whether *this figure* was
sourced. The price guard matched currency symbols when the withheld figures
were written `USD 500` and `USD 2,500`. The attribution guard filtered to lines
containing an underscore, so `"for HV faults"` was skipped entirely. The pole
guard scanned a 400-character window inside a docstring full of attribution
words. All four repaired; all five mutations now fail on mutation and pass on
revert.

**And repairing the attribution guard immediately produced a
mention-versus-use failure** — the widened guard flagged the correction itself,
because the correction quotes the wrong attribution in order to refute it. It
is now block-scoped and judges each occurrence on what precedes it, with
anti-vacuity assertions in both directions.

**12 entries**, 10 `service-manual` and 2 `forum`. Beyond the two doubts they
cover: the motor differing by generation with Energica's own pages
contradicting each other; the 110-code table and generic OBD access; EV live
data through standard PIDs; the owner-readable dash procedure and the four
power cycles a MIL needs to clear; service intervals that exist per generation
but print no figure here because the current schedule is unpublished; pack
capacity and cycle basis; the chain final drive; DC fast charging; and two
community entries. **Two entries exist because of what is missing** — that no
pole count is published, and that the manufacturer currently publishes no
manual, schedule or warranty at all following liquidation.

Corpus 958 → 970; four user docs moved under the Phase 208 guard. F9 lint
clean. This phase touched **two source files** as well as seed data, a wider
blast radius than 241-243.

Regression: **6087 passed / 0 failed** (baseline 6066; +21 guards).
