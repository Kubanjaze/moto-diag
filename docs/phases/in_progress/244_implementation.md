# Phase 244 — Energica (Ego, Eva, Esse, Experia)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-09

## Goal

The third make-specific electric phase. Energica is the Italian premium
electric marque — Ego, Eva/EsseEsse9, Experia — and the one whose engineering
diverges most from the other two Track L makes: an oil-cooled PMSM rather than
an air-cooled motor, DC fast charging as a design centre rather than an option,
and a documented racing lineage through MotoE.

**This phase opens with two named doubts rather than a general sweep**, because
Phase 243 established that a doubt assigned as a required output field beats
breadth at a seventeenth of the cost. Both are unsourced claims about Energica
already shipping in this product's source code.

CLI: no new commands.

Outputs:
- `known_issues_energica.json`
- `tests/test_phase244_energica.py`
- a resolution for each named doubt — corrected, confirmed, or recorded as
  unestablished
- the research record, with rejected claims and reasons

## Logic

### Step 0 — what exists

**Content: nothing.** A precise scan for `Energica` across every knowledge,
DTC, compat, parts and template file returns only Phase 241's HV safety floor
(10 entries, where Energica appears in the shared `make` field). No
make-specific content of any kind.

*(A first scan using `\bEgo\b` and `Esse` as tokens returned sixty-odd files
and was discarded: `Esse` matches inside "assessed", and `Ego` matches ordinary
prose. Recorded because the false positive was mine and a later reader
repeating the scan should not repeat it.)*

**Code: two unsourced claims, and they are the doubts this phase must settle.**

**Doubt A — the fault-code format.** `engine/fault_codes.py:48` defines
`ELECTRIC_HV = "electric_hv"` with the comment *"Zero/LiveWire/Energica HV
battery/motor DTCs (HV_, MC_, BMS_ prefixes)"*, and line 194 repeats *"Used by
Zero, LiveWire, Energica for HV battery / motor controller / inverter faults"*.
The matcher at line 195 recognises `^(HV|MC|BMS|INV|CHG|REG)_[0-9A-Z]{2,5}$`.

Measured: **zero of the 99 seeded DTC codes use that format.** Its only
occurrences anywhere are test fixtures (`HV_B001` in the Phase 111 tests). So
the format is a project invention — which is defensible as an internal
namespace — but the comment attributes it to three named manufacturers, and
that attribution is now contradicted twice by this track's own work. Phase 242
established that Zero publishes its fault codes as a numbered table in the
owner's manual, not a machine-readable vocabulary. Phase 243 established that
LiveWire's codes are readable on the dash but need Digital Technician II or the
purchasable electrical diagnostic manual to interpret. Neither uses an `HV_`
prefix.

The research must establish what Energica actually publishes. Whatever it
finds, the comment is wrong about at least two of the three makes it names and
this phase corrects it.

**Doubt B — the motor specification.** `media/sound_signatures.py:321` asserts
*"Energica uses an oil-cooled PMSM (8 pole pairs)"*, alongside *"Zero SR/F and
LiveWire One use permanent-magnet synchronous motors (4 and 8 pole pairs
respectively)"*. The surrounding signature text tells a technician to compute
motor whine fundamental as `motor_RPM × pole_pairs / 60`.

Measured: the figure is not consumed by any code outside that signature string,
so nothing computes with it today — but it is written as fact and instructs a
human to compute with it. An incorrect pole-pair count yields an incorrect
expected frequency and a misdiagnosis. The research must establish Energica's
motor type and pole-pair count from a manufacturer source, or the claim is
withdrawn rather than left standing unsourced.

### Research

Track K cadence — 2 questions × 2 adversarial lenses = 6 agents — using the
canonical lenses in `docs/phases/RESEARCH_LENSES.md`. **Both doubts are
assigned as required output fields**, not left to breadth.

Question A covers manufacturer documentation, the platform range and the
service route, and must answer Doubt B (motor type and pole pairs).
Question B covers regulator records, owner community and the diagnostic route,
and must answer Doubt A (what Energica publishes as fault codes, and in what
form).

Survivors are grouped by `source_class` before any entry is written; if one
class approaches 100%, the lens is suspect, not the corpus.

### The `make` decision

`make = "Energica"`. Unambiguous, matched by `%Energica%`, and it joins 241's
HV floor cleanly — which already carries Energica in its shared make field. No
brand-split problem here, unlike Phase 243, and no combustion namesake to be
buried under, unlike Harley-Davidson.

## Key Concepts

- **A named doubt beats breadth** (243). Both doubts are output fields.
- **A figure carries its document or it is withheld**, per the class-matched
  standard (238 → 241 → 242B).
- **Campaigns by mechanism, never by reference number** (231).
- **Scope by ownership**: 246/247/249 own generic BMS, inverter and thermal.
  Energica's oil-cooled motor is in scope as *Energica's*; how oil cooling
  works in general is not.
- **An unsourced claim in code is still an unsourced claim.** The corpus has a
  provenance discipline; source comments have had none.

## Verification Checklist

- [ ] Doubt A resolved: `fault_codes.py`'s manufacturer attribution corrected,
      with the internal-namespace status stated plainly
- [ ] Doubt B resolved: the pole-pair and motor claims sourced, corrected, or
      withdrawn — never left unsourced
- [ ] Every printed figure names its document under the class-matched standard
- [ ] Survivors grouped by `source_class` and the distribution checked
- [ ] No campaign reference number anywhere
- [ ] `make="Energica"` returns the file and 241's HV floor, critical first
- [ ] Provenance honest per entry; forum-tip biconditional
- [ ] Count guards and the four user docs move together
- [ ] Every new guard mutation-tested
- [ ] Full regression at or above 6066, 0 failed

## Risks

- **Correcting `fault_codes.py` touches shipped source, not seed data.** The
  matcher itself is exercised by Phase 111 tests and must keep working; only
  the manufacturer attribution is in question. The change is to comments and,
  if warranted, to the enum's documented meaning — not to the regex.
- **Doubt B may be right.** An oil-cooled PMSM is plausible for Energica and
  the pole-pair count may check out. "Confirmed with a source" is a valid
  outcome; "left as it is because nobody could disprove it" is not.
- **Energica's corporate situation may complicate sourcing.** The company has
  been through financial difficulty, and documentation availability may have
  changed. Where a document cannot be opened, the absence is recorded rather
  than filled from an aggregator.
- **MotoE is a distraction.** Race machines are not what a workshop meets.
  In scope only where a road model inherits something documented.
- **Corpus count moves again**, with the four user docs.
