# Phase 243 — Harley-Davidson LiveWire / LiveWire One — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-09 | **Closed:** 2026-09-09
**Repo:** https://github.com/Kubanjaze/moto-diag

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

---

## 2026-09-09 — Build complete

**The Track K cadence held and cost a seventeenth of Phase 242.** Two research
questions, two adversarial lenses over each batch, six agents, zero errors,
~980K subagent tokens against 242's ~17M across two runs. 28 unique claims, 21
survived, 7 rejected, **0 unverified** — no refuter died, so nothing had to be
recorded as debt.

**The corrected lens is confirmed working, not assumed.** Survivors came back
11 `manufacturer-document`, 4 `regulator-record`, 6 `community-report`. The
lens-skew warning built into the workflow after 242 — it fires when one source
class exceeds 95% of survivors — stayed silent. That is the first positive
evidence that the standard now canonical in `docs/phases/RESEARCH_LENSES.md`
does what it was written to do, rather than merely not having failed yet.

**The thermostat claim in shipping content was wrong, and the research settled
it decisively.** All 108 sections of the LiveWire owner's manual were
enumerated and fetched: *thermostat* appears **zero times**. Neither the 2020
nor the 2021 service-interval table carries a thermostat row. The manual's own
cooling-system troubleshooting topic lists low or improper coolant, obstructed
radiator airflow, blocked passages and a radiator cap — no thermostat, in
precisely the place one would appear if the diagnostic tree recognised it.

The `40,000-50,000 miles` figure was a corrupted echo of something real: both
manuals schedule a coolant replacement, once, at 80,000 km (50,000 mi). The
number is genuine; it belongs to the coolant.

`known_issues_cross_platform_cooling.json[0]` corrected — LiveWire struck from
the list, reasoning stated inline. **The correction is scoped**: it makes no
claim either way about the Street 750 or Pan America, which were not examined,
and a guard asserts that disclaimer stays present so silence is never mistaken
for a finding. The LiveWire entry likewise keeps saying *not established* about
whether a thermostat exists as an orderable part, because the parts catalogue
and service manual could not be opened — and a guard asserts that too, so the
entry cannot harden into a claim the evidence does not carry.

**14 entries**, 11 `service-manual` and 3 `forum`. The most operationally
useful is the charging one: a LiveWire ONE on a Level 2 charger charges at the
**Level 1 rate**, which the manual attributes to the onboard charger. An owner
reporting no benefit from a public AC charger is describing designed behaviour,
and a shop chasing it finds nothing.

**The reachability guard asserts position, not presence** — the failure mode
this phase was scoped around. `make="Harley-Davidson"` returns 110 combustion
entries, so LiveWire content that merely exists is unfindable. Mutation 1
demotes the critical recall and the guard fires. That assertion is only
*possible* because Phase 240C fixed severity ordering; before it, `critical`
sorted last and there was no band to be inside.

**Two claims were rejected for carrying campaign reference numbers** — the
Phase 231 rule holding across tracks with nobody re-arguing it.

Six mutation scenarios, all caught, including reverting the thermostat
correction and making an entry overstate past its evidence. Corpus 944 → 958;
four user docs moved under the Phase 208 guard. F9 lint clean.

Regression: **6066 passed / 0 failed** (baseline 6047; +19 guards).
