# Phase 242 — Zero Motorcycles — phase log

**Status:** Planned
**Opened:** 2026-09-09

---

## 2026-09-09 — Plan v1.0 written

The first make-specific electric phase, on the HV safety floor 241 laid.

**Step 0 — existing-code audit.** Nothing. Zero, Z-Force, ZF14 and Cypher
appear in no knowledge, DTC, compat, parts or template file except 241's
make-agnostic HV file; the vehicle identifier has never heard the name; the
only electric workflow template is the generic PPI. Discipline 9 (the primary
source may already be on disk) was checked across the scratchpad, Downloads
and the repo's data directory and found nothing. Greenfield content on the
Phase 110/111 extension substrate — the same footing as 241.

**Scope boundary, stated before content exists.** Phases 246, 247 and 249 own
BMS, inverter and thermal. 242 covers what is Zero-specific and nothing
generic. The third refuter lens exists to enforce that.

**The figure boundary, stated before content exists.** 241 printed no
machine-specific figure because it opened no manufacturer document. 242 may
print one **only** from a Zero document the research actually opened and the
entry names — the Phase 238 rule, per entry. Otherwise the figure is withheld
and the absence stated. Spec roundups, aggregators and forum recollection do
not count as documents.

**The research is orchestrated, and the plan records its shape.** Track K ran
2 questions × 2 refuter lenses; this phase runs a five-way multi-modal sweep
(manufacturer document, regulator record, owner community, tooling, platform
generation), then three-lens adversarial refutation per claim — source exists
and says this; figure is attributed; claim is Zero-specific — with refuters
defaulting to refuted, then a completeness critic, then synthesis. Every
rejected claim is recorded with its reason. An entry count is what survives,
not a target.

**Two open questions the research answers, not the plan.** Whether Zero's fault
codes are documented in a primary source (then a `dtc_codes/zero.json` ships;
otherwise the absence is recorded), and how the Zero app — the actual
diagnostic route — should be represented given `adapters.json` has no
app-based transport.

Baseline before any work: **6031 passed / 0 failed** (Phase 241).

Plan v1.0 written to `docs/phases/in_progress/242_implementation.md`.
