# Phase 243 — Harley-Davidson LiveWire and LiveWire One

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-09

## Goal

The second make-specific electric phase, and the first where the make itself is
contested: the machine launched in 2019 as the **Harley-Davidson LiveWire** and
from 2021 the brand was spun out, so the same lineage continues as **LiveWire
One** under LiveWire as a separate marque. A workshop meets both, often on one
ramp, and the product must answer for either name.

This phase covers what is specific to that lineage — the Revelation powertrain,
the charging system, the H-D dealer service route the early bikes depend on,
and the failure patterns and campaigns actually recorded. Phase 241 laid the
make-agnostic HV safety floor; 246, 247 and 249 own generic BMS, inverter and
thermal.

CLI: no new commands. Content reaches mechanics through `kb search`,
`kb symptom`, `diagnose`.

Outputs:
- `known_issues_livewire.json`
- `tests/test_phase243_livewire.py`
- a decision, recorded, on the `make` field (see Logic)
- the research record, with rejected claims and reasons

## Logic

### Step 0 — what exists

**The reachability problem runs the opposite way from Phase 242's.** Measured
against the live corpus:

| query | rows returned |
|---|---|
| `make="Harley-Davidson"` | **129** — 110 combustion Harley entries plus 241's 10 HV entries |
| `make="LiveWire"` | 10 — only 241's HV floor |
| `make="Zero"` | 27 |

Phase 240B's S2 was about content being unreachable. Here the risk is the
reverse: a LiveWire filed as `Harley-Davidson` is returned **behind 110 Twin
Cam, Sportster, V-Rod and Milwaukee-Eight entries**, none of which apply to an
electric machine. Over-inclusion at that ratio is not a minor imprecision — it
is content that cannot be found.

**Three existing entries already mention LiveWire in passing**, all filed under
`make="Honda"` because they are cross-platform entries that list makes in
prose. One of them,
`known_issues_cross_platform_cooling.json[0]`, states that Harley's
liquid-cooled models "including Street 750, Pan America, and LiveWire" take a
thermostat that "should be replaced every 40,000-50,000 miles". **That is a
combustion-cooling claim extended to an electric machine by list membership,
and it carries a service interval.** Whether a LiveWire has a thermostat on
that schedule at all is a research question this phase must answer, and it is
the exact cross-file contradiction shape Track K's audit was built to catch.

**`src/motodiag/advanced/data/recalls.json` carries a synthetic LiveWire
campaign id**, `HD-20-LW-BMS`, describing a BMS firmware fault halting
charging. That extends the Track K audit's section D finding — previously
recorded as fifteen European rows with synthetic ids — to this track. This
phase ships campaigns by mechanism with no reference numbers; a synthetic id
sitting in the parts-adjacent catalogue contradicts that discipline in the same
product. The phase records it; correcting `recalls.json` is not Track L's to
do, and the audit already scopes that boundary.

### The `make` decision

Recorded before research so the research can test it rather than assume it.
The options and their costs:

1. `make="LiveWire"` alone — precise, joins 241's HV floor cleanly, but a
   mechanic who types the machine's own 2019-2021 badge, `Harley-Davidson`,
   finds nothing.
2. `make="Harley-Davidson"` alone — findable from the early badge, but buried
   behind 110 combustion entries and wrong for the post-2021 marque.
3. `make="Harley-Davidson, LiveWire"` — matched by `%Harley%` **and**
   `%LiveWire%`, so both names reach it. This is the Track K convention for
   genuinely cross-make entries and the same shape 241 uses.

**Option 3 is the plan's choice**, with the entries themselves stating which
badge applies to which model years. The residual cost is that a combustion
Harley query also returns these entries — acceptable, and the mirror of the
decision recorded at 241, because the knowledge search has no powertrain
filter. That absent filter is now the third phase to be shaped by it and
belongs in the debt record.

### Research

Runs the canonical lenses in `docs/phases/RESEARCH_LENSES.md` — made canonical
at Phase 242B precisely because 242's figure lens applied a
manufacturer-document standard to regulator and community claims and silently
refuted all of them. The source-class-aware standard is used here from the
start, and the survivors are grouped by `source_class` before use: **if one
class comes back at or near 100%, the lens is suspect, not the corpus.**

Finders: manufacturer document; regulator record; owner community; diagnostic
tooling and the dealer route; platform generation across the brand split.

## Key Concepts

- **A figure carries its document or it is withheld** (238, hardened at 241,
  generalised at 242B) — with the attribution standard matched to the evidence
  class.
- **Campaigns by mechanism, never by reference number** (231).
- **Reachability is correctness** (240B S2) — and so is not being buried.
- **Ordering is real** (240C): critical entries surface first, which is what
  makes a 129-row Harley result survivable at all.
- **Scope by ownership**: 246/247/249 own the generic systems.

## Verification Checklist

- [x] Every entry reachable from both `Harley-Davidson` and `LiveWire`
- [x] Entries state which badge applies to which model years
- [x] Every printed figure names its document under the class-matched standard;
      every withheld figure states the absence
- [x] Survivors grouped by `source_class` and the distribution sanity-checked
      before any entry is written
- [x] The cross-platform thermostat claim resolved — corrected, or recorded as
      a contradiction this phase does not own
- [x] No campaign reference number anywhere
- [x] Provenance honest per entry; forum-tip biconditional
- [x] Count guards and the four user docs move together
- [x] Every new guard mutation-tested
- [x] Full regression at or above 6047, 0 failed

## Risks

- **Burial, not absence.** The failure mode here is content that exists and
  cannot be found under 110 combustion entries. The reachability test must
  assert position, not just presence.
- **The brand split invites wrong-year content.** A claim about LiveWire One
  applied to a 2019 Harley-Davidson LiveWire, or the reverse, is the
  same-nameplate error Track K hit repeatedly. Year ranges must be defensible
  per badge.
- **The thermostat claim may be right.** The Revelation powertrain is
  liquid-cooled, so a coolant service may genuinely exist — the error, if there
  is one, may be the interval rather than the system. Refute it properly rather
  than assuming an electric machine has no thermostat.
- **Harley's dealer route is a business fact as well as a technical one**, and
  the brand split may have changed it. What an independent can obtain is a
  research question, not an assumption.
- **Corpus count moves again**, with the four user docs.

---

## Deviations from Plan

**None to the shape of the phase.** The Track K cadence held: 2 questions x 2
adversarial lenses = 6 agents, 6 completed, no errors, **~980K subagent tokens
against Phase 242's ~17M across two runs**. 21 of 28 claims survived.

**The corrected lens worked, and the skew check confirmed it rather than
assuming it.** Survivors came back 11 `manufacturer-document`, 4
`regulator-record`, 6 `community-report`. The workflow's own lens-skew warning
— added after 242, firing when one class exceeds 95% of survivors — stayed
silent, which is the first positive evidence that the source-class-aware
standard in `docs/phases/RESEARCH_LENSES.md` does what it was written to do.

**The thermostat question was answered, and the corpus was wrong.** The
research enumerated and fetched **all 108 sections** of the LiveWire owner's
manual: the word *thermostat* appears **zero times**. Neither the 2020 nor the
2021 service-interval table carries a thermostat row. The manual's own
cooling-system troubleshooting topic lists low or improper coolant, obstructed
radiator airflow, blocked passages and a radiator cap problem as the causes of
overheating — no thermostat, which is exactly where one would appear if the
diagnostic tree recognised one.

The `40,000-50,000 miles` figure turned out to be a corrupted echo of a real
interval: both manuals **do** schedule a coolant replacement, once, at 80,000
km (50,000 mi). So a 50,000-mile number is genuine for this machine and
attaches to the coolant rather than to a thermostat.

`known_issues_cross_platform_cooling.json[0]` was corrected: LiveWire struck
from the model list, with the reasoning stated inline. **The correction states
its own scope** — it makes no claim either way about the Street 750 or Pan
America, which the research did not examine, and a guard asserts that
disclaimer is present so a later reader cannot mistake silence for a finding.

**The entry records the limit of its own evidence.** No LiveWire parts
catalogue or service manual could be opened (the lookup endpoint returns 403),
so whether a thermostat exists as an *orderable part* inside the loop is not
established — only that it is not a scheduled-service item and carries no
replacement interval. A guard asserts the entry keeps saying "not established"
rather than hardening into a claim the research cannot support.

**Two claims were rejected for carrying campaign reference numbers**, which is
the Phase 231 rule working across tracks without anyone re-arguing it.

## Results

| Metric | Value |
|--------|-------|
| Research cadence | Track K: 2 questions x 2 lenses = **6 agents**, 0 errors |
| Cost | **~980K subagent tokens** (Phase 242: ~17M across two runs) |
| Claims | 28 unique, **21 survived**, 7 rejected, **0 unverified** |
| Source-class distribution | 11 manufacturer / 4 regulator / 6 community — **no skew warning** |
| Entries shipped | **14** — 11 `service-manual`, 3 `forum` |
| Shipping content corrected | 1 — the cross-platform thermostat list |
| Corpus | 944 → **958**; four user docs moved with it |
| Guards | 19, six families mutation-tested |
| Mutation scenarios | 6, all caught |
| Regression | **6066 passed / 0 failed** (baseline 6047; +19 guards) |

**Key finding: the cheaper cadence found the error the expensive one would
have missed, because the question was assigned rather than hoped for.** Phase
242 swept five finders and 75 claims at seventeen times the cost. This phase
ran two questions and named the thermostat claim as a required output field of
one of them — and got a definitive answer with a section count, a zero-hit
search, and a scoping caveat the researcher volunteered unprompted. Breadth
finds what you did not know to look for; a named question finds what you
already suspect is wrong. A phase that has a specific doubt should spend its
budget on the doubt.
