# Phase 244 — Energica (Ego, Eva, Esse, Experia)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-09

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

- [x] Doubt A resolved: `fault_codes.py`'s manufacturer attribution corrected,
      with the internal-namespace status stated plainly
- [x] Doubt B resolved: the pole-pair and motor claims sourced, corrected, or
      withdrawn — never left unsourced
- [x] Every printed figure names its document under the class-matched standard
- [x] Survivors grouped by `source_class` and the distribution checked
- [x] No campaign reference number anywhere
- [x] `make="Energica"` returns the file and 241's HV floor, critical first
- [x] Provenance honest per entry; forum-tip biconditional
- [x] Count guards and the four user docs move together
- [x] Every new guard mutation-tested
- [x] Full regression at or above 6066, 0 failed

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

---

## Deviations from Plan

**Both named doubts were refuted, and the assigned-question method worked
again.** 6 agents, 0 errors, ~720K subagent tokens; 28 claims, 23 survived, 0
unverified. Survivors: 18 manufacturer-document, 2 regulator-record, 2
community-report, 1 not-established. No lens-skew warning.

**Doubt A — refuted, and the origin of the error identified.** Energica
publishes 110 fault codes in its owner's manual, pages 77-83, in standard SAE
J2012 form: a letter P, B, C or U and four alphanumerics, no underscore and no
prefix. A full-text search for `HV_|MC_|BMS_|INV_|CHG_|REG_` across the manual,
the manufacturer's component-and-diagnosis sheet and an owner-compiled copy of
the same table returned zero hits.

The researcher also found *how the mistake was probably made*, which is the
part worth keeping: "HV" and "BMS" **do** appear in Energica's table — in the
DESCRIPTION column, never the code label. P1010 is "HV+ CONTACTOR SHORT
CIRCUIT"; P0516 is "BMS TEMPERATURE SENSOR SHORT CIRCUIT FAULT". Pattern-
matching on description text yields prefixes no manufacturer uses.

`fault_codes.py` corrected: the namespace is kept — it is a serviceable
internal convention and Phase 111 depends on it — but it is now documented as
internal, with what each of the three makes actually emits recorded beside it.
**Across all three makes now examined, the format matches nothing any of them
emits.**

Also recorded for a later phase: several Energica codes carry a hex letter in
the second position (P0A08, P0A05, P0A02), which a naive four-digit powertrain
matcher silently drops.

**Doubt B — refuted four ways over, and the claim withdrawn.** No Energica
source states a pole or pole-pair count: zero occurrences of "pole" in the
126-page manual, none in the archived 2016/2022/2023 spec tables, none in the
current tables or technology page, and no secondary coverage asserts one
either. Beyond the missing number, three further defects made the line unsafe:
the motor type was wrong for most of the range (oil-cooled PMAC only pre-2021,
liquid-cooled HSM on EMCE, PMASynRM on the Experia); `motor_RPM x pole_pairs /
60` yields the **electrical fundamental**, not audible whine, which is
dominated by unpublished slot-passing and PWM orders; and motor rpm is not
derivable from wheel speed because the reduction ratio is unpublished.

**I was wrong about the blast radius, and my own guard caught it.** Plan v1.0
stated the pole-pair figure "is not consumed by any code". There is a public
function, `motor_rpm_to_whine_frequency()`, that computes exactly this, with
worked per-make examples in its docstring. I missed it because my grep excluded
`sound_signatures.py` while searching for uses *outside* the signature text —
a filter that hid the function living in the same file. The guard found it.

**Four of five guards were vacuous on first write, and mutation testing is the
only reason they are not shipping.** Each failed differently:

| gap | why it escaped |
|---|---|
| figure guard asked "is *some* document named", not "is *this* figure sourced" | an injected pole count inherited the entry's existing citation |
| price regex matched only currency **symbols** | the research withheld `USD 500` / `USD 2,500` — currency **codes** |
| attribution guard filtered to lines containing `HV_` | `"for HV faults"` has no underscore, so the line was skipped entirely |
| pole guard scanned +/-400 characters | the rewritten docstring is full of attribution words, so any figure dropped in inherited them |

The price gap is the sharpest: a guard written against printing prices missed
the exact figures this research withheld, because it was written against a form
the source material does not use.

**Fixing the attribution gap immediately produced a mention-versus-use
failure.** The widened guard flagged the correction itself, because the
correction quotes the wrong attribution in order to refute it. Rewritten to be
block-scoped and to judge each occurrence on what precedes it — an attribution
introduced by "previously read" is being cited, not made — with anti-vacuity
assertions in both directions and a positive check that the guard cannot be
satisfied by deleting the comment.

**A guard pattern was widened for a legitimate document type.** `DOC` listed
"spec sheet" but not "spec table", so an entry citing Energica's own model spec
tables failed. Widened, and re-checked that it still rejects an entry naming
nothing.

## Results

| Metric | Value |
|--------|-------|
| Research | Track K cadence, **6 agents**, 0 errors, ~720K subagent tokens |
| Claims | 28 unique, **23 survived**, 5 rejected, **0 unverified** |
| Distribution | 18 manufacturer / 2 regulator / 2 community / 1 not-established — no skew |
| Named doubts | **both refuted**; both corrected in source |
| Source files corrected | 2 — `engine/fault_codes.py`, `media/sound_signatures.py` |
| Entries shipped | **12** — 10 `service-manual`, 2 `forum` |
| Corpus | 958 → **970**; four user docs moved with it |
| Guards | 21 |
| Mutation scenarios | 5 — **4 escaped on first write**, all 5 caught after repair |
| Regression | **6087 passed / 0 failed** (baseline 6066; +21 guards) |

**Key finding: a guard written before the evidence is a guess about what the
evidence will look like.** All four vacuous guards were written from plan v1.0,
before the research returned — and each missed because it anticipated the wrong
*form*: currency symbols instead of codes, an underscore instead of a bare
prefix, a line instead of a block, presence-of-citation instead of
attribution-of-figure. Writing guards early is still right; it caught the
function I had missed. But a guard authored before its evidence must be
re-mutated *after* the evidence lands, because until then it has only ever been
tested against the failure mode its author imagined.
