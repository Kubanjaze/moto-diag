# Phase 213 — BMW S1000RR / S1000R / S1000XR — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
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
