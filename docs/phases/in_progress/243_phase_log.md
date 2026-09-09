# Phase 243 — Harley-Davidson LiveWire / LiveWire One — phase log

**Status:** Planned
**Opened:** 2026-09-09

---

## 2026-09-09 — Plan v1.0 written

The second make-specific electric phase, and the first where the make is
contested: launched 2019 as the Harley-Davidson LiveWire, spun out from 2021 as
LiveWire One under a separate marque. A workshop meets both names.

**Step 0 — existing-code audit. Three findings.**

**1. The reachability problem is the inverse of Phase 242's.** Measured against
the live corpus: `make="Harley-Davidson"` returns **129 rows** — 110 combustion
Harley entries plus 241's 10 HV-safety entries — while `make="LiveWire"`
returns only 241's 10. Phase 240B's S2 was content that could not be reached;
here the risk is content **buried behind 110 Twin Cam, Sportster, V-Rod and
Milwaukee-Eight entries** that do not apply to an electric machine. The plan
therefore chooses `make="Harley-Davidson, LiveWire"` so both badges match, and
requires the reachability test to assert **position**, not merely presence.

**2. A combustion-cooling claim has already been extended to the LiveWire by
list membership.** `known_issues_cross_platform_cooling.json[0]` — filed under
`make="Honda"`, since cross-platform entries name makes in prose — states that
Harley's liquid-cooled models "including Street 750, Pan America, and LiveWire"
take a thermostat that "should be replaced every 40,000-50,000 miles". That is
a service interval attached to an electric motorcycle through a list. It may
even be partly right, since the Revelation powertrain is liquid-cooled; the
error, if any, may be the interval rather than the system. Either way it is the
cross-file contradiction shape Track K's audit exists to catch, and the phase
must resolve it rather than write alongside it.

**3. A synthetic campaign id for the LiveWire is already in the product.**
`src/motodiag/advanced/data/recalls.json` carries `HD-20-LW-BMS` describing a
BMS firmware fault halting charging. The Track K closure audit recorded section
D as fifteen European rows with synthetic ids; this extends the same finding to
Track L. This phase ships campaigns by mechanism with no reference numbers, so
the product would carry both disciplines at once. Recorded — correcting
`recalls.json` is outside Track L, and the audit already scopes that boundary.

**The research uses the canonical lenses** in `docs/phases/RESEARCH_LENSES.md`,
made canonical at Phase 242B after 242's figure lens applied a
manufacturer-document standard to every evidence class and silently refuted all
35 regulator and community claims. The source-class-aware standard applies from
the start here, and the survivors will be grouped by `source_class` before any
entry is written: if one class comes back at or near 100%, the lens is suspect,
not the corpus.

Baseline before any work: **6047 passed / 0 failed** (Phase 242).

Plan v1.0 written to `docs/phases/in_progress/243_implementation.md`.
