# Phase 213 — BMW S1000RR / S1000R / S1000XR — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-213-bmw-s1000`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit (inline)

- **Greenfield for content.** No BMW inline-four entry exists; every
  `S1000` grep hit is `GSX-S1000` (27) or `GS1000` (4), both Suzuki.
- **The roadmap row names a topic already written.** Row 213 says
  "…electronics, shift assist pro", but Phase 212 shipped a Gear Shift
  Assist Pro entry for the F750/F850GS, and quickshifter failures are
  covered again on the CBR1000RR and in cross_platform_drivetrain. A
  fourth is only justified if the S1000's system fails differently.
- **Generic electronics are saturated** — traction control, IMU,
  lean-sensitive intervention, riding modes and semi-active suspension
  appear across ~48 files, including four litre-class peers. Any S1000
  electronics entry must name BMW hardware (DDC, DTC Pro, ABS Pro, HP4)
  and describe a failure of that specifically.
- **Method decided with the user.** Ultracode is off, so rather than
  assume, the options were put explicitly: the full verified workflow,
  a leaner two-refuter variant, or inline drafting. The user chose the
  full workflow — six drafting lenses, three refuters per candidate
  (attribution / invented figures / safety), each defaulting to refuted.
- **Load-bearing lens for this phase is attribution.** In 212 it caught
  an R1200 component written onto an F-series. Here the equivalent risk
  is a generic litre-bike failure wearing an S1000 badge, which four
  existing peer files make easy to do by accident.

### 2026-09-07 — Built. Six entries, and the twelve rejections are the finding.

- **18 drafted → 6 survived → 6 kept. 61 agents, 0 errors, 0
  undecided.** Every one of the twelve drops was **fatal on
  attribution**; no other lens cast a fatal verdict on any candidate.
  The plan named duplication as this phase's default failure mode and
  the refuter agreed twelve times.
- **The rejections were not wrong — they were unspecific.** *"Second
  gear jumps out under load on early S1000RR (K46)"* was killed as
  "the archetypal sport-bike transmission complaint — equally true of a
  ZX-10R, R1 or GSX-R1000", with no BMW part nomenclature and a generic
  diagnostic sequence. **Four separate DDC semi-active-suspension
  entries** died the same way, and the verdict on one is worth quoting:
  attribution mechanics *clean* — correct generation, DDC genuinely an
  option, no ported hardware — but "strip the BMW badge and the entry
  is the standard semi-active-suspension failure story."
- **Two entries rested on recall numbers that could not be confirmed**
  for this model, one of which also ported a cracked fuel-pump-flange
  story from the boxer and big-tourer families onto the K67 sportbike
  tank. An entry whose diagnostic value *is* a campaign identifier has
  to have that identifier right.
- **Two whole lenses produced no survivor.** RR 2015–2018 and S1000R
  were entirely refuted, so those generations are **absent rather than
  invented**. The synthesizer cut nothing and said so — there was
  nothing above the bar to cut.
- **The symptom contract worked this time.** Phase 212's drafters
  returned full sentences and ~60 strings were normalised by hand.
  Putting the rule in the JSON schema field description — with the
  reason stated, that symptoms are matched with SQL LIKE against a
  mechanic's typed query — produced compliant output first time: mean
  28 characters, max 39, zero manual edits.
- **The undecided state carried forward from 212 never fired.** 0
  errors, 0 undecided, so nothing's fate was decided by an outage.
- 6 entries (2 K46, 2 ShiftCam, 2 S1000XR first-gen); 684 → 690; 36
  phase tests; regression **5000 / 0**; F9 lint clean.
- **Key finding: in a saturated corpus, "specific enough to be worth
  adding" is a far harder bar than "true".** All twelve rejected
  entries were plausibly correct; they were rejected for being correct
  about motorcycles in general rather than about these motorcycles.
  With four litre-class peers already seeded, a generic litre-bike
  entry has zero marginal value and a real cost in a mechanic's trust.
  Six honest entries and two openly empty generations is the right
  output; twelve padded ones would have been worse than none.
